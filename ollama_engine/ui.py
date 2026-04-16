"""
UI layer — phantom (ghost text) rendering + status bar.
"""
import sublime

_PHANTOM_KEY = "ollama_ghost"
_STATUS_KEY = "ollama_status"

# PhantomSet per view
_phantom_sets = {}
_phantom_lock = __import__("threading").Lock()


def _get_ps(view):
    vid = view.id()
    with _phantom_lock:
        if vid not in _phantom_sets:
            _phantom_sets[vid] = sublime.PhantomSet(view, _PHANTOM_KEY)
        return _phantom_sets[vid]


def show_phantom(view, point, text):
    """Show ghost text at cursor position."""
    escaped = (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br>")
        .replace(" ", "&nbsp;")
        .replace("\t", "&nbsp;&nbsp;&nbsp;&nbsp;")
    )

    html = (
        '<body id="ollama-ghost">'
        "<style>"
        "body {{ margin: 0; padding: 0; }}"
        ".ghost {{"
        "  color: color(var(--foreground) alpha(0.35));"
        "  font-style: italic;"
        "  font-size: 0.95rem;"
        "}}"
        "</style>"
        '<span class="ghost">{}</span>'
        "</body>"
    ).format(escaped)

    phantom = sublime.Phantom(
        sublime.Region(point, point),
        html,
        sublime.LAYOUT_INLINE,
    )
    _get_ps(view).update([phantom])


def clear(view):
    """Remove ghost text."""
    if not view:
        return
    vid = view.id()
    with _phantom_lock:
        if vid in _phantom_sets:
            _phantom_sets[vid].update([])


def cleanup(view_id):
    """Dispose phantom set when view closes."""
    with _phantom_lock:
        _phantom_sets.pop(view_id, None)


def show_status(view, message):
    """Show message in status bar."""
    view.set_status(_STATUS_KEY, "[Ollama] " + message)


def clear_status(view):
    """Clear status bar message."""
    view.erase_status(_STATUS_KEY)
