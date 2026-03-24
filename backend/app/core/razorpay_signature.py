import hmac
import hashlib


def verify_webhook_signature(body: bytes, signature: str, secret: str) -> bool:
    """Razorpay: HMAC SHA256 of raw webhook body using webhook secret."""
    if not secret or not signature:
        return False
    expected = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
