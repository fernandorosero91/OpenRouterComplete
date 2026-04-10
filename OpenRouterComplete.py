"""
OllamaComplete - Autocompletado Profesional con IA Local
Arquitectura modular optimizada para máximo rendimiento

Optimizado especialmente para CodeLlama 7B/13B
"""

import sublime
import sublime_plugin
import threading
import time

# Importar módulos especializados
from .ollama_client import call_ollama, check_ollama_running, get_ollama_models, warm_model
from .ollama_prompt import build_prompt
from .ollama_cleaner import clean_completion
from .ollama_config import get_model_config
from .ollama_ui import (
    show_phantom, clear_phantom, cleanup_phantom_set,
    show_status, clear_status
)

# Estado global del plugin
_state = {
    "suggestion": None,
    "cursor_point": None,
    "view_id": None,
    "request_id": 0,
    "last_completion_time": 0,
}


def get_settings():
    """Obtiene la configuración del plugin."""
    return sublime.load_settings("OpenRouterComplete.sublime-settings")


def plugin_loaded():
    """Se ejecuta cuando el plugin se carga - Pre-calentar modelo."""
    def _init():
        if check_ollama_running():
            settings = get_settings()
            model = settings.get("model", "codellama:7b-code")
            warm_model(model)
    
    # Ejecutar después de 2 segundos para no bloquear el inicio
    sublime.set_timeout(_init, 2000)


def get_context(view, cursor_point, config):
    """Obtiene contexto antes y después del cursor - Ultra optimizado."""
    max_prefix = config.get("max_prefix", 1200)
    max_suffix = config.get("max_suffix", 250)
    
    region_before = sublime.Region(max(0, cursor_point - max_prefix), cursor_point)
    region_after = sublime.Region(cursor_point, min(view.size(), cursor_point + max_suffix))
    return view.substr(region_before), view.substr(region_after)


# ---------------------------------------------------------------------------
# Comando Principal
# ---------------------------------------------------------------------------

class OllamaCompleteCommand(sublime_plugin.TextCommand):
    """Ctrl+Space - Solicita sugerencia de código."""
    
    def run(self, edit):
        if not check_ollama_running():
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
        
        settings = get_settings()
        model = settings.get("model", "codellama:7b-code")
        config = get_model_config(model)
        
        # Pre-calentar modelo en background
        warm_model(model)
        
        prefix, suffix = get_context(view, cursor_point, config)
        
        _state["request_id"] += 1
        my_id = _state["request_id"]
        
        show_status(view, "[Ollama] Generando...")
        
        thread = threading.Thread(
            target=self._worker,
            args=(view, cursor_point, prefix, suffix, model, config, my_id),
        )
        thread.daemon = True
        thread.start()
    
    def _worker(self, view, cursor_point, prefix, suffix, model, config, my_id):
        """Worker thread para no bloquear la UI."""
        start_time = time.time()
        
        try:
            # Construir prompt optimizado
            fim_format = config.get("fim_format", "codellama")
            max_prefix = config.get("max_prefix", 1200)
            max_suffix = config.get("max_suffix", 250)
            prompt = build_prompt(prefix, suffix, fim_format, max_prefix, max_suffix)
            
            # Llamar a Ollama con caché
            raw = call_ollama(prompt, model, use_cache=True)
            
            if my_id != _state["request_id"]:
                return
            
            # Limpiar respuesta
            completion = clean_completion(raw, prefix)
            elapsed = time.time() - start_time
            
            if not completion:
                sublime.set_timeout(lambda: self._no_result(view), 0)
                return
            
            sublime.set_timeout(
                lambda: self._show(view, cursor_point, completion, elapsed), 0
            )
            _state["last_completion_time"] = time.time()
        
        except Exception as err:
            if my_id != _state["request_id"]:
                return
            error_msg = str(err)
            sublime.set_timeout(lambda msg=error_msg: self._error(view, msg), 0)
    
    def _show(self, view, point, completion, elapsed):
        """Muestra la sugerencia."""
        show_phantom(view, point, completion)
        _state["suggestion"] = completion
        _state["cursor_point"] = point
        _state["view_id"] = view.id()
        
        preview = completion[:40].replace("\n", " ")
        show_status(view, "[Ollama] Tab=aceptar Esc=cancelar ({0:.1f}s) | {1}...".format(elapsed, preview))
    
    def _no_result(self, view):
        """Sin resultado."""
        clear_status(view)
        show_status(view, "[Ollama] Sin sugerencia")
        sublime.set_timeout(lambda: clear_status(view), 2000)
    
    def _error(self, view, msg):
        """Error."""
        clear_status(view)
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
        
        show_status(view, "[Ollama] ✓")
        sublime.set_timeout(lambda: clear_status(view), 1500)
        
        # Limpiar estado
        _state["suggestion"] = None
        _state["cursor_point"] = None
        _state["view_id"] = None
    
    def is_enabled(self):
        return True


class OllamaCancelCommand(sublime_plugin.TextCommand):
    """Escape - Cancela la sugerencia."""
    
    def run(self, edit):
        view = self.view
        if _state.get("suggestion") and _state.get("view_id") == view.id():
            clear_phantom(view)
            clear_status(view)
            _state["request_id"] += 1
            _state["suggestion"] = None
            _state["cursor_point"] = None
            _state["view_id"] = None
        else:
            view.run_command("single_selection")
    
    def is_enabled(self):
        return True


# ---------------------------------------------------------------------------
# Event Listener
# ---------------------------------------------------------------------------

class OllamaEventListener(sublime_plugin.EventListener):
    """Listener para cancelar sugerencias automáticamente."""
    
    def on_selection_modified(self, view):
        """Cancela si el cursor se mueve."""
        if _state.get("view_id") != view.id() or not _state.get("suggestion"):
            return
        sel = view.sel()
        if not sel or sel[0].begin() != _state.get("cursor_point"):
            clear_phantom(view)
            clear_status(view)
            _state["request_id"] += 1
            _state["suggestion"] = None
    
    def on_modified(self, view):
        """Cancela si el usuario escribe."""
        if _state.get("view_id") == view.id() and _state.get("suggestion"):
            clear_phantom(view)
            clear_status(view)
            _state["request_id"] += 1
            _state["suggestion"] = None
    
    def on_close(self, view):
        """Limpia recursos cuando se cierra la vista."""
        vid = view.id()
        cleanup_phantom_set(vid)
        if _state.get("view_id") == vid:
            _state["suggestion"] = None
            _state["view_id"] = None
            _state["cursor_point"] = None


# ---------------------------------------------------------------------------
# Cambiar Modelo
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
