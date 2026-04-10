"""
OllamaComplete - Autocompletado Profesional con IA Local
Optimizado para todos los modelos Ollama (pequeños y grandes)
Similar a GitHub Copilot para Sublime Text 4

Características:
- Texto fantasma inline estilo Copilot
- Optimización específica por modelo
- Contexto inteligente del proyecto
- Detección automática de frameworks
- Prompts FIM nativos optimizados
- Limpieza agresiva de explicaciones
"""

import sublime
import sublime_plugin
import urllib.request
import urllib.error
import json
import threading
import os
import re

# Estado global del plugin
_state = {
    "pending_thread": None,
    "suggestion": None,
    "cursor_point": None,
    "view_id": None,
    "request_id": 0,
    "phantom_set": {},
    "last_completion_time": 0,
    "auto_trigger_timer": None,
}

PHANTOM_KEY = "ollama_complete_phantom"
STATUS_KEY = "ollama_complete"

# ---------------------------------------------------------------------------
# Configuración por Modelo (Optimizado para cada modelo)
# ---------------------------------------------------------------------------

MODEL_CONFIGS = {
    # Modelos pequeños (0.5B-3B) - Configuración ULTRA AGRESIVA
    "qwen2.5-coder:0.5b": {
        "max_tokens": 30,  # MUY BAJO para evitar divagaciones
        "temperature": 0.0,  # Sin creatividad
        "top_p": 0.85,
        "repeat_penalty": 1.2,  # Alto para evitar repeticiones
        "timeout": 30,
        "num_ctx": 512,  # Contexto MUY reducido
        "fim_format": "qwen",
        "use_raw_completion": True,  # Usar solo el código sin procesar
    },
    "qwen2.5-coder:1.5b": {
        "max_tokens": 40,
        "temperature": 0.0,
        "top_p": 0.85,
        "repeat_penalty": 1.15,
        "timeout": 40,
        "num_ctx": 1024,
        "fim_format": "qwen",
        "use_raw_completion": True,
    },
    "deepseek-coder:1.3b": {
        "max_tokens": 40,
        "temperature": 0.0,
        "top_p": 0.85,
        "repeat_penalty": 1.15,
        "timeout": 40,
        "num_ctx": 1024,
        "fim_format": "deepseek",
        "use_raw_completion": True,
    },
    "codegemma:2b": {
        "max_tokens": 35,
        "temperature": 0.0,
        "top_p": 0.85,
        "repeat_penalty": 1.15,
        "timeout": 35,
        "num_ctx": 1024,
        "fim_format": "simple",
        "use_raw_completion": True,
    },
    "starcoder2:3b": {
        "max_tokens": 60,
        "temperature": 0.05,
        "top_p": 0.9,
        "repeat_penalty": 1.1,
        "timeout": 40,
        "num_ctx": 2048,
        "fim_format": "starcoder",
        "use_raw_completion": False,
    },
    "granite-code:3b": {
        "max_tokens": 70,
        "temperature": 0.05,
        "top_p": 0.9,
        "repeat_penalty": 1.1,
        "timeout": 40,
        "num_ctx": 2048,
        "fim_format": "simple",
        "use_raw_completion": False,
    },
    "phi3:mini": {
        "max_tokens": 70,
        "temperature": 0.05,
        "top_p": 0.9,
        "repeat_penalty": 1.1,
        "timeout": 40,
        "num_ctx": 2048,
        "fim_format": "simple",
        "use_raw_completion": False,
    },
    # Modelos medianos (7B)
    "codellama:7b-code": {
        "max_tokens": 60,
        "temperature": 0.0,
        "top_p": 0.85,
        "repeat_penalty": 1.05,
        "timeout": 60,
        "num_ctx": 4096,
        "fim_format": "codellama",
        "use_raw_completion": False,
    },
    # Modelos grandes (13B-16B)
    "codellama:13b-code": {
        "max_tokens": 80,
        "temperature": 0.0,
        "top_p": 0.85,
        "repeat_penalty": 1.05,
        "timeout": 90,
        "num_ctx": 8192,
        "fim_format": "codellama",
        "use_raw_completion": False,
    },
    "deepseek-coder-v2:16b": {
        "max_tokens": 100,
        "temperature": 0.05,
        "top_p": 0.85,
        "repeat_penalty": 1.05,
        "timeout": 120,
        "num_ctx": 8192,
        "fim_format": "deepseek",
        "use_raw_completion": False,
    },
}

# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def get_settings():
    return sublime.load_settings("OpenRouterComplete.sublime-settings")


