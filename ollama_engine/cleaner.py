"""
Response cleaner — sanitizes raw LLM output into pure code.
Much less aggressive than before. Scales with model capability.
The goal: keep valid code, only strip obvious junk.
"""
import re

# ─── Junk tokens to strip ────────────────────────────────────

_JUNK_TOKENS = [
    "<|endoftext|>", "<|fim_suffix|>", "<|fim_prefix|>", "<|fim_middle|>",
    "<EOT>", "</s>", "<s>", "[INST]", "[/INST]",
    "<PRE>", "<SUF>", "<MID>", "<FILL_HERE>",
    "<|eot_id|>", "<|im_end|>", "<|im_start|>", "<|end|>",
    "<fim_prefix>", "<fim_suffix>", "<fim_middle>",
    "<|fim▁begin|>", "<|fim▁hole|>", "<|fim▁end|>",
    "<|assistant|>", "<|user|>",
    "<|repo_name|>", "<|file_sep|>",
]

# ─── Patterns that signal "this is explanation, not code" ────

_EXPLANATION_BLOCK_RE = re.compile(
    r"\n\n(?:"
    r"(?:It looks|However|Note that|This code|The code|Here is|Here\'s)"
    r"|(?:Esta función|Parece que|Sin embargo|Nota|Este código|Aquí está)"
    r"|(?:Explanation|Note|Example|Usage|Output|Result)"
    r"|(?:Explicación|Nota|Ejemplo|Uso|Salida|Resultado)"
    r"|(?:Let me|I will|You can|We can|This will|This should)"
    r"|(?:The above|The following|As you can see)"
    r")",
    re.IGNORECASE,
)

_MARKDOWN_FENCE_RE = re.compile(r"```[a-zA-Z]*\n?")


def clean(raw, prefix, mcfg):
    """Clean raw LLM output. Returns code string or empty."""
    if not raw:
        print("[OllamaComplete] Cleaner: raw is empty")
        return ""

    max_lines = mcfg.get("max_output_lines", 10)
    max_chars = mcfg.get("max_output_chars", 400)

    text = raw
    print("[OllamaComplete] Cleaner raw ({} chars): {}".format(
        len(raw), repr(raw[:200])
    ))

    # 1. Strip junk tokens
    for tok in _JUNK_TOKENS:
        text = text.replace(tok, "")

    # 2. Strip markdown code fences
    text = _MARKDOWN_FENCE_RE.sub("", text)
    text = text.replace("```", "")

    # 3. Handle leading whitespace carefully
    # If the raw starts with newline + indent, that's the model giving us
    # the next line with proper indentation — preserve it
    text = text.rstrip()
    # Strip leading blank lines but keep indentation of first code line
    while text.startswith("\n"):
        text = text[1:]

    if not text:
        print("[OllamaComplete] Cleaner: empty after token/fence strip")
        return ""

    # 4. Cut at explanation blocks
    m = _EXPLANATION_BLOCK_RE.search(text)
    if m:
        text = text[:m.start()].rstrip()

    # 5. Cut at triple newline
    idx = text.find("\n\n\n")
    if idx >= 0:
        text = text[:idx].rstrip()

    # 6. Remove echoed prefix (model repeating what's already there)
    text = _remove_prefix_echo(text, prefix)

    if not text.strip():
        print("[OllamaComplete] Cleaner: empty after echo removal")
        return ""

    # 7. Enforce limits
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

    # 8. Adapt indentation to match the file's style
    text = _adapt_indentation(text, prefix)

    # 9. Minimum viable completion
    if len(text.strip()) < 2:
        print("[OllamaComplete] Cleaner: too short after limits")
        return ""

    print("[OllamaComplete] Cleaner result ({} chars): {}".format(
        len(text), repr(text[:150])
    ))
    return text


def _adapt_indentation(text, prefix):
    """Match the indentation style of the file (tabs vs spaces)."""
    if not prefix or not text:
        return text

    # Detect file's indent style from prefix
    uses_tabs = False
    uses_spaces = False
    space_size = 4

    for line in prefix.split("\n"):
        if line.startswith("\t"):
            uses_tabs = True
        elif line.startswith("    "):
            uses_spaces = True
            # Detect space width
            stripped = line.lstrip(" ")
            indent = len(line) - len(stripped)
            if indent > 0 and indent < space_size:
                space_size = indent

    if not space_size:
        space_size = 4

    if uses_spaces and not uses_tabs:
        # File uses spaces — convert tabs in output to spaces
        text = text.replace("\t", " " * space_size)
    elif uses_tabs and not uses_spaces:
        # File uses tabs — convert leading spaces to tabs
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

    # Get last few lines of prefix
    prefix_lines = prefix.rstrip().split("\n")
    check_lines = prefix_lines[-3:]

    for pline in check_lines:
        pclean = pline.strip()
        if not pclean:
            continue
        # If completion starts with an exact prefix line, remove it
        if text.lstrip("\n").startswith(pclean):
            text = text.lstrip("\n")[len(pclean):]
            # Remove the newline right after if present
            if text.startswith("\n"):
                text = text[1:]

    return text
