"""
Thread-safe LRU cache for completions.
Compatible with both Python 3.3 and 3.8 in Sublime Text.
"""
import threading
import hashlib

_lock = threading.Lock()
_cache = {}       # key → value
_order = []       # list of keys, most recent at end
_MAX_SIZE = 80


def _key(prompt_text, model):
    raw = "{}:{}".format(model, prompt_text)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def get(prompt_text, model):
    """Get cached completion. Moves entry to end (LRU refresh)."""
    k = _key(prompt_text, model)
    with _lock:
        if k in _cache:
            # Move to end (most recently used)
            try:
                _order.remove(k)
            except ValueError:
                pass
            _order.append(k)
            return _cache[k]
    return None


def put(prompt_text, model, result):
    """Store completion in cache. Evicts oldest if full."""
    k = _key(prompt_text, model)
    with _lock:
        if k in _cache:
            try:
                _order.remove(k)
            except ValueError:
                pass
        _cache[k] = result
        _order.append(k)
        # Evict oldest entries
        while len(_order) > _MAX_SIZE:
            old_key = _order.pop(0)
            _cache.pop(old_key, None)


def clear():
    """Flush the entire cache."""
    with _lock:
        _cache.clear()
        del _order[:]


def size():
    """Current cache size."""
    with _lock:
        return len(_cache)
