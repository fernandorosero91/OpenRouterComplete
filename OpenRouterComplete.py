"""
OllamaComplete - Autocompletado de código con IA local (Ollama)
Similar a GitHub Copilot para Sublime Text 4

Características:
- Texto fantasma inline (gris) - Tab para aceptar, Escape para cancelar
- Contexto inteligente del proyecto (archivos relevantes)
- Detección automática de frameworks (Django, Vue, React, Angular)
- Optimizado para modelos locales Ollama
- Prompts FIM nativos por modelo (Qwen, DeepSeek, CodeLlama)
- Autocompletado automático mientras escribes (opcional)
"""

import sublime
import sublime_plugin
import urllib.request
import urllib.error
import json
import threading
import os

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
STATUS_KEY  = "ollama_complete"

# ---------------------------------------------------------------------------
# Utilidades generales
# ---------------------------------------------------------------------------

def get_settings():
    return sublime.load_settings("OpenRouterComplete.sublime-settings")


def get_context(view, cursor_point, max_prefix=4000, max_suffix=800):
    region_before = sublime.Region(max(0, cursor_point - max_prefix), cursor_point)
    region_after  = sublime.Region(cursor_point, min(view.size(), cursor_point + max_suffix))
    return view.substr(region_before), view.substr(region_after)


def get_language(view):
    syntax = view.settings().get("syntax", "").lower()
    for key, lang in [
        ("python",     "Python"),
        ("javascript", "JavaScript"),
        ("typescript", "TypeScript"),
        ("java",       "Java"),
        ("c++",        "C++"),
        ("c#",         "C#"),
        ("go",         "Go"),
        ("rust",       "Rust"),
        ("ruby",       "Ruby"),
        ("php",        "PHP"),
        ("html",       "HTML"),
        ("css",        "CSS"),
        ("sql",        "SQL"),
        ("bash",       "Bash"),
        ("shell",      "Shell"),
    ]:
        if key in syntax:
            return lang
    return "code"


# ---------------------------------------------------------------------------
# Lectura del proyecto (contexto tipo Copilot)
# ---------------------------------------------------------------------------

def get_project_root(view):
    """Obtiene la carpeta raiz del proyecto abierto en Sublime."""
    window = view.window()
    if not window:
        return None

    folders = window.folders()
    if folders:
        return folders[0]

    # Fallback: carpeta del archivo actual
    filename = view.file_name()
    if filename:
        return os.path.dirname(filename)

    return None


