"""
Cliente optimizado para Ollama con caché inteligente
"""
import urllib.request
import urllib.error
import json
import hashlib
import threading

from .ollama_config import get_model_config, get_stop_tokens

# Caché simple para completions repetidas
_completion_cache = {}
_cache_max_size = 50
_model_warmed = {}


def _get_cache_key(prompt, model):
    """Genera clave de caché."""
    content = "{0}:{1}".format(model, prompt)
    return hashlib.md5(content.encode()).hexdigest()


def _get_from_cache(prompt, model):
    """Obtiene del caché si existe."""
    key = _get_cache_key(prompt, model)
    return _completion_cache.get(key)


def _save_to_cache(prompt, model, result):
    """Guarda en caché."""
    key = _get_cache_key(prompt, model)
    _completion_cache[key] = result
    
    # Limitar tamaño del caché
    if len(_completion_cache) > _cache_max_size:
        # Eliminar el más antiguo (FIFO simple)
        oldest = next(iter(_completion_cache))
        del _completion_cache[oldest]


def warm_model(model):
    """Pre-calienta el modelo para reducir latencia inicial."""
    if model in _model_warmed:
        return
    
    def _warm():
        try:
            # Hacer una llamada dummy pequeña
            payload = json.dumps({
                "model": model,
                "prompt": "def ",
                "stream": False,
                "options": {
                    "num_predict": 5,
                    "temperature": 0.0,
                    "num_ctx": 512,
                }
            }).encode("utf-8")
            
            req = urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            req.get_method = lambda: "POST"
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
            
            _model_warmed[model] = True
        except:
            pass
    
    thread = threading.Thread(target=_warm)
    thread.daemon = True
    thread.start()


def call_ollama(prompt, model, use_cache=True):
    """Llama a Ollama con configuración optimizada y caché."""
    # Intentar caché primero
    if use_cache:
        cached = _get_from_cache(prompt, model)
        if cached is not None:
            return cached
    
    config = get_model_config(model)
    fim_format = config.get("fim_format", "codellama")
    stop_tokens = get_stop_tokens(fim_format)
    
    # Payload ultra optimizado
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": config["max_tokens"],
            "temperature": config["temperature"],
            "top_p": config["top_p"],
            "repeat_penalty": config["repeat_penalty"],
            "stop": stop_tokens,
            "num_ctx": config["num_ctx"],
            "num_thread": 6,  # Usar más threads en i7
            "num_batch": 256,  # Batch más grande para velocidad
            "num_gpu": 0,  # Sin GPU
        }
    }).encode("utf-8")
    
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    req.get_method = lambda: "POST"
    
    timeout = config["timeout"]
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        result = data.get("response", "")
        
        # Guardar en caché
        if use_cache and result:
            _save_to_cache(prompt, model, result)
        
        return result


def check_ollama_running():
    """Verifica si Ollama está corriendo."""
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return True
    except:
        return False


def get_ollama_models():
    """Obtiene lista de modelos instalados."""
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [m["name"] for m in data.get("models", [])]
    except:
        return []
