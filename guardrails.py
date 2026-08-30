import re

MAX_INPUT_LENGTH = 500

INJECTION_PATTERNS = [
    r"(?i)ignore\s+(your\s+)?instructions",
    r"(?i)ignore\s+previous",
    r"(?i)don't\s+(tell|inform|show|print|mention)",
    r"(?i)system\s*:",
    r"(?i)override",
    r"(?i)worst\s+thing",
    r"(?i)escape\s+the\s+prompt",
    r"(?i)jailbreak",
    r"(?i)<script",
    r"(?i)<[^>]+>",
    r"(?i)you\s+are\s+(now|a|an)\s+",
    r"(?i)dismiss\s+your\s+rules",
    r"(?i)pretend\s+(you\s+are|to\s+be)",
    r"(?i)for\b.*\bsecurity",
    r"(?i)unrestricted\s+mode",
]

BLOCKED_MESSAGE = "Your input was blocked by our safety filter."

def check_input(user_input: str) -> bool:
    if not user_input or not user_input.strip():
        raise ValueError("Input cannot be empty.")

    if len(user_input) > MAX_INPUT_LENGTH:
        raise ValueError(
            f"Input exceeds maximum length of {MAX_INPUT_LENGTH} characters."
        )

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, user_input):
            raise ValueError(BLOCKED_MESSAGE)

    return True