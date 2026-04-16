"""
FIM (Fill-In-the-Middle) prompt builders.
Each model family has its own special token format.
Context is trimmed by lines (not just chars) for cleaner cuts.
"""


def build(prefix, suffix, fim_format, mcfg):
    """Build the optimal FIM prompt for the given format."""
    max_pre_chars = mcfg.get("max_prefix_chars", 1000)
    max_suf_chars = mcfg.get("max_suffix_chars", 200)
    max_pre_lines = mcfg.get("max_prefix_lines", 18)
    max_suf_lines = mcfg.get("max_suffix_lines", 4)

    prefix = _trim_prefix(prefix, max_pre_chars, max_pre_lines)
    suffix = _trim_suffix(suffix, max_suf_chars, max_suf_lines)

    builders = {
        "codellama": _codellama,
        "deepseek": _deepseek,
        "qwen": _qwen,
        "starcoder": _starcoder,
    }
    fn = builders.get(fim_format, _codellama)
    return fn(prefix, suffix)


def _trim_prefix(text, max_chars, max_lines):
    """Trim prefix: keep last N lines within char budget."""
    if len(text) <= max_chars:
        lines = text.split("\n")
        if len(lines) <= max_lines:
            return text
        return "\n".join(lines[-max_lines:])

    # Over char budget — trim by lines from the end
    lines = text.split("\n")
    result = []
    total = 0
    for line in reversed(lines):
        if total + len(line) + 1 > max_chars:
            break
        if len(result) >= max_lines:
            break
        result.append(line)
        total += len(line) + 1
    result.reverse()
    return "\n".join(result)


def _trim_suffix(text, max_chars, max_lines):
    """Trim suffix: keep first N lines within char budget."""
    if len(text) <= max_chars:
        lines = text.split("\n")
        if len(lines) <= max_lines:
            return text
        return "\n".join(lines[:max_lines])

    lines = text.split("\n")
    result = []
    total = 0
    for line in lines:
        if total + len(line) + 1 > max_chars:
            break
        if len(result) >= max_lines:
            break
        result.append(line)
        total += len(line) + 1
    return "\n".join(result)


# ─── Format-specific builders ────────────────────────────────

def _codellama(prefix, suffix):
    """CodeLlama SPM format."""
    return "<PRE> {} <SUF>{} <MID>".format(prefix, suffix)


def _deepseek(prefix, suffix):
    """DeepSeek FIM format."""
    return "<|fim_prefix|>{}<|fim_suffix|>{}<|fim_middle|>".format(prefix, suffix)


def _qwen(prefix, suffix):
    """Qwen FIM format."""
    return "<|fim_prefix|>{}<|fim_suffix|>{}<|fim_middle|>".format(prefix, suffix)


def _starcoder(prefix, suffix):
    """StarCoder FIM format."""
    return "<fim_prefix>{}<fim_suffix>{}<fim_middle>".format(prefix, suffix)