def get_model_config(model):
    """Obtiene la configuración óptima para un modelo."""
    # Buscar configuración exacta
    if model in MODEL_CONFIGS:
        return MODEL_CONFIGS[model]
    
    # Buscar por patrón
    model_lower = model.lower()
    for pattern, config in MODEL_CONFIGS.items():
        if pattern.split(':')[0] in model_lower:
            return config
    
    # Configuración por defecto basada en tamaño
    if any(size in model_lower for size in ["0.5b", "1.3b", "1.5b", "2b"]):
        return MODEL_CONFIGS["qwen2.5-coder:0.5b"]
    elif "3b" in model_lower:
        return MODEL_CONFIGS["granite-code:3b"]
    elif "7b" in model_lower:
        return MODEL_CONFIGS["codellama:7b-code"]
    elif any(size in model_lower for size in ["13b", "14b", "16b"]):
        return MODEL_CONFIGS["deepseek-coder-v2:16b"]
    
    # Fallback genérico
    return {
        "max_tokens": 80,
        "temperature": 0.1,
        "top_p": 0.9,
        "repeat_penalty": 1.05,
        "timeout": 60,
        "num_ctx": 4096,
        "fim_format": "simple",
        "needs_simple_prompt": False,
    }


def get_context(view, cursor_point, max_prefix=3000, max_suffix=500):
    """Obtiene el contexto antes y después del cursor."""
    region_before = sublime.Region(max(0, cursor_point - max_prefix), cursor_point)
    region_after = sublime.Region(cursor_point, min(view.size(), cursor_point + max_suffix))
    return view.substr(region_before), view.substr(region_after)


def get_language(view):
    """Detecta el lenguaje del archivo."""
    syntax = view.settings().get("syntax", "").lower()
    lang_map = {
        "python": "Python", "javascript": "JavaScript", "typescript": "TypeScript",
        "java": "Java", "c++": "C++", "c#": "C#", "go": "Go", "rust": "Rust",
        "ruby": "Ruby", "php": "PHP", "html": "HTML", "css": "CSS",
        "sql": "SQL", "bash": "Bash", "shell": "Shell",
    }
    for key, lang in lang_map.items():
        if key in syntax:
            return lang
    return "code"


# ---------------------------------------------------------------------------
# Construcción de Prompts Optimizados
# ---------------------------------------------------------------------------

def build_prompt_simple(prefix, suffix):
    """Prompt ULTRA simple para modelos pequeños - Solo las últimas líneas."""
    # Para modelos pequeños: SOLO las últimas 5-10 líneas
    lines = prefix.split('\n')
    
    # Tomar solo las últimas líneas relevantes
    relevant_lines = []
    for line in reversed(lines):
        relevant_lines.insert(0, line)
        if len(relevant_lines) >= 10:  # Máximo 10 líneas
            break
        # Si encontramos una definición de función/clase, parar ahí
        stripped = line.strip()
        if stripped.startswith(('def ', 'class ', 'function ', 'const ', 'let ', 'var ')):
            break
    
    simple_prefix = '\n'.join(relevant_lines)
    
    # NO usar suffix para modelos pequeños - los confunde
    return simple_prefix


def build_prompt_fim(prefix, suffix, fim_format):
    """Prompt FIM optimizado - Solo para modelos medianos/grandes."""
    # Reducir contexto si es muy largo
    if len(prefix) > 2000:
        lines = prefix.split('\n')
        prefix = '\n'.join(lines[-30:])  # Últimas 30 líneas
    
    if fim_format == "qwen":
        return "<|fim_prefix|>{0}<|fim_suffix|>{1}<|fim_middle|>".format(prefix, suffix)
    elif fim_format == "deepseek":
        return "<|fim_prefix|>{0}<|fim_suffix|>{1}<|fim_middle|>".format(prefix, suffix)
    elif fim_format == "codellama":
        return "<PRE> {0} <SUF>{1} <MID>".format(prefix, suffix)
    elif fim_format == "starcoder":
        return "<fim_prefix>{0}<fim_suffix>{1}<fim_middle>".format(prefix, suffix)
    else:
        return prefix


def build_prompt(prefix, suffix, model, model_config):
    """Construye el prompt óptimo según el modelo."""
    use_raw = model_config.get("use_raw_completion", False)
    
    # Modelos pequeños: prompt ULTRA simple
    if use_raw:
        return build_prompt_simple(prefix, "")  # Sin suffix
    
    # Modelos grandes: FIM completo
    fim_format = model_config.get("fim_format", "simple")
    return build_prompt_fim(prefix, suffix, fim_format)


# ---------------------------------------------------------------------------
# Limpieza Agresiva de Respuestas
# ---------------------------------------------------------------------------