def read_file_safe(path, max_chars=2000):
    """Lee un archivo de forma segura, truncando si es muy largo."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(max_chars)
            if len(content) == max_chars:
                content += "\n... (truncado)"
            return content
    except Exception:
        return None


def find_file_in_project(root, filename):
    """Busca un archivo por nombre en el proyecto recursivamente."""
    results = []
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            # Ignorar carpetas irrelevantes
            dirnames[:] = [d for d in dirnames if d not in [
                ".git", "__pycache__", "node_modules", ".venv", "venv",
                "env", "migrations", "staticfiles", "media", ".idea"
            ]]
            for f in filenames:
                if f == filename:
                    results.append(os.path.join(dirpath, f))
    except Exception:
        pass
    return results


# Cache simple para archivos del proyecto (evita releer en cada request)
_project_cache = {
    "root": None,
    "timestamp": 0,
    "context": "",
}

def build_project_context(view, max_total=6000):
    """
    Construye el contexto del proyecto leyendo archivos clave.
    Similar a como Copilot analiza el workspace.
    Usa cache para evitar releer archivos constantemente.
    """
    import time
    
    root = get_project_root(view)
    if not root:
        return ""
    
    # Cache: si el root es el mismo y paso menos de 30 segundos, reusar
    current_time = time.time()
    if (_project_cache["root"] == root and 
        current_time - _project_cache["timestamp"] < 30):
        return _project_cache["context"]

    context_parts = []
    used_chars = 0

    # Archivos a buscar segun prioridad
    priority_files = [
        ("urls.py",    2000),   # URLs de Django - muy importante para templates
        ("models.py",  2000),   # Modelos - nombres de campos y clases
        ("views.py",   1500),   # Vistas - nombres de funciones
        ("settings.py", 500),   # Settings basicos
        ("forms.py",   1000),   # Formularios Django
        ("serializers.py", 800), # DRF serializers
    ]

    for filename, max_size in priority_files:
        if used_chars >= max_total:
            break

        paths = find_file_in_project(root, filename)
        for path in paths[:2]:  # Maximo 2 archivos del mismo nombre
            if used_chars >= max_total:
                break

            allowed = min(max_size, max_total - used_chars)
            content = read_file_safe(path, allowed)
            if content:
                # Ruta relativa para el contexto
                rel_path = os.path.relpath(path, root)
                context_parts.append("# File: {0}\n{1}".format(rel_path, content))
                used_chars += len(content)

    result = "\n\n".join(context_parts) if context_parts else ""
    
    # Guardar en cache
    _project_cache["root"] = root
    _project_cache["timestamp"] = current_time
    _project_cache["context"] = result
    
    return result


def detect_framework(prefix, suffix):
    """Detecta el framework por el contenido del archivo."""
    content = prefix + suffix
    if "{%" in content and ("url" in content or "block" in content or "extends" in content or "load" in content):
        return "Django"
    if "v-bind" in content or "v-for" in content or ":class" in content:
        return "Vue"
    if "ng-" in content or "[(ngModel)]" in content:
        return "Angular"
    if "import React" in content or "useState" in content:
        return "React"
    return None


# ---------------------------------------------------------------------------
# Limpieza de respuesta
# ---------------------------------------------------------------------------

def clean_completion(text, prefix):
    """Limpia tokens basura y artefactos del modelo - SOLO CÓDIGO."""
    if not text:
        return ""
    
    text = text.strip()

    # Quitar code fences
    if text.startswith("```"):
        lines = text.split("\n")
        if len(lines) > 2:
            text = "\n".join(lines[1:-1]).strip()
        else:
            text = text.replace("```", "").strip()

    # Tokens basura de todos los modelos conocidos
    bad_tokens = [
        "<|endoftext|>", "<|fim_suffix|>", "<|fim_prefix|>", "<|fim_middle|>",
        "<EOT>", " <EOT>", "</s>", "<s>", "[INST]", "[/INST]",
        "<<SYS>>", "<</SYS>>", "<PRE>", "<SUF>", "<MID>",
        "<|eot_id|>", "<|start_header_id|>", "<|end_header_id|>",
        "\\end{code}", "```python", "```javascript", "```html",
        "<FILL_HERE>", "<|im_end|>", "<|im_start|>",
    ]
    for token in bad_tokens:
        text = text.replace(token, "")

    # ULTRA AGRESIVO: Cortar en la primera línea que parezca explicación
    lines = text.split('\n')
    code_lines = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        lower = stripped.lower()
        
        # Si la línea empieza con texto explicativo, CORTAR TODO
        explanation_keywords = [
            'it looks like', 'however', 'note that', 'this code', 'the code',
            'this function', 'the function', 'here is', 'here\'s', 'this is',
            'the provided', 'in this', 'explanation', 'step-by-step',
            'parece que', 'sin embargo', 'nota', 'este código', 'el código',
            'esta función', 'la función', 'aquí está', 'esto es',
            'breakdown', 'how it works', 'what this does', 'to understand',
        ]
        
        if any(keyword in lower for keyword in explanation_keywords):
            # CORTAR AQUÍ - no agregar esta línea ni las siguientes
            break
        
        # Saltar líneas numeradas (1., 2., etc.)
        if stripped and len(stripped) > 0 and stripped[0].isdigit() and '.' in stripped[:4]:
            continue
        
        # Saltar líneas con markdown
        if stripped.startswith(('**', '##', '###', '- **', '* **', '---')):
            continue
        
        # Saltar comentarios que son claramente explicaciones (>70 chars sin código)
        if stripped.startswith('#'):
            # Permitir comentarios cortos o con código
            if len(stripped) > 70 and not any(c in stripped for c in ['=', '(', ')', '[', ']']):
                continue
        
        code_lines.append(line)
    
    text = '\n'.join(code_lines).strip()

    # Si el modelo repite el prefijo, quitarlo
    stripped_prefix = prefix.rstrip()
    if stripped_prefix:
        # Verificar últimas 3 líneas del prefix
        prefix_lines = stripped_prefix.split('\n')
        for line in prefix_lines[-3:]:
            line_clean = line.strip()
            if line_clean and text.startswith(line_clean):
                text = text[len(line_clean):].lstrip()

    # Cortar en la primera línea vacía doble (fin de código)
    if '\n\n\n' in text:
        text = text.split('\n\n\n')[0]
    
    # Cortar en doble salto de línea si después hay texto sin indentación
    parts = text.split('\n\n')
    if len(parts) > 1:
        # Verificar si la segunda parte es explicación
        second_part = parts[1].strip()
        if second_part and not second_part[0] in ' \t' and len(second_part) > 40:
            # Si no está indentado y es largo, probablemente es explicación
            text = parts[0]

    return text.strip()


# ---------------------------------------------------------------------------
# Construccion del prompt
# ---------------------------------------------------------------------------

def build_prompt(prefix, suffix, language, model, project_context):
    """
    Construye el prompt completo con contexto del proyecto.
    Usa FIM nativo para modelos que lo soportan.
    OPTIMIZADO PARA GENERAR SOLO CÓDIGO SIN EXPLICACIONES.
    """
    model_lower = model.lower()

    # Contexto del proyecto - ULTRA COMPACTO (solo imports y definiciones)
    if project_context:
        lines = project_context.split('\n')
        important_lines = []
        for line in lines:
            stripped = line.strip()
            # Solo imports y definiciones de clase/función
            if stripped.startswith(('from ', 'import ', 'def ', 'class ')):
                important_lines.append(line)
                if len(important_lines) >= 15:  # Máximo 15 líneas
                    break
        
        if important_lines:
            proj_block = '\n'.join(important_lines) + '\n\n'
        else:
            proj_block = ""
    else:
        proj_block = ""

    # Granite-Code - Formato simple (no usa FIM tokens especiales)
    if "granite" in model_lower:
        full_prefix = proj_block + prefix
        # Granite funciona mejor con prompt directo
        if suffix:
            return "{0}\n# Complete the code above\n".format(full_prefix)
        else:
            return full_prefix
    
    # Phi-3 - Formato instrucción
    elif "phi" in model_lower or "phi3" in model_lower:
        full_prefix = proj_block + prefix
        # Phi-3 funciona mejor con contexto claro
        if suffix:
            return "{0}\n# Continue the code\n".format(full_prefix)
        else:
            return full_prefix

    # Qwen 2.5 Coder - FIM nativo
    elif "qwen2.5" in model_lower or "qwen" in model_lower:
        full_prefix = proj_block + prefix
        return "<|fim_prefix|>{0}<|fim_suffix|>{1}<|fim_middle|>".format(full_prefix, suffix)
    
    # DeepSeek Coder - FIM nativo
    elif "deepseek" in model_lower:
        full_prefix = proj_block + prefix
        return "<|fim_prefix|>{0}<|fim_suffix|>{1}<|fim_middle|>".format(full_prefix, suffix)

    # CodeLlama - Formato SPM
    elif "codellama" in model_lower or "code-llama" in model_lower:
        full_prefix = proj_block + prefix
        return "<PRE> {0} <SUF>{1} <MID>".format(full_prefix, suffix)
    
    # Starcoder - FIM format
    elif "starcoder" in model_lower or "star" in model_lower:
        full_prefix = proj_block + prefix
        return "<fim_prefix>{0}<fim_suffix>{1}<fim_middle>".format(full_prefix, suffix)

    # Fallback - solo código sin instrucciones
    else:
        return "{0}{1}".format(proj_block, prefix)


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------

def call_ollama(prompt, model, max_tokens, temperature):
    """Llama a Ollama local con configuración optimizada por modelo."""
    model_lower = model.lower()
    
    # Stop tokens específicos por modelo - MUY AGRESIVOS
    stop_tokens = [
        "<|endoftext|>", "<EOT>", "</s>", "<|eot_id|>",
        "\n\n\n",  # Tres saltos de línea = fin de código
        "```",     # Code fence
        "\n\n#",   # Doble salto + comentario = explicación
        "\n\nIt",  # Doble salto + "It" = explicación en inglés
        "\n\nThe", # Doble salto + "The" = explicación
        "\n\nThis",# Doble salto + "This" = explicación
        "\n\nNote",# Doble salto + "Note" = explicación
        "\n\nHowever", # Explicación
    ]
    
    if "qwen" in model_lower:
        stop_tokens.extend([
            "<|fim_suffix|>", "<|fim_prefix|>", "<|fim_middle|>",
            "<|im_end|>", "<|im_start|>", "<|endoftext|>",
            "<|end|>", "<|file_sep|>",
        ])
    elif "deepseek" in model_lower:
        stop_tokens.extend([
            "<|fim_suffix|>", "<|fim_prefix|>", "<|fim_middle|>",
            "<｜end▁of▁sentence｜>", "<|EOT|>",
            "<|end_of_sentence|>", "```",
        ])
    elif "codellama" in model_lower:
        stop_tokens.extend([
            "<FILL_HERE>", "<MID>", "<PRE>", "<SUF>",
            "```", "\n\n\n\n",
        ])
    elif "starcoder" in model_lower or "star" in model_lower:
        stop_tokens.extend([
            "<fim_prefix>", "<fim_suffix>", "<fim_middle>",
            "<|endoftext|>", "<file_sep>",
        ])
    elif "granite" in model_lower:
        stop_tokens.extend([
            "<|endoftext|>", "<|end|>", "```",
            "\n\n\n",
        ])
    elif "phi" in model_lower or "phi3" in model_lower:
        stop_tokens.extend([
            "<|end|>", "<|endoftext|>", "<|assistant|>",
            "<|user|>", "```",
        ])
    elif "starcoder" in model_lower:
        stop_tokens.extend([
            "<fim_prefix>", "<fim_suffix>", "<fim_middle>",
            "<|endoftext|>", "<file_sep>",
        ])
    
    # Configuración optimizada por tamaño de modelo
    if "0.5b" in model_lower or "1.3b" in model_lower or "1.5b" in model_lower or "2b" in model_lower:
        # Modelos pequeños (2B o menos)
        top_p = 0.95
        repeat_penalty = 1.1
        timeout = 45
        num_ctx = 2048
    elif "3b" in model_lower or "6.7b" in model_lower or "7b" in model_lower:
        # Modelos medianos (3B-7B)
        top_p = 0.9
        repeat_penalty = 1.05
        timeout = 60
        num_ctx = 4096
    elif "13b" in model_lower or "14b" in model_lower or "16b" in model_lower:
        # Modelos grandes (13B-16B) - Optimizado para tu hardware
        top_p = 0.85
        repeat_penalty = 1.05
        timeout = 120  # Aumentado a 120 segundos para modelos grandes
        num_ctx = 8192  # Más contexto para modelos grandes
    else:
        # Modelos muy grandes (34B+)
        top_p = 0.85
        repeat_penalty = 1.1
        timeout = 120
        num_ctx = 16384
    
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "repeat_penalty": repeat_penalty,
            "stop": stop_tokens,
            "num_ctx": num_ctx,
            "num_thread": 4,
            "num_gpu": 0,  # Forzar CPU para consistencia
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    req.get_method = lambda: "POST"

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
    """Obtiene la lista de modelos instalados en Ollama."""
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [m["name"] for m in data.get("models", [])]
    except:
        return []


# ---------------------------------------------------------------------------
# Phantom (texto fantasma)
# ---------------------------------------------------------------------------

def get_phantom_set(view):
    vid = view.id()
    if vid not in _state["phantom_set"]:
        _state["phantom_set"][vid] = sublime.PhantomSet(view, PHANTOM_KEY)
    return _state["phantom_set"][vid]


def show_phantom(view, point, suggestion):
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
    _state["suggestion"]   = suggestion
    _state["cursor_point"] = point
    _state["view_id"]      = view.id()


def clear_phantom(view):
    if view and view.id() in _state["phantom_set"]:
        _state["phantom_set"][view.id()].update([])
    _state["suggestion"]   = None
    _state["cursor_point"] = None
    _state["view_id"]      = None
    if view:
        view.erase_status(STATUS_KEY)


# ---------------------------------------------------------------------------
# Comando principal
# ---------------------------------------------------------------------------

class OllamaCompleteCommand(sublime_plugin.TextCommand):
    """Ctrl+Space — solicita sugerencia de IA con contexto del proyecto."""

    def run(self, edit, auto_trigger=False):
        settings = get_settings()
        view     = self.view

        # Verificar que Ollama esté corriendo
        if not check_ollama_running():
            if not auto_trigger:
                sublime.error_message(
                    "Ollama no está corriendo.\n\n"
                    "Inicia Ollama con:\n  ollama serve\n\n"
                    "O ejecuta Ollama desde el menú de inicio."
                )
            return

        sel = view.sel()
        if not sel:
            return

        cursor_point = sel[0].begin()
        clear_phantom(view)

        prefix, suffix = get_context(view, cursor_point)
        
        # No autocompletar si el prefijo es muy corto
        if auto_trigger and len(prefix.strip()) < 10:
            return
        
        language = get_language(view)
        model    = settings.get("model", "qwen2.5-coder:1.5b")

        _state["request_id"] += 1
        my_id = _state["request_id"]

        if not auto_trigger:
            view.set_status(STATUS_KEY, "[Ollama] Analizando... (" + model + ")")

        thread = threading.Thread(
            target=self._worker,
            args=(view, cursor_point, prefix, suffix, language, settings, model, my_id, auto_trigger),
        )
        thread.daemon = True
        thread.start()
        _state["pending_thread"] = thread

    def _worker(self, view, cursor_point, prefix, suffix, language, settings, model, my_id, auto_trigger):
        import time
        
        max_tokens  = settings.get("max_tokens", 120)
        temperature = settings.get("temperature", 0.05)

        # Leer contexto del proyecto (urls, models, views...)
        if not auto_trigger:
            sublime.set_timeout(
                lambda: view.set_status(STATUS_KEY, "[Ollama] Leyendo proyecto..."), 0
            )
        
        project_context = build_project_context(view)

        if my_id != _state["request_id"]:
            return

        if not auto_trigger:
            sublime.set_timeout(
                lambda: view.set_status(STATUS_KEY, "[Ollama] Generando..."), 0
            )

        prompt = build_prompt(prefix, suffix, language, model, project_context)
        start_time = time.time()

        try:
            raw = call_ollama(prompt, model, max_tokens, temperature)
            
            if my_id != _state["request_id"]:
                return

            completion = clean_completion(raw, prefix)
            
            # Post-procesamiento adicional: si es muy largo y tiene explicaciones, cortar
            if len(completion) > 200:
                # Buscar patrones de explicación y cortar ahí
                for pattern in ['\n\nIt looks', '\n\nHowever', '\n\nNote', '\n\nThe code', '\n\nThis code']:
                    if pattern in completion:
                        completion = completion.split(pattern)[0].strip()
                        break
            
            elapsed = time.time() - start_time

            if not completion:
                if not auto_trigger:
                    sublime.set_timeout(lambda: self._no_result(view), 0)
                return

            sublime.set_timeout(
                lambda: self._show(view, cursor_point, completion, elapsed), 0
            )
            
            _state["last_completion_time"] = time.time()

        except urllib.error.URLError as err:
            if my_id != _state["request_id"]:
                return
            if auto_trigger:
                return  # No mostrar errores en auto-trigger
            
            error_msg = ""
            reason_str = str(err.reason) if hasattr(err, 'reason') else str(err)
            if "Connection refused" in reason_str:
                error_msg = "No se pudo conectar a Ollama.\n\nAsegúrate de que esté corriendo:\n  ollama serve"
            elif "timed out" in reason_str.lower():
                error_msg = "Timeout: El modelo {0} tardó más de {1}s.\n\nOpciones:\n1. Espera a que termine de cargar\n2. Usa un modelo más pequeño\n3. Aumenta el timeout en el código".format(model, timeout)
            else:
                error_msg = "Error de conexión: {0}".format(reason_str)
            sublime.set_timeout(lambda msg=error_msg: self._error(view, msg), 0)

        except urllib.error.HTTPError as err:
            if my_id != _state["request_id"] or auto_trigger:
                return
            body = err.read().decode("utf-8") if err.fp else ""
            error_msg = "HTTP {0}: {1}".format(err.code, body[:200])
            sublime.set_timeout(lambda msg=error_msg: self._error(view, msg), 0)

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
# Aceptar con Tab
# ---------------------------------------------------------------------------

class OllamaAcceptCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        view       = self.view
        suggestion = _state.get("suggestion")
        point      = _state.get("cursor_point")

        if not suggestion or _state.get("view_id") != view.id():
            view.run_command("insert_best_completion", {"default": "\t", "exact": False})
            return

        clear_phantom(view)
        view.insert(edit, point, suggestion)

        new_point = point + len(suggestion)
        view.sel().clear()
        view.sel().add(sublime.Region(new_point, new_point))
        view.show(new_point)
        view.set_status(STATUS_KEY, "[Ollama] ✓ Completado")
        sublime.set_timeout(lambda: view.erase_status(STATUS_KEY), 1500)

    def is_enabled(self):
        return True


# ---------------------------------------------------------------------------
# Cancelar con Escape
# ---------------------------------------------------------------------------

class OllamaCancelCommand(sublime_plugin.TextCommand):

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
# Listener: cancelar si el cursor se mueve o el usuario escribe
# ---------------------------------------------------------------------------

class OllamaEventListener(sublime_plugin.EventListener):

    def on_selection_modified(self, view):
        if _state.get("view_id") != view.id() or not _state.get("suggestion"):
            return
        sel = view.sel()
        if not sel:
            return
        if sel[0].begin() != _state.get("cursor_point"):
            clear_phantom(view)
            _state["request_id"] += 1

    def on_modified(self, view):
        if _state.get("view_id") == view.id() and _state.get("suggestion"):
            clear_phantom(view)
            _state["request_id"] += 1
        
        # Auto-trigger si está habilitado
        settings = get_settings()
        if settings.get("auto_complete", False):
            self._schedule_auto_complete(view)

    def on_close(self, view):
        vid = view.id()
        if vid in _state["phantom_set"]:
            del _state["phantom_set"][vid]
        if _state.get("view_id") == vid:
            _state["suggestion"]   = None
            _state["view_id"]      = None
            _state["cursor_point"] = None
    
    def _schedule_auto_complete(self, view):
        """Programa autocompletado automático después de una pausa."""
        import time
        
        settings = get_settings()
        delay = settings.get("auto_complete_delay", 1500)
        
        # Cancelar timer anterior
        if _state["auto_trigger_timer"]:
            try:
                _state["auto_trigger_timer"].cancel()
            except:
                pass
        
        # No auto-completar si ya hay una sugerencia visible
        if _state.get("suggestion"):
            return
        
        # No auto-completar si recién se completó algo (evitar spam)
        if time.time() - _state["last_completion_time"] < 3:
            return
        
        # Programar nuevo auto-complete
        timer = threading.Timer(
            delay / 1000.0,
            lambda: sublime.set_timeout(lambda: self._trigger_auto_complete(view), 0)
        )
        timer.daemon = True
        timer.start()
        _state["auto_trigger_timer"] = timer
    
    def _trigger_auto_complete(self, view):
        """Ejecuta el autocompletado automático."""
        if not view.is_valid():
            return
        
        # Solo en archivos de código
        syntax = view.settings().get("syntax", "").lower()
        if not any(x in syntax for x in ["python", "javascript", "typescript", "java", "c++", "go", "rust", "php", "html", "css"]):
            return
        
        view.run_command("ollama_complete", {"auto_trigger": True})


# ---------------------------------------------------------------------------
# Bonus: explicar codigo seleccionado
# ---------------------------------------------------------------------------

class OllamaExplainCommand(sublime_plugin.TextCommand):
    """Explica código seleccionado en español."""

    def run(self, edit):
        if not check_ollama_running():
            sublime.error_message("Ollama no está corriendo.\nInicia Ollama con: ollama serve")
            return
        
        settings = get_settings()
        view     = self.view
        sel      = view.sel()

        if not sel or sel[0].empty():
            sublime.error_message("Selecciona el código que quieres explicar.")
            return

        code     = view.substr(sel[0])
        language = get_language(view)
        model    = settings.get("model", "qwen2.5-coder:1.5b")
        view.set_status(STATUS_KEY, "[Ollama] Explicando...")

        thread = threading.Thread(
            target=self._worker,
            args=(view, code, language, model),
        )
        thread.daemon = True
        thread.start()

    def _worker(self, view, code, language, model):
        prompt = "Explica este código {0} en español de forma clara y concisa:\n\n{1}".format(language, code)
        try:
            result = call_ollama(prompt, model, 500, 0.3)
            sublime.set_timeout(lambda res=result.strip(): self._show(view, res), 0)
        except Exception as err:
            msg = str(err)
            sublime.set_timeout(lambda error=msg: self._err(view, error), 0)

    def _show(self, view, explanation):
        view.erase_status(STATUS_KEY)
        sublime.message_dialog("Explicación:\n\n" + explanation)

    def _err(self, view, msg):
        view.erase_status(STATUS_KEY)
        sublime.error_message("Error: " + msg)


# ---------------------------------------------------------------------------
# Comando: Cambiar modelo rápidamente
# ---------------------------------------------------------------------------

class OllamaSelectModelCommand(sublime_plugin.WindowCommand):
    """Permite cambiar el modelo de Ollama rápidamente."""

    def run(self):
        if not check_ollama_running():
            sublime.error_message("Ollama no está corriendo.\nInicia Ollama con: ollama serve")
            return
        
        models = get_ollama_models()
        if not models:
            sublime.error_message("No se encontraron modelos instalados.\n\nInstala un modelo con:\n  ollama pull qwen2.5-coder:1.5b")
            return
        
        self.models = models
        settings = get_settings()
        current = settings.get("model", "")
        
        # Marcar el modelo actual
        items = []
        for m in models:
            if m == current:
                items.append(m + " ✓")
            else:
                items.append(m)
        
        self.window.show_quick_panel(items, self._on_select)
    
    def _on_select(self, index):
        if index < 0:
            return
        
        selected = self.models[index]
        settings = get_settings()
        settings.set("model", selected)
        sublime.save_settings("OpenRouterComplete.sublime-settings")
        sublime.status_message("Modelo cambiado a: " + selected)
