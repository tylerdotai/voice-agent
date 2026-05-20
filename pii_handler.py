"""PII detection and redaction for voice agent."""

import re

# Patterns for PII detection
PII_PATTERNS = {
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone": r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b",
    "ssn": r"\b[0-9]{3}[-]?[0-9]{2}[-]?[0-9]{4}\b",
    "credit_card": r"\b(?:[0-9]{4}[- ]?){3}[0-9]{4}\b",
    "ip_address": r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
}

REDACTED_PLACEHOLDERS = {
    "email": "[EMAIL]",
    "phone": "[PHONE]",
    "ssn": "[SSN]",
    "credit_card": "[CREDIT_CARD]",
    "ip_address": "[IP]",
}


def detect_pii(text: str) -> list[dict]:
    """Detect PII in text and return locations. Does NOT return raw PII values."""
    findings = []
    for pii_type, pattern in PII_PATTERNS.items():
        for match in re.finditer(pattern, text):
            # Mask value for security - never expose raw PII in findings
            masked_value = REDACTED_PLACEHOLDERS[pii_type]
            findings.append(
                {
                    "type": pii_type,
                    "start": match.start(),
                    "end": match.end(),
                    "redacted": masked_value,
                }
            )
    return findings


def redact_pii(text: str) -> tuple[str, list[dict]]:
    """Redact PII from text. Returns (redacted_text, findings)."""
    findings = detect_pii(text)
    redacted = text
    # Replace from end to avoid offset shifting
    for finding in sorted(findings, key=lambda x: x["start"], reverse=True):
        redacted = redacted[: finding["start"]] + finding["redacted"] + redacted[finding["end"] :]
    return redacted, findings


def has_pii(text: str) -> bool:
    """Check if text contains any PII."""
    return len(detect_pii(text)) > 0
