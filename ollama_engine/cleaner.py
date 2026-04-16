"""
Response cleaner — sanitizes raw LLM output into pure code.
Detects and rejects explanation/chat responses immediately.
"""
import re

# ─── Junk tokens to strip ────────────────────────────────────

_JUNK_TOKENS = [
    "<|endoftext|>", "<|fim_suffix|>", "<|fim_prefix|>", "<|fim_middle|>",
    "<EOT>", "</s>", "<s>", "[INST]", "[/INST]",
    "<PRE>", "<SUF>", "<MID>", "<FILL_HERE>",
    "<|eot_id|>", "<|im_end|>", "<|im_start|>", "<|end|>",
    "<fim_prefix>", "<fim_suffix>", "<fim_middle>",
    "<|assistant|>", "<|user|>",
    "<|repo_name|>", "<|file_sep|>",
]

# ─── Detect if the output is explanation instead of code ─────

_EXPLANATION_STARTERS = (
    "it looks", "it seems", "it appears",
    "however", "note that", "note:",
    "this code", "the code", "here is", "here's", "here are",
    "this function", "the function",
    "you can", "you need", "you should", "you might",
    "we can", "we need",
    "let me", "i will", "i'll",
    "this will", "this should",
    "the above", "the following", "as you can see",
    "sure", "certainly", "of course",
    "to fix", "to solve", "to implement",
    "explanation", "example", "usage", "output", "result",
    # Spanish
    "parece que", "sin embargo", "nota:", "esta función",
    "el código", "este código", "aquí está", "puedes",
    "necesitas", "deberías", "explicación", "ejemplo",
)

_MARKDOWN_FENCE_RE = re.compile(r"```[a-zA-Z]*\n?")

# ─── Patterns that signal explanation block mid-text ─────────

_EXPLANATION_BLOCK_RE = re.compile(
    r"\n\n(?:"
    r"(?:It looks|However|Note that|This code|The code|Here is|Here\'s)"
    r"|(?:Esta función|Parece que|Sin embargo|Nota|Este código|Aquí está)"
    r"|(?:Explanation|Note|Example|Usage|Output|Result)"
    r"|(?:Explicación|Nota|Ejemplo|Uso|Salida|Resultado)"
    r"|(?:Let me|I will|You can|We can|This will|This should)"
    r"|(?:The above|The following|As you can see)"
    r"|(?:Sure|Certainly|Of course)"
    r"|(?:To fix|To solve|To implement)"
    r")",
    re.IGNORECASE,
)


def clean(raw, prefix, mcfg):
    """Clean raw LLM output. Returns code string or empty."""
    if not raw:
        return ""

    max_lines = mcfg.get("max_output_lines", 10)
    max_chars = mcfg.get("max_output_chars", 400)

    text = raw

    # 1. Strip junk tokens
    for tok in _JUNK_TOKENS:
        text = text.replace(tok, "")

    # 2. Strip markdown code fences
    text = _MARKDOWN_FENCE_RE.sub("", text)
    text = text.replace("```", "")

    # 3. Clean whitespace
    text = text.rstrip()
    while text.startswith("\n"):
        text = text[1:]

    if not text:
        return ""

    # 4. CRITICAL: Detect if the entire output is explanation, not code
    first_content = text.lstrip().lower()
    if any(first_content.startswith(s) for s in _EXPLANATION_STARTERS):
        code = _extract_code_from_markdown(raw)
        if code:
            text = code
        else:
            return ""

    # 5. Cut at explanation blocks mid-text
    m = _EXPLANATION_BLOCK_RE.search(text)
    if m:
        text = text[:m.start()].rstrip()

    # 6. Cut at triple newline
    idx = text.find("\n\n\n")
    if idx >= 0:
        text = text[:idx].rstrip()

    # 7. Remove echoed prefix
    text = _remove_prefix_echo(text, prefix)

    if not text.strip():
        return ""

    # 8. Enforce limits
    lines = text.split("\n")
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        text = "\n".join(lines)

    if len(text) > max_chars:
        cut = text[:max_chars]
        nl = cut.rfind("\n")
        if nl > 0:
            text = cut[:nl]
        else:
            text = cut

    text = text.rstrip()

    # 9. Adapt indentation
    text = _adapt_indentation(text, prefix)

    # 10. Minimum viable completion
    if len(text.strip()) < 2:
        return ""

    return text


def _extract_code_from_markdown(raw):
    """If the model wrapped code in markdown fences, extract it."""
    # Find ```python\n...\n``` or ```\n...\n```
    pattern = re.compile(r"```(?:python|javascript|java|cpp|c|html|css|typescript|go|rust)?\s*\n(.*?)```", re.DOTALL)
    m = pattern.search(raw)
    if m:
        code = m.group(1).strip()
        if code and len(code) > 5:
            return code
    return None


def _adapt_indentation(text, prefix):
    """Match the indentation style of the file (tabs vs spaces)."""
    if not prefix or not text:
        return text

    uses_tabs = False
    uses_spaces = False
    space_size = 4

    for line in prefix.split("\n"):
        if line.startswith("\t"):
            uses_tabs = True
        elif line.startswith("    "):
            uses_spaces = True
            stripped = line.lstrip(" ")
            indent = len(line) - len(stripped)
            if 0 < indent < space_size:
                space_size = indent

    if not space_size:
        space_size = 4

    if uses_spaces and not uses_tabs:
        text = text.replace("\t", " " * space_size)
    elif uses_tabs and not uses_spaces:
        lines = text.split("\n")
        result = []
        for line in lines:
            stripped = line.lstrip(" ")
            n_spaces = len(line) - len(stripped)
            if n_spaces >= space_size:
                n_tabs = n_spaces // space_size
                remainder = n_spaces % space_size
                result.append("\t" * n_tabs + " " * remainder + stripped)
            else:
                result.append(line)
        text = "\n".join(result)

    return text


def _remove_prefix_echo(text, prefix):
    """Remove lines from the start of completion that echo the prefix."""
    if not prefix:
        return text

    prefix_lines = prefix.rstrip().split("\n")
    check_lines = prefix_lines[-3:]

    for pline in check_lines:
        pclean = pline.strip()
        if not pclean:
            continue
        if text.lstrip("\n").startswith(pclean):
            text = text.lstrip("\n")[len(pclean):]
            if text.startswith("\n"):
                text = text[1:]

    return text
