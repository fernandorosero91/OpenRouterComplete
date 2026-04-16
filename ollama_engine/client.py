"""
HTTP client for Ollama API.
Uses urllib (reliable in Sublime Text's Python) with proper error handling.
No bare excepts. Thread-safe warm tracking.
"""
import urllib.request
import urllib.error
import json
import threading

_OLLAMA_BASE = "http://localhost:11434"

_warmed = set()
_warm_lock = threading.Lock()


def _post(path, payload, timeout=30):
    """POST JSON to Ollama, return parsed response dict."""
    url = _OLLAMA_BASE + path
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    # Compatible with both Python 3.3 and 3.8 in Sublime Text
    req.get_method = lambda: "POST"
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get(path, timeout=5):
    """GET from Ollama, return parsed response dict or None."""
    url = _OLLAMA_BASE + path
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


# ─── Public API ───────────────────────────────────────────────

def is_running():
    """Check if Ollama is reachable."""
    return _get("/api/tags", timeout=3) is not None


def list_models():
    """Get list of installed model names."""
    result = _get("/api/tags", timeout=5)
    if not result:
        return []
    return [m["name"] for m in result.get("models", [])]


def warm(model):
    """Pre-load model into RAM with a tiny dummy request."""
    with _warm_lock:
        if model in _warmed:
            return

    try:
        _post("/api/generate", {
            "model": model,
            "prompt": "def f():",
            "stream": False,
            "options": {
                "num_predict": 1,
                "temperature": 0.0,
                "num_ctx": 256,
            }
        }, timeout=120)
        with _warm_lock:
            _warmed.add(model)
    except Exception as e:
        print("[OllamaComplete] Warm-up failed: {}".format(e))


def generate(prompt_text, model, mcfg):
    """Generate a completion. Returns raw response text."""
    stop = _stop_tokens(mcfg["fim_format"])

    payload = {
        "model": model,
        "prompt": prompt_text,
        "stream": False,
        "options": {
            "num_predict": mcfg["max_tokens"],
            "temperature": mcfg["temperature"],
            "top_p": mcfg["top_p"],
            "repeat_penalty": mcfg["repeat_penalty"],
            "stop": stop,
            "num_ctx": mcfg["num_ctx"],
            "num_thread": mcfg["num_thread"],
            "num_batch": mcfg["num_batch"],
            "num_gpu": 0,
        }
    }

    result = _post("/api/generate", payload, timeout=mcfg["timeout"])
    return result.get("response", "")


# ─── Stop tokens per FIM format ──────────────────────────────

def _stop_tokens(fim_format):
    _MAP = {
        "codellama": [
            "<EOT>", "</s>", "<|endoftext|>",
            "\n\n\n", "\n\n",
        ],
        "deepseek": [
            "<|fim_suffix|>", "<|fim_prefix|>", "<|fim_middle|>",
            "<|endoftext|>", "<EOT>", "</s>",
            "\n\n\n", "\n\n",
        ],
        "qwen": [
            "<|fim_suffix|>", "<|fim_prefix|>", "<|fim_middle|>",
            "<|im_end|>", "<|endoftext|>",
            "\n\n\n", "\n\n",
        ],
        "starcoder": [
            "<fim_suffix>", "<fim_prefix>", "<fim_middle>",
            "<|endoftext|>",
            "\n\n\n", "\n\n",
        ],
    }
    return _MAP.get(fim_format, _MAP["codellama"])
