"""
OllamaComplete — Copilot-class AI autocomplete for Sublime Text 4
Powered by local Ollama models. Zero cloud, zero latency tax.

Architecture:
    OllamaComplete.py          → Plugin entry, commands, event listener
    ollama_engine/
        __init__.py            → Public API
        client.py              → HTTP client + connection pool
        cache.py               → Thread-safe LRU cache
        config.py              → Model configs + settings bridge
        prompt.py              → FIM prompt builders
        cleaner.py             → Response sanitizer
        ui.py                  → Phantom + status bar rendering
        state.py               → Thread-safe global state
        debouncer.py           → Auto-trigger debounce logic
"""

import sublime
import sublime_plugin
import threading
import time

from .ollama_engine import (
    client, cache, config, prompt, cleaner, ui, state, debouncer
)


def plugin_loaded():
    """Warm up model on Sublime start — non-blocking."""
    def _init():
        if client.is_running():
            model = config.get_active_model()
            client.warm(model)
            print("[OllamaComplete] Warmed up: " + model)
        else:
            print("[OllamaComplete] Ollama not running — start with: ollama serve")
    sublime.set_timeout_async(_init, 1500)


def plugin_unloaded():
    """Cleanup on plugin unload."""
    cache.clear()
    state.reset()
    debouncer.cancel_all()


# ──────────────────────────────────────────────
# Core command: request completion
# ──────────────────────────────────────────────

class OllamaCompleteCommand(sublime_plugin.TextCommand):
    """Ctrl+Space — Request AI code completion."""

    def run(self, edit):
        view = self.view
        print("[OllamaComplete] Command triggered")

        if not client.is_running():
            sublime.error_message(
                "Ollama is not running.\n\nStart it with:\n  ollama serve"
            )
            return

        sel = view.sel()
        if not sel:
            print("[OllamaComplete] No selection")
            return

        cursor = sel[0].begin()
        ui.clear(view)

        model = config.get_active_model()
        mcfg = config.for_model(model)
        print("[OllamaComplete] Model: {} | Cursor: {}".format(model, cursor))

        prefix, suffix = _get_context(view, cursor, mcfg)
        req_id = state.new_request(view.id(), cursor)

        ui.show_status(view, "⟳ Generating…")

        t = threading.Thread(
            target=self._worker,
            args=(view, cursor, prefix, suffix, model, mcfg, req_id),
            daemon=True,
        )
        t.start()

    def _worker(self, view, cursor, prefix, suffix, model, mcfg, req_id):
        t0 = time.perf_counter()
        try:
            fim = mcfg["fim_format"]
            p = prompt.build(prefix, suffix, fim, mcfg)

            # Try cache first
            cached = cache.get(p, model)
            if cached is not None:
                raw = cached
            else:
                raw = client.generate(p, model, mcfg)
                if raw:
                    cache.put(p, model, raw)

            if not state.is_current(req_id):
                return

            text = cleaner.clean(raw, prefix, mcfg)
            elapsed = time.perf_counter() - t0

            if not text:
                print("[OllamaComplete] Cleaner returned empty")
                sublime.set_timeout(lambda: self._empty(view), 0)
                return

            print("[OllamaComplete] Success: {:.1f}s | {} chars".format(elapsed, len(text)))

            sublime.set_timeout(
                lambda: self._show(view, cursor, text, elapsed), 0
            )

        except Exception as e:
            print("[OllamaComplete] Error: {}".format(e))
            import traceback
            traceback.print_exc()
            if not state.is_current(req_id):
                return
            msg = _friendly_error(str(e), model)
            sublime.set_timeout(lambda: self._fail(view, msg), 0)

    def _show(self, view, cursor, text, elapsed):
        ui.show_phantom(view, cursor, text)
        state.set_suggestion(view.id(), cursor, text)
        preview = text[:50].replace("\n", "↵")
        ui.show_status(
            view,
            "Tab ✓  Esc ✗  ({:.1f}s) │ {}".format(elapsed, preview)
        )

    def _empty(self, view):
        ui.show_status(view, "No suggestion")
        sublime.set_timeout(lambda: ui.clear_status(view), 2000)

    def _fail(self, view, msg):
        ui.clear_status(view)
        sublime.error_message("OllamaComplete\n\n" + msg)


# ──────────────────────────────────────────────
# Accept / Cancel
# ──────────────────────────────────────────────

class OllamaAcceptCommand(sublime_plugin.TextCommand):
    """Tab — Accept the current suggestion."""

    def run(self, edit):
        view = self.view
        s = state.get_suggestion(view.id())

        if not s:
            # No active suggestion — fall through to normal Tab
            view.run_command("insert_best_completion", {
                "default": "\t", "exact": False
            })
            return

        ui.clear(view)
        view.insert(edit, s["cursor"], s["text"])

        end = s["cursor"] + len(s["text"])
        view.sel().clear()
        view.sel().add(sublime.Region(end, end))
        view.show(end)

        ui.show_status(view, "✓ Accepted")
        sublime.set_timeout(lambda: ui.clear_status(view), 1500)
        state.clear_suggestion(view.id())

    def is_enabled(self):
        return True


class OllamaCancelCommand(sublime_plugin.TextCommand):
    """Escape — Dismiss the current suggestion."""

    def run(self, edit):
        view = self.view
        if state.get_suggestion(view.id()):
            ui.clear(view)
            ui.clear_status(view)
            state.clear_suggestion(view.id())
            state.invalidate_request()
        else:
            view.run_command("single_selection")

    def is_enabled(self):
        return True


# ──────────────────────────────────────────────
# Accept word-by-word (Copilot-style Ctrl+Right)
# ──────────────────────────────────────────────

