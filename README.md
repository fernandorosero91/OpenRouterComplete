# OllamaComplete — Copilot-class AI Autocomplete for Sublime Text 4

Local AI code completion powered by Ollama. Zero cloud, zero cost, full privacy.

## Features

- Ghost text suggestions (Copilot-style inline phantoms)
- Accept full / word-by-word / line-by-line (Tab, Ctrl+Right, Ctrl+Down)
- Thread-safe LRU cache — instant repeats (<100ms)
- Auto-trigger mode — completions appear as you type
- Automatic model warm-up on Sublime start
- Quick model switcher (Ctrl+Shift+M)
- Persistent HTTP connection (no per-request overhead)
- Tuned per-model configs for CPU-only machines
- Scales output limits based on model capability

## Requirements

- Sublime Text 4
- [Ollama](https://ollama.ai) installed and running (`ollama serve`)
- At least one code model pulled

## Recommended Models (CPU-only, i5 + 32GB RAM)

| Model | Size | Speed | Quality |
|---|---|---|---|
| `qwen2.5-coder:1.5b` | 986MB | ~1-2s ⚡⚡⚡⚡⚡ | ⭐⭐⭐⭐ |
| `qwen2.5-coder:3b` | 1.9GB | ~2-3s ⚡⚡⚡⚡ | ⭐⭐⭐⭐ |
| `starcoder2:3b` | 1.7GB | ~2-3s ⚡⚡⚡⚡ | ⭐⭐⭐⭐ |
| `codellama:7b-code` | 3.8GB | ~3-5s ⚡⚡⚡ | ⭐⭐⭐⭐⭐ |
| `qwen2.5-coder:7b` | 4.7GB | ~4-6s ⚡⚡ | ⭐⭐⭐⭐⭐ |

## Installation

```bash
# 1. Install Ollama from https://ollama.ai

# 2. Pull a model
ollama pull qwen2.5-coder:1.5b

# 3. Start Ollama
ollama serve

# 4. Install plugin
#    Preferences → Browse Packages → create folder "OllamaComplete"
#    Copy all files into it. Restart Sublime Text.
```

## Keybindings

| Key | Action |
|---|---|
| `Ctrl+Space` | Request completion |
| `Tab` | Accept full suggestion |
| `Ctrl+Right` | Accept next word |
| `Ctrl+Down` | Accept next line |
| `Escape` | Dismiss suggestion |
| `Ctrl+Shift+M` | Switch model |

## Settings

`Preferences → Package Settings → OllamaComplete → Settings`

```json
{
    "model": "qwen2.5-coder:1.5b",
    "auto_complete": false,
    "auto_complete_delay_ms": 800
}
```

## Architecture

```
OllamaComplete/
├── OllamaComplete.py              # Plugin entry, commands, events
├── OllamaComplete.sublime-settings
├── Default.sublime-keymap
├── ollama_engine/
│   ├── __init__.py
│   ├── client.py                   # HTTP client, connection pool
│   ├── cache.py                    # Thread-safe LRU cache
│   ├── config.py                   # Per-model tuned configs
│   ├── prompt.py                   # FIM prompt builders
│   ├── cleaner.py                  # Response sanitizer
│   ├── ui.py                       # Phantom + status bar
│   ├── state.py                    # Thread-safe global state
│   └── debouncer.py                # Auto-trigger debounce
└── test_ollama.py                  # Standalone diagnostic
```

## Diagnostic

```bash
python test_ollama.py
# or test a specific model:
python test_ollama.py qwen2.5-coder:1.5b
```

## License

MIT
