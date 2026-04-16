"""
Response cleaner — sanitizes raw LLM output into pure code.
Scales limits based on model config instead of hardcoded values.
"""
import re

# ─── Junk tokens to strip ────────────────────────────────────

_JUNK_TOKENS = frozenset([
    "<|endoftext|>", "<|fim_suffix|>", "<|fim_prefix|>", "<|fim_middle|>",
    "<EOT>", "</s>", "<s>", "[INST]", "[/INST]",
    "<PRE>", "<SUF>", "<MID>", "<FILL_HERE>",
    "<|eot_id|>", "<|im_end|>", "<|im_start|>", "<|end|>",
    "<fim_prefix>", "<fim_suffix>", "<fim_middle>",
    "<|assistant|>", "<|user|>",
])

# ─── Explanation markers (line starts) ───────────────────────

_EXPLANATION_STARTS = (
    "the function", "this function", "the code", "this code",
    "here is", "here's", "this is", "the provided", "in this",
    "note:", "explanation:", "step-by-step", "breakdown",
    "how it works", "what this does", "to understand",
    "la función", "el código", "esta función", "este código",
    "aquí está", "esto es", "nota:", "explicación:",
    "it looks", "however", "note that", "you can", "we can",
    "this will", "this should", "let me", "i will",
    "first,", "second,", "then,", "finally,",
    "example:", "usage:", "output:", "result:", "ejemplo",
    "args:", "returns:", "salida:",
)

# ─── Regex patterns for non-code lines ───────────────────────

_SKIP_PATTERNS = [
    re.compile(r"^\s*#\s*(explanation|note|example|usage|output|result|ejemplo|salida|args|returns):", re.I),
    re.compile(r"^\s*//\s*(explanation|note|example|usage|output|result):", re.I),
    re.compile(r"^\s*\d+\.\s+"),       # numbered lists
    re.compile(r"^\s*[-*]\s+\w"),       # bullet lists
    re.compile(r"^\s*\*\*"),            # bold markdown
    re.compile(r"^\s*#{1,4}\s+"),       # markdown headers
    re.compile(r"^\s*---"),             # horizontal rules
]


def clean(raw, prefix, mcfg):
    """Full cleaning pipeline. Returns pure code or empty string."""
    if not raw:
        return ""

    max_lines = mcfg.get("max_output_lines", 10)
    max_chars = mcfg.get("max_output_chars", 400)

    text = raw.strip()
    text = _strip_junk_tokens(text)
    text = _strip_code_fences(text)
    text = _strip_docstrings(text)
    text = _cut_at_explanation(text)
    text = _filter_lines(text)
    text = _remove_prefix_echo(text, prefix)
    text = _enforce_limits(text, max_lines, max_chars)

    text = text.rstrip()
    if len(text.strip()) < 2:
        return ""
    return text


# ─── Pipeline stages ─────────────────────────────────────────

def _strip_junk_tokens(text):
    for tok in _JUNK_TOKENS:
        text = text.replace(tok, "")
    return text


def _strip_code_fences(text):
    text = re.sub(r"```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"```", "", text)
    return text.strip()


def _strip_docstrings(text):
    text = re.sub(r'""".*?"""', "", text, flags=re.DOTALL)
    text = re.sub(r"'''.*?'''", "", text, flags=re.DOTALL)
    return text


def _cut_at_explanation(text):
    """Cut text at the first block that looks like natural language."""
    patterns = [
        r"\n\n(?:It looks|However|Note that|This code|The code|Here is)",
        r"\n\n(?:Esta función|Suma dos|Parece que|Sin embargo|Nota|Este código)",
        r"\n\n\d+\.",
        r"\n\n[*-]\s",
        r"\n(?:# (?:Ejemplo|Example|Usage|Uso))",
        r"\nprint\(",
    ]
    earliest = len(text)
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m and m.start() < earliest:
            earliest = m.start()
    if earliest < len(text):
        return text[:earliest].strip()
    return text


def _filter_lines(text):
    """Remove lines that are clearly not code."""
    lines = text.split("\n")
    result = []
    for line in lines:
        stripped = line.strip()

        # Skip empty lines at the start
        if not stripped and not result:
            continue

        low = stripped.lower()

        # Explanation line — stop here
        if any(low.startswith(kw) for kw in _EXPLANATION_STARTS):
            break

        # Regex skip patterns
        if any(p.match(stripped) for p in _SKIP_PATTERNS):
            continue

        # Long comment that's probably prose
        if stripped.startswith("#") and len(stripped) > 60:
            words = stripped.split()
            code_chars = sum(1 for c in stripped if c in "=()[]{}:;,.<>+-*/&|^~@")
            if code_chars < 3 and len(words) > 8:
                continue

        result.append(line)

    return "\n".join(result)


def _remove_prefix_echo(text, prefix):
    """Remove echoed prefix lines from the start of the completion."""
    if not prefix:
        return text
    prefix_lines = prefix.rstrip().split("\n")
    for pline in prefix_lines[-3:]:
        pclean = pline.strip()
        if pclean and text.startswith(pclean):
            text = text[len(pclean):].lstrip("\n")
    return text


def _enforce_limits(text, max_lines, max_chars):
    """Enforce line and character limits."""
    # Cut at triple newline
    if "\n\n\n" in text:
        text = text.split("\n\n\n")[0]

    # Cut at double newline if next block is unindented (new definition)
    parts = text.split("\n\n")
    if len(parts) > 1:
        second = parts[1].lstrip("\n")
        if second and second[0] not in " \t":
            text = parts[0]

    # Line limit
    lines = text.split("\n")
    if len(lines) > max_lines:
        text = "\n".join(lines[:max_lines])

    # Char limit — cut at last complete line
    if len(text) > max_chars:
        cut = text[:max_chars]
        nl = cut.rfind("\n")
        if nl > 0:
            text = cut[:nl]
        else:
            text = cut

    return text
