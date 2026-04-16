"""
Model configuration — tuned for CPU-only i5 + 32GB RAM.
Balanced for speed AND quality. No GPU.
"""
import sublime

# ─── Model Profiles ───────────────────────────────────────────

_PROFILES = {
    # ── Gemma (NOT a FIM model — uses plain completion) ──
    "gemma4:e2b": {
        "max_tokens": 200,
        "temperature": 0.0,
        "top_p": 0.95,
        "repeat_penalty": 1.1,
        "timeout": 120,
        "num_ctx": 1024,
        "num_thread": 6,
        "num_batch": 256,
        "fim_format": "completion",
        "max_prefix_chars": 1500,
        "max_suffix_chars": 300,
        "max_prefix_lines": 25,
        "max_suffix_lines": 5,
        "max_output_lines": 30,
        "max_output_chars": 1200,
    },

    # ── Qwen2.5-Coder family ──
    "qwen2.5-coder:0.5b": {
        "max_tokens": 120,
        "temperature": 0.0,
        "top_p": 0.95,
        "repeat_penalty": 1.2,
        "timeout": 25,
        "num_ctx": 512,
        "num_thread": 8,
        "num_batch": 512,
        "fim_format": "qwen",
        "max_prefix_chars": 600,
        "max_suffix_chars": 150,
        "max_prefix_lines": 12,
        "max_suffix_lines": 3,
        "max_output_lines": 15,
        "max_output_chars": 600,
    },
    "qwen2.5-coder:1.5b": {
        "max_tokens": 150,
        "temperature": 0.0,
        "top_p": 0.95,
        "repeat_penalty": 1.15,
        "timeout": 45,
        "num_ctx": 768,
        "num_thread": 8,
        "num_batch": 512,
        "fim_format": "qwen",
        "max_prefix_chars": 900,
        "max_suffix_chars": 200,
        "max_prefix_lines": 18,
        "max_suffix_lines": 4,
        "max_output_lines": 20,
        "max_output_chars": 800,
    },
    "qwen2.5-coder:3b": {
        "max_tokens": 100,
        "temperature": 0.0,
        "top_p": 0.95,
        "repeat_penalty": 1.1,
        "timeout": 40,
        "num_ctx": 1024,
        "num_thread": 8,
        "num_batch": 512,
        "fim_format": "qwen",
        "max_prefix_chars": 1200,
        "max_suffix_chars": 300,
        "max_prefix_lines": 20,
        "max_suffix_lines": 5,
        "max_output_lines": 15,
        "max_output_chars": 600,
    },
    "qwen2.5-coder:7b": {
        "max_tokens": 120,
        "temperature": 0.0,
        "top_p": 0.95,
        "repeat_penalty": 1.1,
        "timeout": 60,
        "num_ctx": 1024,
        "num_thread": 6,
        "num_batch": 256,
        "fim_format": "qwen",
        "max_prefix_chars": 1500,
        "max_suffix_chars": 300,
        "max_prefix_lines": 25,
        "max_suffix_lines": 6,
        "max_output_lines": 20,
        "max_output_chars": 800,
    },

    # ── DeepSeek Coder ──
    "deepseek-coder:1.3b": {
        "max_tokens": 150,
        "temperature": 0.0,
        "top_p": 0.95,
        "repeat_penalty": 1.15,
        "timeout": 45,
        "num_ctx": 768,
        "num_thread": 8,
        "num_batch": 512,
        "fim_format": "deepseek",
        "max_prefix_chars": 900,
        "max_suffix_chars": 200,
        "max_prefix_lines": 18,
        "max_suffix_lines": 4,
        "max_output_lines": 20,
        "max_output_chars": 800,
    },
    "deepseek-coder:6.7b": {
        "max_tokens": 120,
        "temperature": 0.0,
        "top_p": 0.95,
        "repeat_penalty": 1.1,
        "timeout": 60,
        "num_ctx": 1024,
        "num_thread": 6,
        "num_batch": 256,
        "fim_format": "deepseek",
        "max_prefix_chars": 1500,
        "max_suffix_chars": 300,
        "max_prefix_lines": 25,
        "max_suffix_lines": 6,
        "max_output_lines": 20,
        "max_output_chars": 800,
    },
    "deepseek-coder-v2:16b": {
        "max_tokens": 150,
        "temperature": 0.0,
        "top_p": 0.9,
        "repeat_penalty": 1.1,
        "timeout": 90,
        "num_ctx": 1024,
        "num_thread": 6,
        "num_batch": 256,
        "fim_format": "deepseek",
        "max_prefix_chars": 1500,
        "max_suffix_chars": 300,
        "max_prefix_lines": 25,
        "max_suffix_lines": 6,
        "max_output_lines": 20,
        "max_output_chars": 800,
    },

    # ── CodeLlama ──
    "codellama:7b-code": {
        "max_tokens": 200,
        "temperature": 0.0,
        "top_p": 1.0,
        "repeat_penalty": 1.15,
        "timeout": 120,
        "num_ctx": 1024,
        "num_thread": 6,
        "num_batch": 256,
        "fim_format": "codellama",
        "max_prefix_chars": 1500,
        "max_suffix_chars": 300,
        "max_prefix_lines": 25,
        "max_suffix_lines": 5,
        "max_output_lines": 30,
        "max_output_chars": 1200,
    },
    "codellama:13b-code": {
        "max_tokens": 200,
        "temperature": 0.0,
        "top_p": 1.0,
        "repeat_penalty": 1.1,
        "timeout": 120,
        "num_ctx": 1024,
        "num_thread": 6,
        "num_batch": 256,
        "fim_format": "codellama",
        "max_prefix_chars": 1500,
        "max_suffix_chars": 300,
        "max_prefix_lines": 25,
        "max_suffix_lines": 6,
        "max_output_lines": 30,
        "max_output_chars": 1200,
    },

    # ── StarCoder2 ──
    "starcoder2:3b": {
        "max_tokens": 100,
        "temperature": 0.0,
        "top_p": 0.95,
        "repeat_penalty": 1.1,
        "timeout": 40,
        "num_ctx": 1024,
        "num_thread": 8,
        "num_batch": 512,
        "fim_format": "starcoder",
        "max_prefix_chars": 1200,
        "max_suffix_chars": 300,
        "max_prefix_lines": 20,
        "max_suffix_lines": 5,
        "max_output_lines": 15,
        "max_output_chars": 600,
    },
    "starcoder2:7b": {
        "max_tokens": 120,
        "temperature": 0.0,
        "top_p": 0.95,
        "repeat_penalty": 1.1,
        "timeout": 60,
        "num_ctx": 1024,
        "num_thread": 6,
        "num_batch": 256,
        "fim_format": "starcoder",
        "max_prefix_chars": 1500,
        "max_suffix_chars": 300,
        "max_prefix_lines": 25,
        "max_suffix_lines": 6,
        "max_output_lines": 20,
        "max_output_chars": 800,
    },
}

# ─── Default fallback ─────────────────────────────────────────

_DEFAULT = {
    "max_tokens": 80,
    "temperature": 0.0,
    "top_p": 0.95,
    "repeat_penalty": 1.15,
    "timeout": 45,
    "num_ctx": 768,
    "num_thread": 6,
    "num_batch": 256,
    "fim_format": "completion",
    "max_prefix_chars": 1200,
    "max_suffix_chars": 250,
    "max_prefix_lines": 20,
    "max_suffix_lines": 5,
    "max_output_lines": 15,
    "max_output_chars": 600,
}


def get_active_model():
    """Read the active model from settings."""
    s = sublime.load_settings("OllamaComplete.sublime-settings")
    return s.get("model", "codellama:7b-code")


def for_model(model):
    """Get the optimized config dict for a model."""
    # Exact match
    if model in _PROFILES:
        return _PROFILES[model]

    # Fuzzy match by base name
    model_low = model.lower()
    for key, cfg in _PROFILES.items():
        base = key.split(":")[0]
        if base in model_low:
            return cfg

    return _DEFAULT.copy()