def clean_completion(text, prefix, use_raw=False):
    """Limpieza ultra agresiva - SOLO CÓDIGO."""
    if not text:
        return ""
    
    text = text.strip()
    
    # Para modelos pequeños con use_raw: limpieza EXTREMA
    if use_raw:
        # Tomar SOLO la primera línea de código válida
        lines = text.split('\n')
        code_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Saltar líneas vacías al inicio
            if not stripped and not code_lines:
                continue
            
            # Si empieza con texto explicativo, PARAR
            if any(stripped.lower().startswith(kw) for kw in [
                'to ', 'for ', 'the ', 'this ', 'here', 'you ', 'we ',
                'para ', 'el ', 'la ', 'esto ', 'aquí',
                '1.', '2.', '3.', '*', '-', '#',
            ]):
                break
            
            # Si es código válido, agregar
            if stripped and (
                any(c in stripped for c in ['=', '(', ')', '{', '}', '[', ']', ':', ';']) or
                stripped.startswith(('return', 'if', 'else', 'for', 'while', 'def', 'class'))
            ):
                code_lines.append(line)
                # Para modelos pequeños: SOLO 1-3 líneas
                if len(code_lines) >= 3:
                    break
            elif code_lines:  # Si ya tenemos código y encontramos algo raro, parar
                break
        
        return '\n'.join(code_lines).strip()
    
    # Limpieza normal para modelos grandes
    # Remover code fences
    if text.startswith("```"):
        lines = text.split("\n")
        if len(lines) > 2:
            text = "\n".join(lines[1:-1]).strip()
        else:
            text = text.replace("```", "").strip()
    
    # Tokens basura comunes
    bad_tokens = [
        "<|endoftext|>", "<|fim_suffix|>", "<|fim_prefix|>", "<|fim_middle|>",
        "<EOT>", "</s>", "<s>", "[INST]", "[/INST]", "<PRE>", "<SUF>", "<MID>",
        "<|eot_id|>", "<|im_end|>", "<|im_start|>", "<|end|>",
        "<fim_prefix>", "<fim_suffix>", "<fim_middle>",
        "<|assistant|>", "<|user|>",
    ]
    for token in bad_tokens:
        text = text.replace(token, "")
    
    # Cortar en explicaciones
    explanation_patterns = [
        r'\n\n(It looks|However|Note that|This code|The code|Here is|This is)',
        r'\n\n(Parece que|Sin embargo|Nota|Este código|El código)',
        r'\n\n\d+\.',
        r'\n\n[*-]\s',
    ]
    for pattern in explanation_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            text = text[:match.start()].strip()
            break
    
    # Remover líneas explicativas
    lines = text.split('\n')
    code_lines = []
    for line in lines:
        stripped = line.strip()
        if any(stripped.lower().startswith(kw) for kw in [
            'the function', 'this function', 'the code', 'this code',
            'here is', 'this is', 'note:', 'explanation:', 'step',
            'la función', 'el código', 'aquí', 'nota:',
        ]):
            break
        if (stripped and stripped[0].isdigit() and '.' in stripped[:4]) or \
           stripped.startswith(('**', '##', '###', '---')):
            continue
        if stripped.startswith('#') and len(stripped) > 80:
            continue
        code_lines.append(line)
    
    text = '\n'.join(code_lines).strip()
    
    # Remover repetición del prefijo
    if prefix:
        prefix_lines = prefix.rstrip().split('\n')
        for line in prefix_lines[-3:]:
            line_clean = line.strip()
            if line_clean and text.startswith(line_clean):
                text = text[len(line_clean):].lstrip()
    
    # Cortar en triple salto de línea
    if '\n\n\n' in text:
        text = text.split('\n\n\n')[0]
    
    return text.strip()


# ---------------------------------------------------------------------------
# Llamada a Ollama Optimizada
# ---------------------------------------------------------------------------

