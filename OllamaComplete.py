"""
OllamaComplete — Copilot-class AI autocomplete for Sublime Text 4
Powered by local Ollama models. Zero cloud, zero latency tax.
"""

import sublime
import sublime_plugin
import threading
import time

from .ollama_engine import (
    client, cache, config, prompt, cleaner, ui, state, debouncer
)


def plugin_loaded():
    """Warm up model on Sublime start."""
    def _init():
        if client.is_running():
            model = config.get_active_model()
            client.warm(model)
            print("[OllamaComplete] Ready — model: " + model)
        else:
            print("[OllamaComplete] Ollama not running — start with: ollama serve")
    sublime.set_timeout_async(_init, 1500)


def plugin_unloaded():
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

        if not client.is_running():
            sublime.error_message(
                "Ollama is not running.\n\nStart it with:\n  ollama serve"
            )
            return

        sel = view.sel()
        if not sel:
            return

        cursor = sel[0].begin()
        ui.clear(view)

        model = config.get_active_model()
        mcfg = config.for_model(model)

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
                text = cleaner.clean(cached, prefix, mcfg)
                elapsed = time.perf_counter() - t0
                if text:
                    sublime.set_timeout(
                        lambda: self._show(view, cursor, text, elapsed), 0
                    )
                else:
                    sublime.set_timeout(lambda: self._empty(view), 0)
                return

            # Stream tokens — update phantom in real-time
            last_update = [0.0]

            def on_chunk(text_so_far):
                now = time.perf_counter()
                if now - last_update[0] < 0.25:
                    return
                last_update[0] = now
                cleaned = cleaner.clean(text_so_far, prefix, mcfg)
                if cleaned:
                    elapsed = now - t0
                    sublime.set_timeout(lambda c=cleaned, e=elapsed: (
                        ui.show_phantom(view, cursor, c),
                        state.set_suggestion(view.id(), cursor, c),
                        ui.show_status(view, "⟳ {:.1f}s…".format(e)),
                    ), 0)

            def on_done(full_text):
                pass

            def is_cancelled():
                return not state.is_current(req_id)

            raw = client.generate_stream(
                p, model, mcfg, on_chunk, on_done, is_cancelled
            )

            if not state.is_current(req_id):
                return

            if raw:
                cache.put(p, model, raw)

            text = cleaner.clean(raw, prefix, mcfg)
            elapsed = time.perf_counter() - t0

            if not text:
                sublime.set_timeout(lambda: self._empty(view), 0)
                return

            print("[OllamaComplete] {:.1f}s | {} chars | {}".format(
                elapsed, len(text), model
            ))
            sublime.set_timeout(
                lambda: self._show(view, cursor, text, elapsed), 0
            )

        except Exception as e:
            if not state.is_current(req_id):
                return
            print("[OllamaComplete] Error: {}".format(e))
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
                "No models installed.\n\nInstall one:\n  ollama pull qwen2.5-coder:1.5b"
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

        settings = sublime.load_settings("OllamaComplete.sublime-settings")
        if settings.get("auto_complete", False):
            debouncer.trigger(view, self._auto_complete)

    def on_close(self, view):
        vid = view.id()
        ui.cleanup(vid)
        state.clear_suggestion(vid)

    def _auto_complete(self, view):
        if not client.is_running():
            return
        sel = view.sel()
        if not sel:
            return
        line = view.line(sel[0].begin())
        line_text = view.substr(line).strip()
        if not line_text or line_text.startswith("#") or line_text.startswith("//"):
            return
        view.run_command("ollama_complete")


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _get_context(view, cursor, mcfg):
    import os
    max_pre = mcfg.get("max_prefix_chars", 1500)
    max_suf = mcfg.get("max_suffix_chars", 300)
    start = max(0, cursor - max_pre)
    end = min(view.size(), cursor + max_suf)
    prefix = view.substr(sublime.Region(start, cursor))
    suffix = view.substr(sublime.Region(cursor, end))

    # ── Build context from neighboring open tabs ──
    # This is what makes it Copilot-like: the model sees related files
    filename = view.file_name()
    fname = os.path.basename(filename) if filename else ""
    comment_fn = _comment_style(view, fname)

    header_parts = []

    # Gather snippets from other open tabs in the same directory
    neighbors = _get_neighbor_context(view, 600)
    if neighbors:
        header_parts.append(comment_fn("Related project files:"))
        for nf, snippet in neighbors:
            header_parts.append(comment_fn("--- {} ---".format(nf)))
            for line in snippet.split("\n")[:10]:
                if line.strip():
                    header_parts.append(comment_fn(line.rstrip()))
        header_parts.append("")

    # Add current filename
    if fname:
        header_parts.append(comment_fn(fname))

    if header_parts:
        header = "\n".join(header_parts) + "\n"
        # Only add if within budget (don't blow up the context)
        if len(header) + len(prefix) <= max_pre + 800:
            prefix = header + prefix

    return prefix, suffix


def _get_neighbor_context(view, budget):
    """Get snippets from other open tabs in the same directory.
    Prioritizes models.py, urls.py, forms.py — the files that define
    the data structures the current file likely references.
    """
    import os
    window = view.window()
    if not window:
        return []

    current_file = view.file_name()
    if not current_file:
        return []

    current_dir = os.path.dirname(current_file)
    current_name = os.path.basename(current_file)

    # Priority files — these define the project's data structures
    priority = ("models.py", "forms.py", "serializers.py", "urls.py", "schema.py")

    neighbors = []
    for v in window.views():
        if v.id() == view.id():
            continue
        f = v.file_name()
        if not f:
            continue

        vname = os.path.basename(f)
        vdir = os.path.dirname(f)

        # Only same directory (same app/module)
        if vdir != current_dir:
            continue

        # Only code files
        if not vname.endswith((".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css")):
            continue

        # Skip __init__, migrations, tests
        if vname.startswith("__") or "migration" in vname.lower():
            continue

        # Get the beginning of the file (imports + definitions)
        size = min(v.size(), 500)
        snippet = v.substr(sublime.Region(0, size)).strip()
        if not snippet:
            continue

        is_priority = vname.lower() in priority
        neighbors.append((vname, snippet, is_priority))

    # Sort: priority files first, then alphabetical
    neighbors.sort(key=lambda x: (not x[2], x[0]))

    # Trim to budget
    result = []
    total = 0
    for nf, snippet, _ in neighbors:
        cost = len(snippet) + len(nf) + 30
        if total + cost > budget:
            # Try a shorter snippet
            short = snippet[:max(0, budget - total - 30)]
            if short:
                result.append((nf, short))
            break
        result.append((nf, snippet))
        total += cost

    return result


def _comment_style(view, fname):
    """Return a function that wraps text in the file's comment style."""
    syntax = view.settings().get("syntax", "").lower()
    if "python" in syntax or fname.endswith(".py"):
        return lambda t: "# " + t
    if any(x in syntax for x in ("javascript", "typescript")) or fname.endswith((".js", ".ts", ".jsx", ".tsx")):
        return lambda t: "// " + t
    if fname.endswith((".html", ".htm")):
        return lambda t: "<!-- {} -->".format(t)
    if fname.endswith((".css", ".scss")):
        return lambda t: "/* {} */".format(t)
    return lambda t: "# " + t


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
