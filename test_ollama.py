#!/usr/bin/env python3
"""
Diagnostic script for OllamaComplete.
Run standalone: python test_ollama.py
"""
import urllib.request
import json
import time
import sys


def check_connection():
    print("1. Checking Ollama connection...")
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m["name"] for m in data.get("models", [])]
            print("   ✓ Ollama is running")
            print("   Models: " + (", ".join(models) if models else "(none)"))
            return models
    except Exception as e:
        print("   ✗ " + str(e))
        print("   → Run: ollama serve")
        return None


def test_completion(model):
    print("\n2. Testing completion with {}...".format(model))

    payload = json.dumps({
        "model": model,
        "prompt": "<PRE> def fibonacci(n): <SUF> <MID>",
        "stream": False,
        "options": {
            "num_predict": 30,
            "temperature": 0.0,
            "num_ctx": 512,
            "num_thread": 6,
        }
    }).encode("utf-8")

    try:
        t0 = time.perf_counter()
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        req.get_method = lambda: "POST"

        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            elapsed = time.perf_counter() - t0
            response = data.get("response", "")
            print("   ✓ Got response in {:.1f}s".format(elapsed))
            print("   Output: " + repr(response[:120]))
            return True
    except Exception as e:
        print("   ✗ " + str(e))
        return False


def test_warm(model):
    print("\n3. Testing warm-up (pre-load)...")
    payload = json.dumps({
        "model": model,
        "prompt": "def f():",
        "stream": False,
        "options": {"num_predict": 1, "temperature": 0.0, "num_ctx": 256}
    }).encode("utf-8")

    try:
        t0 = time.perf_counter()
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        req.get_method = lambda: "POST"
        with urllib.request.urlopen(req, timeout=60) as resp:
            resp.read()
        elapsed = time.perf_counter() - t0
        print("   ✓ Model loaded in {:.1f}s".format(elapsed))
        return True
    except Exception as e:
        print("   ✗ " + str(e))
        return False


def test_second_call(model):
    print("\n4. Testing speed after warm-up...")
    payload = json.dumps({
        "model": model,
        "prompt": "<PRE> def suma(a, b): <SUF> <MID>",
        "stream": False,
        "options": {
            "num_predict": 20,
            "temperature": 0.0,
            "num_ctx": 512,
            "num_thread": 6,
        }
    }).encode("utf-8")

    try:
        t0 = time.perf_counter()
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        req.get_method = lambda: "POST"
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        elapsed = time.perf_counter() - t0
        response = data.get("response", "")
        print("   ✓ {:.1f}s — {}".format(elapsed, repr(response[:80])))
        return elapsed
    except Exception as e:
        print("   ✗ " + str(e))
        return None


def main():
    print("=" * 60)
    print("OllamaComplete — Diagnostic Test")
    print("=" * 60)

    models = check_connection()
    if models is None:
        sys.exit(1)

    if not models:
        print("\n✗ No models installed.")
        print("  Install one: ollama pull qwen2.5-coder:1.5b")
        sys.exit(1)

    model = models[0]
    if len(sys.argv) > 1:
        model = sys.argv[1]
        print("\nUsing model: " + model)

    # Warm up
    test_warm(model)

    # First real completion
    ok = test_completion(model)
    if not ok:
        sys.exit(1)

    # Speed test after warm
    elapsed = test_second_call(model)

    print("\n" + "=" * 60)
    if elapsed and elapsed < 5:
        print("✓ ALL GOOD — {:.1f}s response time".format(elapsed))
    elif elapsed:
        print("⚠ Working but slow ({:.1f}s) — try a smaller model".format(elapsed))
    else:
        print("✗ Issues detected — check errors above")
    print("=" * 60)

    print("\nKeybindings:")
    print("  Ctrl+Space     → Request completion")
    print("  Tab            → Accept full suggestion")
    print("  Ctrl+Right     → Accept word")
    print("  Ctrl+Down      → Accept line")
    print("  Escape         → Dismiss")
    print("  Ctrl+Shift+M   → Switch model")


if __name__ == "__main__":
    main()
