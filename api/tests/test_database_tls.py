"""verify-full TLS to Postgres checks the certificate; "prefer" and SQLite add nothing."""

from __future__ import annotations

import ssl

from jyotish_api.db import tls_connect_args

POSTGRES = "postgresql+pg8000://user@db.example.org:5432/jyotish"


def test_verify_checks_the_certificate_and_host_name() -> None:
    context = tls_connect_args(POSTGRES, "verify-full")["ssl_context"]
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode is ssl.CERT_REQUIRED and context.check_hostname


def test_prefer_and_sqlite_add_nothing() -> None:
    assert tls_connect_args(POSTGRES, "prefer") == {}
    assert tls_connect_args("sqlite:///./jyotish.db", "verify-full") == {}
