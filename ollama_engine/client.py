"""
HTTP client for Ollama API.
Supports both streaming and non-streaming generation.
Uses urllib (reliable in Sublime Text's Python).
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
    req.get_method = lambda: "POST"
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post_stream(path, payload, timeout=30):
    """POST JSON to Ollama with streaming. Yields response chunks."""
    url = _OLLAMA_BASE + path
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    req.get_method = lambda: "POST"
    resp = urllib.request.urlopen(req, timeout=timeout)
    try:
        buf = b""
        while True:
            chunk = resp.read(1)
            if not chunk:
                break
            buf += chunk
            if chunk == b"\n":
                line = buf.strip()
                buf = b""
                if line:
                    try:
                        data = json.loads(line.decode("utf-8"))
                        yield data
                        if data.get("done", False):
                            break
                    except (ValueError, UnicodeDecodeError):
                        continue
    finally:
        resp.close()


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
            "prompt": "def f():\n    return",
            "stream": False,
            "options": {
                "num_predict": 5,
                "temperature": 0.0,
                "num_ctx": 256,
            }
        }, timeout=120)
        with _warm_lock:
            _warmed.add(model)
    except Exception as e:
        print("[OllamaComplete] Warm-up failed: {}".format(e))


def generate(prompt_text, model, mcfg):
    """Generate a completion (non-streaming). Returns raw response text."""
    stop = _stop_tokens(mcfg["fim_format"])

    payload = {
        "model": model,
        "prompt": prompt_text,
        "stream": False,
        "raw": True,  # bypass Ollama's chat template for FIM
        "options": _build_options(mcfg, stop),
    }

    result = _post("/api/generate", payload, timeout=mcfg["timeout"])
    return result.get("response", "")


def generate_stream(prompt_text, model, mcfg, on_chunk, on_done, is_cancelled):
    """Generate with streaming. Calls on_chunk(text_so_far) as tokens arrive.
    Calls on_done(full_text) when complete.
    is_cancelled() should return True to abort.
    """
    stop = _stop_tokens(mcfg["fim_format"])

    payload = {
        "model": model,
        "prompt": prompt_text,
        "stream": True,
        "raw": True,  # CRITICAL: bypass Ollama's chat template for FIM
        "options": _build_options(mcfg, stop),
    }

    full_text = ""
    try:
        for data in _post_stream("/api/generate", payload, timeout=mcfg["timeout"]):
            if is_cancelled():
                break
            token = data.get("response", "")
            if token:
                full_text += token
                on_chunk(full_text)
            if data.get("done", False):
                break
    except Exception as e:
        if not is_cancelled():
            raise e

    on_done(full_text)
    return full_text


def _build_options(mcfg, stop):
    return {
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


# ─── Stop tokens per FIM format ──────────────────────────────

def _stop_tokens(fim_format):
    """Stop tokens — only real end-of-generation markers."""
    _MAP = {
        "codellama": [
            "<EOT>", "</s>", "<|endoftext|>",
            "<PRE>", "<SUF>", "<MID>",
        ],
        "deepseek": [
            "<|fim_suffix|>", "<|fim_prefix|>", "<|fim_middle|>",
            "<|endoftext|>", "<EOT>", "</s>",
        ],
        "qwen": [
            "<|fim_suffix|>", "<|fim_prefix|>", "<|fim_middle|>",
            "<|im_end|>", "<|endoftext|>",
            "<|repo_name|>", "<|file_sep|>",
        ],
        "starcoder": [
            "<fim_suffix>", "<fim_prefix>", "<fim_middle>",
            "<|endoftext|>",
        ],
        "completion": [
            "<|endoftext|>", "<|im_end|>", "</s>", "<eos>",
            "<end_of_turn>",
        ],
    }
    return _MAP.get(fim_format, _MAP["completion"])
