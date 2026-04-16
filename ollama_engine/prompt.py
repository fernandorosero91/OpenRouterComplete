"""
FIM (Fill-In-the-Middle) prompt builders.
Falls back to completion-style prompts when FIM isn't appropriate.
"""


def build(prefix, suffix, fim_format, mcfg):
    """Build the optimal prompt for the given format and context."""
    max_pre_chars = mcfg.get("max_prefix_chars", 1000)
    max_suf_chars = mcfg.get("max_suffix_chars", 200)
    max_pre_lines = mcfg.get("max_prefix_lines", 18)
    max_suf_lines = mcfg.get("max_suffix_lines", 4)

    prefix = _trim_prefix(prefix, max_pre_chars, max_pre_lines)
    suffix = _trim_suffix(suffix, max_suf_chars, max_suf_lines)

    # Check if suffix has meaningful code
    has_suffix = bool(suffix.strip())

    builders = {
        "codellama": _codellama,
        "deepseek": _deepseek,
        "qwen": _qwen,
        "starcoder": _starcoder,
        "completion": _completion,
    }
    fn = builders.get(fim_format, _completion)
    result = fn(prefix, suffix, has_suffix)
    print("[OllamaComplete] Prompt fmt={} suffix={} len={}".format(
        fim_format, has_suffix, len(result)
    ))
    return result


def _trim_prefix(text, max_chars, max_lines):
    """Trim prefix: keep last N lines within char budget."""
    if not text:
        return ""
    if len(text) <= max_chars:
        lines = text.split("\n")
        if len(lines) <= max_lines:
            return text
        return "\n".join(lines[-max_lines:])

    lines = text.split("\n")
    result = []
    total = 0
    for line in reversed(lines):
        cost = len(line) + 1
        if total + cost > max_chars:
            break
        if len(result) >= max_lines:
            break
        result.append(line)
        total += cost
    result.reverse()
    return "\n".join(result)


def _trim_suffix(text, max_chars, max_lines):
    """Trim suffix: keep first N lines within char budget."""
    if not text:
        return ""
    if len(text) <= max_chars:
        lines = text.split("\n")
        if len(lines) <= max_lines:
            return text
        return "\n".join(lines[:max_lines])

    lines = text.split("\n")
    result = []
    total = 0
    for line in lines:
        cost = len(line) + 1
        if total + cost > max_chars:
            break
        if len(result) >= max_lines:
            break
        result.append(line)
        total += cost
    return "\n".join(result)


# ─── Format-specific builders ────────────────────────────────

def _codellama(prefix, suffix, has_suffix):
    """CodeLlama SPM format.
    When there's no suffix, use plain prefix completion —
    CodeLlama code models handle raw prefix continuation well.
    """
    if has_suffix:
        return "<PRE> {0} <SUF>{1} <MID>".format(prefix, suffix)
    # No suffix: just let the model continue from prefix
    return prefix


def _deepseek(prefix, suffix, has_suffix):
    """DeepSeek Coder FIM format."""
    if has_suffix:
        return "<|fim\u2581begin|>{0}<|fim\u2581hole|>{1}<|fim\u2581end|>".format(
            prefix, suffix
        )
    return "<|fim\u2581begin|>{0}<|fim\u2581hole|><|fim\u2581end|>".format(prefix)


def _qwen(prefix, suffix, has_suffix):
    """Qwen2.5-Coder FIM format."""
    if has_suffix:
        return "<|fim_prefix|>{0}<|fim_suffix|>{1}<|fim_middle|>".format(
            prefix, suffix
        )
    return "<|fim_prefix|>{0}<|fim_suffix|><|fim_middle|>".format(prefix)


def _starcoder(prefix, suffix, has_suffix):
    """StarCoder FIM format."""
    if has_suffix:
        return "<fim_prefix>{0}<fim_suffix>{1}<fim_middle>".format(prefix, suffix)
    return "<fim_prefix>{0}<fim_suffix><fim_middle>".format(prefix)


def _completion(prefix, suffix, has_suffix):
    """Plain completion — for models without FIM support (e.g. Gemma, Llama).
    Uses a code-continuation prompt.
    """
    return prefix
