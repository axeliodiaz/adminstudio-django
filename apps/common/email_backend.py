import os
import ssl

from django.core.mail.backends.smtp import EmailBackend as DjangoSMTPEmailBackend


class CustomSMTPEmailBackend(DjangoSMTPEmailBackend):
    """
    SMTP Email backend that allows configuring TLS/SSL certificate verification.

    Behavior (secure by default):
    - Verification ON by default using the system trust store.
    - If EMAIL_CA_BUNDLE (or SSL_CERT_FILE / REQUESTS_CA_BUNDLE) is set, it will be used
      as the CA bundle to validate the server certificate.
    - If EMAIL_TLS_VERIFY is set to "false" (or 0/no/off), verification is disabled
      (use ONLY for local/dev troubleshooting).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ssl_context = self._build_ssl_context()

    @staticmethod
    def _build_ssl_context() -> ssl.SSLContext:
        # Import settings lazily to avoid issues at import time
        try:
            from django.conf import settings  # type: ignore
        except Exception:  # pragma: no cover - fallback if settings aren't ready
            settings = None

        # Determine verification flag: prefer Django settings, fall back to env var
        verify_value = None
        if settings is not None and hasattr(settings, "EMAIL_TLS_VERIFY"):
            verify_value = getattr(settings, "EMAIL_TLS_VERIFY")
        else:
            verify_value = os.getenv("EMAIL_TLS_VERIFY", "true")

        # Normalize to boolean
        if isinstance(verify_value, str):
            verify = verify_value.strip().lower() in {"1", "true", "yes", "on"}
        else:
            verify = bool(verify_value)

        # Determine CA bundle path: prefer Django settings, then common env vars
        ca_bundle = None
        if settings is not None and hasattr(settings, "EMAIL_CA_BUNDLE"):
            ca_bundle = getattr(settings, "EMAIL_CA_BUNDLE")
        if not ca_bundle:
            ca_bundle = (
                os.getenv("EMAIL_CA_BUNDLE")
                or os.getenv("SSL_CERT_FILE")
                or os.getenv("REQUESTS_CA_BUNDLE")
            )

        if not verify:
            # Disable verification (development only)
            return ssl._create_unverified_context()

        if ca_bundle:
            # Use provided CA bundle to validate the server certificate
            return ssl.create_default_context(cafile=ca_bundle)

        # Default secure context using system trust store
        return ssl.create_default_context()
