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

    # 8. Minimum viable completion
    if len(text.strip()) < 2:
        print("[OllamaComplete] Cleaner: too short after limits")
        return ""

    print("[OllamaComplete] Cleaner result ({} chars): {}".format(
        len(text), repr(text[:150])
    ))
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
