"""Web Push reminders that keep no birth data on the server.

The browser works out its own reminders (a date and a short text each) and hands them
over with its push subscription. The server stores only those, deletes each reminder
once it is sent, and forgets idle subscriptions.

- **Encryption:** each message is encrypted for the browser (RFC 8291, with the
  ``aes128gcm`` coding of RFC 8188), so the push service cannot read it.
- **Sender identity:** a VAPID token signed with the operator's key (RFC 8292) tells
  the push service who is sending.
- **Destinations:** only the browsers' own push services are ever called, so the API
  cannot be used to send requests to arbitrary addresses.

``python -m jyotish_api.push keys`` makes a VAPID key pair. ``python -m jyotish_api.push
send`` sends the reminders that are due; run it every few minutes from a scheduler.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import struct
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import delete, exists, select
from sqlalchemy.orm import Session

from jyotish_api.config import get_settings
from jyotish_api.db import PushReminder, PushSubscription, make_engine, session_factory

#: Host suffixes of the browsers' push services: Chrome and the other Chromium browsers,
#: Firefox, Safari, Edge.
PUSH_HOSTS = (
    "fcm.googleapis.com",
    "push.services.mozilla.com",
    "push.apple.com",
    "notify.windows.com",
)
RECORD_SIZE = 4096
#: How long a push service keeps an undelivered reminder (seconds).
TTL = 24 * 3600
#: Reminders overdue by more than this are dropped instead of sent late.
LATE = timedelta(days=1)
#: Subscriptions with nothing pending and not refreshed for this long are forgotten.
IDLE = timedelta(days=30)
#: POST a body with headers to a push service and return the HTTP status (injectable).
Transport = Callable[[str, dict[str, str], bytes], int]


def b64decode(text: str) -> bytes:
    """Base64url without padding, as browsers and VAPID use it."""
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _hmac(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha256).digest()


def _point(key: ec.EllipticCurvePublicKey) -> bytes:
    return key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )


def browser_key(p256dh: str) -> ec.EllipticCurvePublicKey:
    """The browser's P-256 public key; ``ValueError`` if it is not a valid point."""
    return ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), b64decode(p256dh))


def allowed_endpoint(endpoint: str) -> bool:
    """True for an https URL on a browser push service, on the default port."""
    parts = urlsplit(endpoint)
    host = (parts.hostname or "").lower()
    return (
        parts.scheme == "https"
        and parts.port is None
        and parts.username is None
        and any(host == h or host.endswith(f".{h}") for h in PUSH_HOSTS)
    )


def encrypt(
    message: bytes,
    p256dh: bytes,
    auth: bytes,
    *,
    salt: bytes | None = None,
    sender: ec.EllipticCurvePrivateKey | None = None,
) -> bytes:
    """The request body for one message, as a single ``aes128gcm`` record (RFC 8291)."""
    if len(message) + 17 > RECORD_SIZE:  # the padding delimiter and the 16-byte tag
        raise ValueError("a push message must fit in one record")
    salt = salt or os.urandom(16)
    sender = sender or ec.generate_private_key(ec.SECP256R1())
    receiver = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), p256dh)
    sender_point = _point(sender.public_key())
    shared = sender.exchange(ec.ECDH(), receiver)
    # HKDF (RFC 5869) with single-block outputs, as RFC 8291 section 3.4 writes it.
    ikm = _hmac(_hmac(auth, shared), b"WebPush: info\x00" + p256dh + sender_point + b"\x01")
    prk = _hmac(salt, ikm)
    cek = _hmac(prk, b"Content-Encoding: aes128gcm\x00\x01")[:16]
    nonce = _hmac(prk, b"Content-Encoding: nonce\x00\x01")[:12]
    record = AESGCM(cek).encrypt(nonce, message + b"\x02", None)
    return salt + struct.pack("!IB", RECORD_SIZE, len(sender_point)) + sender_point + record


@dataclass(frozen=True)
class Vapid:
    """The operator's signing key and contact, shown to push services (RFC 8292)."""

    private_key: ec.EllipticCurvePrivateKey
    subject: str

    @classmethod
    def from_base64(cls, private_key: str, subject: str) -> Vapid:
        scalar = int.from_bytes(b64decode(private_key), "big")
        return cls(ec.derive_private_key(scalar, ec.SECP256R1()), subject)

    @property
    def public_key(self) -> str:
        """The application server key browsers subscribe with (base64url)."""
        return b64encode(_point(self.private_key.public_key()))

    def authorization(self, endpoint: str, now: float | None = None) -> str:
        parts = urlsplit(endpoint)
        claims = {
            "aud": f"{parts.scheme}://{parts.netloc}",
            "exp": int((time.time() if now is None else now) + 12 * 3600),
            "sub": self.subject,
        }
        token = jwt.encode(claims, self.private_key, algorithm="ES256")
        return f"vapid t={token}, k={self.public_key}"


