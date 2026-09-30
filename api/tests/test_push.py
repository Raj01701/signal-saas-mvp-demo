"""Web Push: RFC 8291 encryption, VAPID, the endpoint allowlist, routes and sending."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import struct
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from jyotish_api.config import ApiSettings
from jyotish_api.db import Base, PushReminder, PushSubscription
from jyotish_api.main import create_app
from jyotish_api.push import (
    Vapid,
    allowed_endpoint,
    b64decode,
    b64encode,
    encrypt,
    main,
    new_vapid_keys,
    send_due,
)

# RFC 8291, Appendix A.
RFC_PLAINTEXT = b"When I grow up, I want to be a watermelon"
RFC_AS_PRIVATE = "yfWPiYE-n46HLnH0KqZOF1fJJU3MYrct3AELtAQ-oRw"
RFC_AS_PUBLIC = (
    "BP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8wEqKK6PBru3jl7A8"
)
RFC_UA_PRIVATE = "q1dXpw3UpT5VOmu_cf_v6ih07Aems3njxI-JWgLcM94"
RFC_UA_PUBLIC = (
    "BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8pZGH6SRpkNtoIAiw4"
)
RFC_AUTH = "BTBZMqHH6r4Tts7J_aSIgg"
RFC_SALT = "DGv6ra1nlYgDCS1FRnbzlw"
RFC_BODY = (
    "DGv6ra1nlYgDCS1FRnbzlwAAEABBBP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInmYWAmS"
    "6TlzAC8wEqKK6PBru3jl7A_yl95bQpu6cVPTpK4Mqgkf1CXztLVBSt2Ks3oZwbuwXPXLWyouBWLVWGNWQexSgSxsj_Qu"
    "lcy4a-fN"
)
ENDPOINT = "https://fcm.googleapis.com/fcm/send/abc:def"


def _private(text: str) -> ec.EllipticCurvePrivateKey:
    return ec.derive_private_key(int.from_bytes(b64decode(text), "big"), ec.SECP256R1())


def _point(key: ec.EllipticCurvePrivateKey) -> bytes:
    return key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )


def _decrypt(body: bytes, receiver: ec.EllipticCurvePrivateKey, auth: bytes) -> bytes:
    """What the browser does with a message (RFC 8291 from the receiving side)."""
    salt, (_, idlen) = body[:16], struct.unpack("!IB", body[16:21])
    sender_point = body[21 : 21 + idlen]
    sender = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), sender_point)
    shared = receiver.exchange(ec.ECDH(), sender)

    def mac(key: bytes, data: bytes) -> bytes:
        return hmac.new(key, data, hashlib.sha256).digest()

    info = b"WebPush: info\x00" + _point(receiver) + sender_point
    prk = mac(salt, mac(mac(auth, shared), info + b"\x01"))
    cek = mac(prk, b"Content-Encoding: aes128gcm\x00\x01")[:16]
    nonce = mac(prk, b"Content-Encoding: nonce\x00\x01")[:12]
    record = AESGCM(cek).decrypt(nonce, body[21 + idlen :], None)
    assert record.rstrip(b"\x00").endswith(b"\x02")  # the last record's delimiter
    return record.rstrip(b"\x00")[:-1]


def test_encryption_matches_rfc_8291() -> None:
    sender = _private(RFC_AS_PRIVATE)
    assert b64encode(_point(sender)) == RFC_AS_PUBLIC
    body = encrypt(
        RFC_PLAINTEXT,
        b64decode(RFC_UA_PUBLIC),
        b64decode(RFC_AUTH),
        salt=b64decode(RFC_SALT),
        sender=sender,
    )
    assert b64encode(body) == RFC_BODY
    assert _decrypt(body, _private(RFC_UA_PRIVATE), b64decode(RFC_AUTH)) == RFC_PLAINTEXT


def test_each_message_gets_fresh_keys() -> None:
    receiver = ec.generate_private_key(ec.SECP256R1())
    auth = os.urandom(16)
    first, second = (encrypt(b"hello", _point(receiver), auth) for _ in range(2))
    assert first[:16] != second[:16] and first[21:86] != second[21:86]  # salt and key
    assert _decrypt(first, receiver, auth) == _decrypt(second, receiver, auth) == b"hello"
    with pytest.raises(ValueError, match="one record"):
        encrypt(b"x" * 4080, _point(receiver), auth)


def test_vapid_token_names_the_push_service() -> None:
    private, public = new_vapid_keys()
    vapid = Vapid.from_base64(private, "mailto:ops@example.org")
    assert vapid.public_key == public and len(b64decode(public)) == 65
    header = vapid.authorization(ENDPOINT, now=1_800_000_000)
    token, key = header.removeprefix("vapid t=").split(", k=")
    assert key == public
    claims = jwt.decode(
        token,
        vapid.private_key.public_key(),
        algorithms=["ES256"],
        audience="https://fcm.googleapis.com",
        options={"verify_exp": False},
    )
    assert claims == {
        "aud": "https://fcm.googleapis.com",
        "exp": 1_800_000_000 + 12 * 3600,
        "sub": "mailto:ops@example.org",
    }


@pytest.mark.parametrize(
    ("endpoint", "allowed"),
    [
        (ENDPOINT, True),
        ("https://updates.push.services.mozilla.com/wpush/v2/gAAAA", True),
        ("https://web.push.apple.com/QGuQyavXutnMH", True),
        ("https://wns2-par02p.notify.windows.com/w/?token=BQYAAA", True),
        ("http://fcm.googleapis.com/fcm/send/abc", False),
        ("https://fcm.googleapis.com:8443/fcm/send/abc", False),
        ("https://fcm.googleapis.com.evil.example/fcm/send/abc", False),
        ("https://evil.example/fcm.googleapis.com", False),
        ("https://user@fcm.googleapis.com/fcm/send/abc", False),
        ("https://169.254.169.254/latest/meta-data", False),
        ("https://notfcm.googleapis.com/x", False),
    ],
)
def test_only_browser_push_services_are_called(endpoint: str, allowed: bool) -> None:
    assert allowed_endpoint(endpoint) is allowed


def _browser() -> tuple[ec.EllipticCurvePrivateKey, dict[str, object]]:
    key = ec.generate_private_key(ec.SECP256R1())
    keys = {"p256dh": b64encode(_point(key)), "auth": b64encode(os.urandom(16))}
    return key, {"endpoint": ENDPOINT, "keys": keys}


def _app(**settings: object) -> TestClient:
    private, _ = new_vapid_keys()
    options: dict[str, object] = {
        "database_url": "sqlite://",
        "rate_limit": "1000/minute",
        "vapid_private_key": private,
        "vapid_subject": "mailto:ops@example.org",
        **settings,
    }
    app = create_app(ApiSettings(**options))  # type: ignore[arg-type]
    Base.metadata.create_all(app.state.db)
    return TestClient(app)


def _at(days: float) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


def test_routes_save_replace_and_forget_reminders() -> None:
    assert _app(vapid_private_key=None).get("/v1/push/key").status_code == 503
    client = _app()
    public = client.get("/v1/push/key").json()["public_key"]
    assert public == client.app.state.vapid.public_key  # type: ignore[attr-defined]

    _, subscription = _browser()
    reminders = [
        {"at": _at(-1), "title": "Past", "body": "ignored"},
        {"at": _at(10), "title": "Jyotish reminder", "body": "A career window begins"},
    ]
    body = {"subscription": subscription, "reminders": reminders}
    assert client.put("/v1/push/subscription", json=body).status_code == 204
    assert client.put("/v1/push/subscription", json=body).status_code == 204  # replaces
    with client.app.state.sessions() as session:  # type: ignore[attr-defined]
        assert session.scalar(select(func.count()).select_from(PushSubscription)) == 1
        titles = session.scalars(select(PushReminder.title)).all()
    assert titles == ["Jyotish reminder"]

    stolen = {**subscription, "keys": {**subscription["keys"], "auth": b64encode(os.urandom(16))}}  # type: ignore[dict-item]
    assert (
        client.put("/v1/push/subscription", json={**body, "subscription": stolen}).status_code
        == 409
    )
    wrong = {"endpoint": ENDPOINT, "auth": stolen["keys"]["auth"]}  # type: ignore[index]
    assert client.post("/v1/push/unsubscribe", json=wrong).status_code == 404
    right = {"endpoint": ENDPOINT, "auth": subscription["keys"]["auth"]}  # type: ignore[index]
    assert client.post("/v1/push/unsubscribe", json=right).status_code == 204
    assert client.post("/v1/push/unsubscribe", json=right).status_code == 204  # idempotent
    with client.app.state.sessions() as session:  # type: ignore[attr-defined]
        assert session.scalar(select(func.count()).select_from(PushReminder)) == 0


@pytest.mark.parametrize(
    ("change", "detail"),
    [
        ({"endpoint": "https://evil.example/x"}, "not a browser push service"),
        (
            {
                "keys": {
                    "p256dh": b64encode(b"\x04" + b"\x01" * 64),
                    "auth": "AAAAAAAAAAAAAAAAAAAAAA",
                }
            },
            "keys",
        ),
        ({"keys": {"p256dh": "BCVxsr7N", "auth": "AAAA"}}, "keys"),
    ],
)
def test_bad_subscriptions_are_refused(change: dict[str, object], detail: str) -> None:
    _, subscription = _browser()
    body = {"subscription": {**subscription, **change}, "reminders": []}
    response = _app().put("/v1/push/subscription", json=body)
    assert response.status_code == 422 and detail in response.json()["detail"]


def test_reminders_are_bounded() -> None:
    _, subscription = _browser()
    client = _app()
    far = {"subscription": subscription, "reminders": [{"at": _at(401), "title": "Far"}]}
    assert client.put("/v1/push/subscription", json=far).status_code == 422
    naive = {
        "subscription": subscription,
        "reminders": [{"at": "2027-01-01T08:00:00", "title": "x"}],
    }
    assert client.put("/v1/push/subscription", json=naive).status_code == 422
    many = {"subscription": subscription, "reminders": [{"at": _at(1), "title": "x"}] * 61}
    assert client.put("/v1/push/subscription", json=many).status_code == 422


def test_due_reminders_are_sent_encrypted_then_deleted() -> None:
    client = _app()
    vapid: Vapid = client.app.state.vapid  # type: ignore[attr-defined]
    browsers = [_browser(), _browser()]
    browsers[1][1]["endpoint"] = "https://updates.push.services.mozilla.com/wpush/v2/gone"
    for _, subscription in browsers:
        body = {
            "subscription": subscription,
            "reminders": [{"at": _at(0.01), "title": "Due", "body": "Now"}],
        }
        assert client.put("/v1/push/subscription", json=body).status_code == 204

    sent: list[tuple[str, dict[str, str], bytes]] = []

    def transport(url: str, headers: dict[str, str], body: bytes) -> int:
        sent.append((url, headers, body))
        return 410 if "gone" in url else 201

    later = datetime.now(UTC) + timedelta(hours=1)
    with client.app.state.sessions() as session, session.begin():  # type: ignore[attr-defined]
        counts = send_due(session, vapid, later, transport)
    assert counts == {"sent": 1, "failed": 0, "gone": 1, "late": 0, "idle": 0}

    _, headers, body = next(item for item in sent if item[0] == ENDPOINT)
    assert headers["Content-Encoding"] == "aes128gcm" and headers["TTL"] == str(24 * 3600)
    assert headers["Authorization"].startswith("vapid t=")
    key, subscription = browsers[0]
    message = _decrypt(body, key, b64decode(subscription["keys"]["auth"]))  # type: ignore[index]
    assert json.loads(message) == {"title": "Due", "body": "Now", "url": "/my"}
    with client.app.state.sessions() as session:  # type: ignore[attr-defined]
        assert session.scalar(select(func.count()).select_from(PushReminder)) == 0
        endpoints = session.scalars(select(PushSubscription.endpoint)).all()
    assert endpoints == [ENDPOINT]  # the one its push service forgot is gone

    idle = later + timedelta(days=31)
    with client.app.state.sessions() as session, session.begin():  # type: ignore[attr-defined]
        assert send_due(session, vapid, idle, transport)["idle"] == 1


def test_late_and_failed_reminders() -> None:
    client = _app()
    vapid: Vapid = client.app.state.vapid  # type: ignore[attr-defined]
    _, subscription = _browser()
    body = {"subscription": subscription, "reminders": [{"at": _at(0.01), "title": "Due"}]}
    client.put("/v1/push/subscription", json=body)

    def unavailable(url: str, headers: dict[str, str], body: bytes) -> int:
        return 503

    soon = datetime.now(UTC) + timedelta(hours=1)
    with client.app.state.sessions() as session, session.begin():  # type: ignore[attr-defined]
        assert send_due(session, vapid, soon, unavailable)["failed"] == 1  # kept for a retry
    with client.app.state.sessions() as session, session.begin():  # type: ignore[attr-defined]
        assert send_due(session, vapid, soon + timedelta(days=2), unavailable)["late"] == 1


def test_command_line(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["keys"]) == 0
    printed = capsys.readouterr().out
    assert printed.startswith("JYOTISH_API_VAPID_PRIVATE_KEY=") and "public key" in printed