def call_ollama(prompt, model, model_config):
    """Llama a Ollama con configuración optimizada por modelo."""
    # Stop tokens agresivos
    stop_tokens = [
        "<|endoftext|>", "<EOT>", "</s>", "<|eot_id|>",
        "\n\n\n", "```",
        "\n\n#", "\n\nIt", "\n\nThe", "\n\nThis", "\n\nNote", "\n\nHowever",
    ]
    
    # Stop tokens específicos por formato FIM
    fim_format = model_config.get("fim_format", "simple")
    if fim_format == "qwen":
        stop_tokens.extend(["<|fim_suffix|>", "<|fim_prefix|>", "<|fim_middle|>", "<|im_end|>"])
    elif fim_format == "deepseek":
        stop_tokens.extend(["<|fim_suffix|>", "<|fim_prefix|>", "<|fim_middle|>"])
    elif fim_format == "codellama":
        stop_tokens.extend(["<FILL_HERE>", "<MID>", "<PRE>", "<SUF>"])
    elif fim_format == "starcoder":
        stop_tokens.extend(["<fim_prefix>", "<fim_suffix>", "<fim_middle>"])
    
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": model_config.get("max_tokens", 80),
            "temperature": model_config.get("temperature", 0.1),
            "top_p": model_config.get("top_p", 0.9),
            "repeat_penalty": model_config.get("repeat_penalty", 1.05),
            "stop": stop_tokens,
            "num_ctx": model_config.get("num_ctx", 4096),
            "num_thread": 4,
        }
    }).encode("utf-8")
    
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    req.get_method = lambda: "POST"
    
    timeout = model_config.get("timeout", 60)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("response", "")


def check_ollama_running():
    """Verifica si Ollama está corriendo."""
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return True
    except:
        return False


def get_ollama_models():
    """Obtiene la lista de modelos instalados."""
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [m["name"] for m in data.get("models", [])]
    except:
        return []


# ---------------------------------------------------------------------------
# Phantom (Texto Fantasma)
# ---------------------------------------------------------------------------

def get_phantom_set(view):
    vid = view.id()
    if vid not in _state["phantom_set"]:
        _state["phantom_set"][vid] = sublime.PhantomSet(view, PHANTOM_KEY)
    return _state["phantom_set"][vid]


def show_phantom(view, point, suggestion):
    """Muestra la sugerencia como texto fantasma gris."""
    html_text = (suggestion
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br>")
        .replace(" ", "&nbsp;"))
    
    html = (
        '<body id="ollama-ghost">'
        '<style>body{{margin:0;padding:0}}'
        '.g{{color:color(var(--foreground) alpha(0.38));font-style:italic}}'
        '</style>'
        '<span class="g">{0}</span>'
        '</body>'
    ).format(html_text)
    
    phantom = sublime.Phantom(
        sublime.Region(point, point),
        html,
        sublime.LAYOUT_INLINE,
    )
    get_phantom_set(view).update([phantom])
    _state["suggestion"] = suggestion
    _state["cursor_point"] = point
    _state["view_id"] = view.id()


def clear_phantom(view):
    """Limpia el texto fantasma."""
    if view and view.id() in _state["phantom_set"]:
        _state["phantom_set"][view.id()].update([])
    _state["suggestion"] = None
    _state["cursor_point"] = None
    _state["view_id"] = None
    if view:
        view.erase_status(STATUS_KEY)


# ---------------------------------------------------------------------------
# Comando Principal
# ---------------------------------------------------------------------------

class OllamaCompleteCommand(sublime_plugin.TextCommand):
    """Ctrl+Space - Solicita sugerencia de código."""
    
    def run(self, edit, auto_trigger=False):
        if not check_ollama_running():
            if not auto_trigger:
                sublime.error_message(
                    "Ollama no está corriendo.\n\n"
                    "Inicia Ollama con: ollama serve"
                )
            return
        
        view = self.view
        sel = view.sel()
        if not sel:
            return
        
        cursor_point = sel[0].begin()
        clear_phantom(view)
        
        prefix, suffix = get_context(view, cursor_point)
        
        # No autocompletar si el prefijo es muy corto
        if auto_trigger and len(prefix.strip()) < 10:
            return
        
        settings = get_settings()
        model = settings.get("model", "codellama:7b-code")
        model_config = get_model_config(model)
        
        # Sobrescribir con configuración del usuario si existe
        user_max_tokens = settings.get("max_tokens")
        user_temperature = settings.get("temperature")
        if user_max_tokens is not None:
            model_config["max_tokens"] = user_max_tokens
        if user_temperature is not None:
            model_config["temperature"] = user_temperature
        
        _state["request_id"] += 1
        my_id = _state["request_id"]
        
        if not auto_trigger:
            view.set_status(STATUS_KEY, "[Ollama] Generando...")
        
        thread = threading.Thread(
            target=self._worker,
            args=(view, cursor_point, prefix, suffix, model, model_config, my_id, auto_trigger),
        )
        thread.daemon = True
        thread.start()
        _state["pending_thread"] = thread
    
    def _worker(self, view, cursor_point, prefix, suffix, model, model_config, my_id, auto_trigger):
        import time
        start_time = time.time()
        
        try:
            prompt = build_prompt(prefix, suffix, model, model_config)
            raw = call_ollama(prompt, model, model_config)
            
            if my_id != _state["request_id"]:
                return
            
            use_raw = model_config.get("use_raw_completion", False)
            completion = clean_completion(raw, prefix, use_raw)
            elapsed = time.time() - start_time
            
            if not completion:
                if not auto_trigger:
                    sublime.set_timeout(lambda: self._no_result(view), 0)
                return
            
            sublime.set_timeout(
                lambda: self._show(view, cursor_point, completion, elapsed), 0
            )
            _state["last_completion_time"] = time.time()
        
        except Exception as err:
            if my_id != _state["request_id"] or auto_trigger:
                return
            error_msg = str(err)
            sublime.set_timeout(lambda msg=error_msg: self._error(view, msg), 0)
    
    def _show(self, view, point, completion, elapsed):
        show_phantom(view, point, completion)
        preview = completion[:40].replace("\n", " ")
        view.set_status(STATUS_KEY, "[Ollama] Tab=aceptar Esc=cancelar ({0:.1f}s) | {1}...".format(elapsed, preview))
    
    def _no_result(self, view):
        view.erase_status(STATUS_KEY)
        view.set_status(STATUS_KEY, "[Ollama] Sin sugerencia")
        sublime.set_timeout(lambda: view.erase_status(STATUS_KEY), 2000)
    
    def _error(self, view, msg):
        view.erase_status(STATUS_KEY)
        sublime.error_message("OllamaComplete\n\n" + msg)


