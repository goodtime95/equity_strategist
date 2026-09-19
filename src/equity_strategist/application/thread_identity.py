"""One versioned identity for all persistent references to an external thread."""

from hashlib import sha256


def persistent_thread_id(external_thread_id: str) -> str:
    """Pseudonymize exact UTF-8 input; never redact, trim or case-fold identity.

    This is a deterministic digest, not encryption or protection against guessing
    known IDs. API responses and LangGraph must keep using the external ID.
    """
    digest = sha256(
        b"equity-strategist:persisted-thread:v1\0" + external_thread_id.encode("utf-8")
    ).hexdigest()
    return f"thread-v1:{digest}"
