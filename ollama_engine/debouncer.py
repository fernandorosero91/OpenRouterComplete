"""
Debouncer for auto-trigger completions.
Waits for a typing pause before requesting a completion.
"""
import sublime
import threading

_timers = {}  # view_id → Timer
_lock = threading.Lock()

# Delay in ms before auto-triggering after last keystroke
_DEBOUNCE_MS = 800


def trigger(view, callback):
    """Schedule a debounced callback for this view."""
    vid = view.id()
    delay = _get_delay()

    with _lock:
        # Cancel previous timer for this view
        if vid in _timers:
            _timers[vid].cancel()

        def _fire():
            with _lock:
                _timers.pop(vid, None)
            # Run on main thread
            sublime.set_timeout(lambda: callback(view), 0)

        t = threading.Timer(delay / 1000.0, _fire)
        t.daemon = True
        _timers[vid] = t
        t.start()


def cancel(view_id):
    """Cancel pending trigger for a view."""
    with _lock:
        t = _timers.pop(view_id, None)
        if t:
            t.cancel()


def cancel_all():
    """Cancel all pending triggers."""
    with _lock:
        for t in _timers.values():
            t.cancel()
        _timers.clear()


def _get_delay():
    """Read debounce delay from settings."""
    try:
        s = sublime.load_settings("OllamaComplete.sublime-settings")
        return s.get("auto_complete_delay_ms", _DEBOUNCE_MS)
    except Exception:
        return _DEBOUNCE_MS