def new_vapid_keys() -> tuple[str, str]:
    """A new key pair: the private scalar and the public point, both base64url."""
    key = ec.generate_private_key(ec.SECP256R1())
    private = key.private_numbers().private_value.to_bytes(32, "big")
    return b64encode(private), b64encode(_point(key.public_key()))


def http_transport(url: str, headers: dict[str, str], body: bytes) -> int:
    if not allowed_endpoint(url):
        raise ValueError("push messages go only to browser push services")
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return int(response.status)
    except urllib.error.HTTPError as error:
        return int(error.code)


def deliver(
    subscription: PushSubscription,
    message: dict[str, str],
    vapid: Vapid,
    transport: Transport = http_transport,
) -> int:
    """Encrypt and post one message; the push service's HTTP status."""
    body = encrypt(
        json.dumps(message, ensure_ascii=False).encode(),
        b64decode(subscription.p256dh),
        b64decode(subscription.auth),
    )
    headers = {
        "Authorization": vapid.authorization(subscription.endpoint),
        "Content-Encoding": "aes128gcm",
        "Content-Type": "application/octet-stream",
        "TTL": str(TTL),
        "Urgency": "normal",
    }
    return transport(subscription.endpoint, headers, body)


def send_due(
    session: Session,
    vapid: Vapid,
    now: datetime | None = None,
    transport: Transport = http_transport,
    batch: int = 200,
) -> dict[str, int]:
    """Send the reminders that are due, then drop late ones and idle subscriptions.

    A sent reminder is deleted. A subscription the push service no longer knows (404
    or 410) is deleted with its reminders. Other failures are retried on the next run
    until the reminder is more than a day late.
    """
    now = now or datetime.now(UTC)
    counts = {"sent": 0, "failed": 0, "gone": 0, "late": 0, "idle": 0}
    late = session.execute(delete(PushReminder).where(PushReminder.due_at < now - LATE))
    counts["late"] = int(getattr(late, "rowcount", 0) or 0)
    due = session.scalars(
        select(PushReminder)
        .where(PushReminder.due_at <= now)
        .order_by(PushReminder.due_at)
        .limit(batch)
    ).all()
    gone: set[str] = set()
    for reminder in due:
        subscription = reminder.subscription
        if subscription.id in gone:
            continue
        message = {"title": reminder.title, "body": reminder.body, "url": "/my"}
        try:
            status = deliver(subscription, message, vapid, transport)
        except (OSError, ValueError):
            status = 0
        if status in (404, 410):
            gone.add(subscription.id)
            session.delete(subscription)
            counts["gone"] += 1
        elif 200 <= status < 300:
            session.delete(reminder)
            counts["sent"] += 1
        else:
            counts["failed"] += 1
    session.flush()
    pending = exists().where(PushReminder.subscription_id == PushSubscription.id)
    idle = session.execute(
        delete(PushSubscription).where(PushSubscription.updated_at < now - IDLE).where(~pending)
    )
    counts["idle"] = int(getattr(idle, "rowcount", 0) or 0)
    return counts


def vapid_from_settings(private_key: str | None, subject: str | None) -> Vapid | None:
    """The configured VAPID key, or ``None`` when push reminders are off."""
    if not private_key or not subject:
        return None
    return Vapid.from_base64(private_key, subject)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m jyotish_api.push", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("keys", help="print a new VAPID key pair")
    commands.add_parser("send", help="send the reminders that are due")
    args = parser.parse_args(argv)
    if args.command == "keys":
        private, public = new_vapid_keys()
        print(f"JYOTISH_API_VAPID_PRIVATE_KEY={private}")
        print(f"# public key, served by GET /v1/push/key: {public}")
        return 0

    settings = get_settings()
    vapid = vapid_from_settings(settings.vapid_private_key, settings.vapid_subject)
    if vapid is None:
        print(
            "push reminders are off: set JYOTISH_API_VAPID_PRIVATE_KEY and _SUBJECT",
            file=sys.stderr,
        )
        return 1
    engine = make_engine(settings.database_url, settings.database_tls, settings.database_ca_file)
    with session_factory(engine)() as session, session.begin():
        counts = send_due(session, vapid)
    print(json.dumps(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
