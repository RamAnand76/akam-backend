import re
from app.exceptions import PromptInjectionException

# Heuristics for adversarial prompt injection
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior)\s+instructions",
    r"system\s*prompt",
    r"you\s+are\s+now\s+a",
    r"jailbreak",
    r"act\s+as\s+an\s+unrestricted",
    r"DAN\s+mode",
    r"reveal\s+your\s+secret",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in PROMPT_INJECTION_PATTERNS]


def sanitise_text(text: str | None, max_length: int = 10000, check_prompt_injection: bool = True) -> str:
    if text is None:
        return ""
    
    # Strip null bytes (database/injection defense)
    clean = text.replace("\x00", "").strip()

    if len(clean) > max_length:
        clean = clean[:max_length]

    if check_prompt_injection and clean:
        for pattern in COMPILED_PATTERNS:
            if pattern.search(clean):
                raise PromptInjectionException(message="Malicious pattern or prompt injection detected in input.")

    return clean