class OllamaAcceptWordCommand(sublime_plugin.TextCommand):
    """Ctrl+Right — Accept next word from suggestion."""

    def run(self, edit):
        view = self.view
        s = state.get_suggestion(view.id())
        if not s:
            view.run_command("move", {"by": "words", "forward": True})
            return

        text = s["text"]
        # Find next word boundary
        i = 0
        while i < len(text) and text[i] in " \t":
            i += 1
        while i < len(text) and text[i] not in " \t\n":
            i += 1

        word = text[:max(i, 1)]
        remaining = text[max(i, 1):]

        ui.clear(view)
        view.insert(edit, s["cursor"], word)

        new_cursor = s["cursor"] + len(word)
        view.sel().clear()
        view.sel().add(sublime.Region(new_cursor, new_cursor))

        if remaining.strip():
            ui.show_phantom(view, new_cursor, remaining)
            state.set_suggestion(view.id(), new_cursor, remaining)
        else:
            ui.clear_status(view)
            state.clear_suggestion(view.id())

    def is_enabled(self):
        return True


# ──────────────────────────────────────────────
# Accept line (Copilot-style Ctrl+Down)
# ──────────────────────────────────────────────

class OllamaAcceptLineCommand(sublime_plugin.TextCommand):
    """Ctrl+Down — Accept next line from suggestion."""

    def run(self, edit):
        view = self.view
        s = state.get_suggestion(view.id())
        if not s:
            view.run_command("move", {"by": "lines", "forward": True})
            return

        text = s["text"]
        nl = text.find("\n")
        if nl == -1:
            line = text
            remaining = ""
        else:
            line = text[:nl + 1]
            remaining = text[nl + 1:]

        ui.clear(view)
        view.insert(edit, s["cursor"], line)

        new_cursor = s["cursor"] + len(line)
        view.sel().clear()
        view.sel().add(sublime.Region(new_cursor, new_cursor))

        if remaining.strip():
            ui.show_phantom(view, new_cursor, remaining)
            state.set_suggestion(view.id(), new_cursor, remaining)
        else:
            ui.clear_status(view)
            state.clear_suggestion(view.id())

    def is_enabled(self):
        return True


# ──────────────────────────────────────────────
# Model selector
# ──────────────────────────────────────────────

class OllamaSelectModelCommand(sublime_plugin.WindowCommand):
    """Ctrl+Shift+M — Quick model switcher."""

    def run(self):
        if not client.is_running():
            sublime.error_message("Ollama not running.\nStart with: ollama serve")
            return

        models = client.list_models()
        if not models:
            sublime.error_message(
                "No models installed.\n\nInstall one:\n  ollama pull codellama:7b-code"
            )
            return

        self._models = models
        current = config.get_active_model()
        items = []
        for m in models:
            mark = " ✓" if m == current else ""
            items.append(m + mark)

        self.window.show_quick_panel(items, self._on_select)

    def _on_select(self, idx):
        if idx < 0:
            return
        selected = self._models[idx]
        settings = sublime.load_settings("OllamaComplete.sublime-settings")
        settings.set("model", selected)
        sublime.save_settings("OllamaComplete.sublime-settings")
        sublime.status_message("Model → " + selected)
        # Warm the new model
        threading.Thread(target=client.warm, args=(selected,), daemon=True).start()


# ──────────────────────────────────────────────
# Event listener
# ──────────────────────────────────────────────

class OllamaEventListener(sublime_plugin.EventListener):

    def on_selection_modified_async(self, view):
        s = state.get_suggestion(view.id())
        if not s:
            return
        sel = view.sel()
        if not sel or sel[0].begin() != s["cursor"]:
            ui.clear(view)
            ui.clear_status(view)
            state.clear_suggestion(view.id())
            state.invalidate_request()

    def on_modified_async(self, view):
        s = state.get_suggestion(view.id())
        if s:
            ui.clear(view)
            ui.clear_status(view)
            state.clear_suggestion(view.id())
            state.invalidate_request()

        # Auto-trigger: debounce typing
        settings = sublime.load_settings("OllamaComplete.sublime-settings")
        if settings.get("auto_complete", False):
            debouncer.trigger(view, self._auto_complete)

    def on_close(self, view):
        vid = view.id()
        ui.cleanup(vid)
        state.clear_suggestion(vid)

    def _auto_complete(self, view):
        """Triggered after typing pause — auto-request completion."""
        if not client.is_running():
            return
        sel = view.sel()
        if not sel:
            return
        cursor = sel[0].begin()
        # Only trigger if cursor is at end of a line with code
        line = view.line(cursor)
        line_text = view.substr(line).strip()
        if not line_text or line_text.startswith("#") or line_text.startswith("//"):
            return
        view.run_command("ollama_complete")


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _get_context(view, cursor, mcfg):
    """Extract prefix/suffix around cursor."""
    max_pre = mcfg.get("max_prefix_chars", 1500)
    max_suf = mcfg.get("max_suffix_chars", 300)
    start = max(0, cursor - max_pre)
    end = min(view.size(), cursor + max_suf)
    prefix = view.substr(sublime.Region(start, cursor))
    suffix = view.substr(sublime.Region(cursor, end))
    return prefix, suffix


def _friendly_error(raw, model):
    low = raw.lower()
    if "timed out" in low:
        return (
            "Timeout — model took too long.\n\n"
            "Try:\n"
            "1. Pre-load: ollama run {}\n"
            "2. Use a smaller model\n"
            "3. Retry".format(model)
        )
    if "connection" in low:
        return "Cannot connect to Ollama.\n\nMake sure it's running:\n  ollama serve"
    return raw