# ---------------------------------------------------------------------------
# Aceptar/Cancelar
# ---------------------------------------------------------------------------

class OllamaAcceptCommand(sublime_plugin.TextCommand):
    """Tab - Acepta la sugerencia."""
    
    def run(self, edit):
        view = self.view
        suggestion = _state.get("suggestion")
        point = _state.get("cursor_point")
        
        if not suggestion or _state.get("view_id") != view.id():
            view.run_command("insert_best_completion", {"default": "\t", "exact": False})
            return
        
        clear_phantom(view)
        view.insert(edit, point, suggestion)
        
        new_point = point + len(suggestion)
        view.sel().clear()
        view.sel().add(sublime.Region(new_point, new_point))
        view.show(new_point)
        view.set_status(STATUS_KEY, "[Ollama] ✓")
        sublime.set_timeout(lambda: view.erase_status(STATUS_KEY), 1500)
    
    def is_enabled(self):
        return True


class OllamaCancelCommand(sublime_plugin.TextCommand):
    """Escape - Cancela la sugerencia."""
    
    def run(self, edit):
        view = self.view
        if _state.get("suggestion") and _state.get("view_id") == view.id():
            clear_phantom(view)
            _state["request_id"] += 1
        else:
            view.run_command("single_selection")
    
    def is_enabled(self):
        return True


# ---------------------------------------------------------------------------
# Event Listener
# ---------------------------------------------------------------------------

class OllamaEventListener(sublime_plugin.EventListener):
    
    def on_selection_modified(self, view):
        if _state.get("view_id") != view.id() or not _state.get("suggestion"):
            return
        sel = view.sel()
        if not sel or sel[0].begin() != _state.get("cursor_point"):
            clear_phantom(view)
            _state["request_id"] += 1
    
    def on_modified(self, view):
        if _state.get("view_id") == view.id() and _state.get("suggestion"):
            clear_phantom(view)
            _state["request_id"] += 1
    
    def on_close(self, view):
        vid = view.id()
        if vid in _state["phantom_set"]:
            del _state["phantom_set"][vid]
        if _state.get("view_id") == vid:
            _state["suggestion"] = None
            _state["view_id"] = None
            _state["cursor_point"] = None


# ---------------------------------------------------------------------------
# Comandos Adicionales
# ---------------------------------------------------------------------------

class OllamaSelectModelCommand(sublime_plugin.WindowCommand):
    """Ctrl+Shift+M - Cambiar modelo rápidamente."""
    
    def run(self):
        if not check_ollama_running():
            sublime.error_message("Ollama no está corriendo.\nInicia con: ollama serve")
            return
        
        models = get_ollama_models()
        if not models:
            sublime.error_message("No hay modelos instalados.\n\nInstala uno con:\n  ollama pull codellama:7b-code")
            return
        
        self.models = models
        settings = get_settings()
        current = settings.get("model", "")
        
        items = [m + (" ✓" if m == current else "") for m in models]
        self.window.show_quick_panel(items, self._on_select)
    
    def _on_select(self, index):
        if index < 0:
            return
        selected = self.models[index]
        settings = get_settings()
        settings.set("model", selected)
        sublime.save_settings("OpenRouterComplete.sublime-settings")
        sublime.status_message("Modelo: " + selected)
