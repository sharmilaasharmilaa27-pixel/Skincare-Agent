import re
from collections import defaultdict
from datetime import datetime, timedelta

MAX_INPUT_LENGTH = 500
MAX_INPUT_LENGTH_HARD = 2000
RATE_LIMIT_PER_MINUTE = 10

SESSION_RATE_LIMITS: dict = defaultdict(list)

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
    r"(?i)bypass\s+(your|the)\s+(filter|guard|safety)",
    r"(?i)role\s+play\s+as\s+(an?\s+)?(assistant|expert)",
    r"(?i)developer\s+mode",
    r"(?i)turn\s+off\s+(your\s+)?(safety|filter|guard)",
    r"(?i)do\s+not\s+(respond|answer|follow)\s+(your|the)\s+(rules|instructions)",
    r"(?i)hypothetical\s+(scenario|situation|example).*(ignore|bypass|skip)",
    r"(?i)what\s+(would\s+you\s+do|do\s+you)\s+if\s+(you\s+had\s+no\s+)?(rules|restrictions)",
    r"(?i)system\s+prompt\s*(leak|reveal|show)",
    r"(?i)get\s+the\s+(actual|real)\s+(answer|response|information)\s+(without|bypassing)",
    r"(?i)injection|prompt\s+injection|xss|sql\s+injection",
    r"(?i)<|>",
    r"(?i)&#\d+;|&lt;|&gt;",
    r"(?i)\b(eval|exec|execfile|compile)\s*\(",
    r"(?i)import\s+(os|sys|subprocess|shutil)",
    r"(?i)__import__\s*\(",
]

BLOCKED_MESSAGE = "Your input was blocked by our safety filter."

def _check_rate_limit(session_id: str) -> bool:
    now = datetime.now()
    window_start = now - timedelta(minutes=1)
    SESSION_RATE_LIMITS[session_id] = [t for t in SESSION_RATE_LIMITS[session_id] if t > window_start]
    if len(SESSION_RATE_LIMITS[session_id]) >= RATE_LIMIT_PER_MINUTE:
        return False
    SESSION_RATE_LIMITS[session_id].append(now)
    return True

def sanitize_input(user_input: str) -> str:
    user_input = user_input.strip()
    user_input = re.sub(r'<[^>]+>', '', user_input)
    user_input = re.sub(r'&#\d+;|&lt;|&gt;', '', user_input)
    user_input = re.sub(r'\s+', ' ', user_input)
    return user_input

def check_input(user_input: str, session_id: str = "default") -> bool:
    if not user_input or not user_input.strip():
        raise ValueError("Input cannot be empty.")

    user_input = sanitize_input(user_input)

    if len(user_input) > MAX_INPUT_LENGTH_HARD:
        raise ValueError(f"Input exceeds hard limit of {MAX_INPUT_LENGTH_HARD} characters.")

    if len(user_input) > MAX_INPUT_LENGTH:
        raise ValueError(f"Input exceeds soft limit of {MAX_INPUT_LENGTH} characters.")

    if not _check_rate_limit(session_id):
        raise ValueError("Rate limit exceeded. Please wait before sending more messages.")

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, user_input):
            raise ValueError(BLOCKED_MESSAGE)

    return True