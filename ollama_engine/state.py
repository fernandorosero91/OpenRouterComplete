"""
Thread-safe global state for OllamaComplete.
No more bare dicts shared across threads.
"""
import threading

_lock = threading.Lock()

_request_counter = 0
_current_request_id = 0

# Per-view suggestion: {view_id: {"cursor": int, "text": str}}
_suggestions = {}


def new_request(view_id, cursor):
    """Register a new completion request. Returns request ID."""
    global _request_counter, _current_request_id
    with _lock:
        _request_counter += 1
        _current_request_id = _request_counter
        return _current_request_id


def is_current(req_id):
    """Check if a request is still the latest (not cancelled)."""
    with _lock:
        return req_id == _current_request_id


def invalidate_request():
    """Invalidate the current request (e.g. user typed or moved)."""
    global _current_request_id
    with _lock:
        _current_request_id = -1


def set_suggestion(view_id, cursor, text):
    """Store the active suggestion for a view."""
    with _lock:
        _suggestions[view_id] = {"cursor": cursor, "text": text}


def get_suggestion(view_id):
    """Get the active suggestion for a view, or None."""
    with _lock:
        return _suggestions.get(view_id)


def clear_suggestion(view_id):
    """Remove suggestion for a view."""
    with _lock:
        _suggestions.pop(view_id, None)


def reset():
    """Full reset — used on plugin unload."""
    global _request_counter, _current_request_id, _suggestions
    with _lock:
        _request_counter = 0
        _current_request_id = 0
        _suggestions = {}
