"""
Interfaz de usuario - Phantom y UI
"""
import sublime

PHANTOM_KEY = "ollama_complete_phantom"
STATUS_KEY = "ollama_complete"

# Estado global
_phantom_sets = {}


def get_phantom_set(view):
    """Obtiene o crea el phantom set para una vista."""
    vid = view.id()
    if vid not in _phantom_sets:
        _phantom_sets[vid] = sublime.PhantomSet(view, PHANTOM_KEY)
    return _phantom_sets[vid]


def show_phantom(view, point, suggestion):
    """Muestra sugerencia como texto fantasma gris."""
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


def clear_phantom(view):
    """Limpia el texto fantasma."""
    if view and view.id() in _phantom_sets:
        _phantom_sets[view.id()].update([])


def cleanup_phantom_set(view_id):
    """Limpia el phantom set cuando se cierra la vista."""
    if view_id in _phantom_sets:
        del _phantom_sets[view_id]


def show_status(view, message):
    """Muestra mensaje en la barra de estado."""
    view.set_status(STATUS_KEY, message)


def clear_status(view):
    """Limpia la barra de estado."""
    view.erase_status(STATUS_KEY)
