"""
Configuración optimizada por modelo
"""

# Configuración profesional por modelo
MODEL_CONFIGS = {
    # CodeLlama - Ultra optimizado para máxima velocidad
    "codellama:7b-code": {
        "max_tokens": 40,
        "temperature": 0.0,
        "top_p": 0.9,
        "repeat_penalty": 1.15,
        "timeout": 30,
        "num_ctx": 1536,
        "fim_format": "codellama",
        "use_cache": True,
        "stream": False,
        "max_prefix": 1200,
        "max_suffix": 250,
    },
    "codellama:13b-code": {
        "max_tokens": 60,
        "temperature": 0.0,
        "top_p": 0.9,
        "repeat_penalty": 1.1,
        "timeout": 45,
        "num_ctx": 2048,
        "fim_format": "codellama",
        "use_cache": True,
        "stream": False,
        "max_prefix": 1500,
        "max_suffix": 300,
    },
    "deepseek-coder-v2:16b": {
        "max_tokens": 70,
        "temperature": 0.0,
        "top_p": 0.9,
        "repeat_penalty": 1.1,
        "timeout": 60,
        "num_ctx": 2048,
        "fim_format": "deepseek",
        "use_cache": True,
        "stream": False,
        "max_prefix": 1500,
        "max_suffix": 300,
    },
    # Modelos pequeños - Configuración ultra agresiva
    "qwen2.5-coder:0.5b": {
        "max_tokens": 20,  # Muy reducido
        "temperature": 0.0,
        "top_p": 0.95,
        "repeat_penalty": 1.3,  # Más alto para evitar repetición
        "timeout": 15,
        "num_ctx": 768,  # Contexto mínimo
        "fim_format": "qwen",
        "use_cache": True,
        "stream": False,
        "max_prefix": 600,  # Muy reducido
        "max_suffix": 100,
    },
    "qwen2.5-coder:1.5b": {
        "max_tokens": 25,
        "temperature": 0.0,
        "top_p": 0.95,
        "repeat_penalty": 1.25,
        "timeout": 20,
        "num_ctx": 1024,
        "fim_format": "qwen",
        "use_cache": True,
        "stream": False,
        "max_prefix": 800,
        "max_suffix": 150,
    },
    "deepseek-coder:1.3b": {
        "max_tokens": 25,
        "temperature": 0.0,
        "top_p": 0.95,
        "repeat_penalty": 1.25,
        "timeout": 20,
        "num_ctx": 1024,
        "fim_format": "deepseek",
        "use_cache": True,
        "stream": False,
        "max_prefix": 800,
        "max_suffix": 150,
    },
}

# Stop tokens por formato
STOP_TOKENS = {
    "codellama": [
        "<FILL_HERE>", "<MID>", "<PRE>", "<SUF>",
        "<|endoftext|>", "<EOT>", "</s>",
        "\n\n\n", "```",
        "\n\n#", "\n\nIt", "\n\nThe", "\n\nThis",
    ],
    "deepseek": [
        "<|fim_suffix|>", "<|fim_prefix|>", "<|fim_middle|>",
        "<|endoftext|>", "<EOT>", "</s>",
        "\n\n\n", "```",
        "\n\n#", "\n\nprint(",
    ],
    "qwen": [
        "<|fim_suffix|>", "<|fim_prefix|>", "<|fim_middle|>",
        "<|im_end|>", "<|endoftext|>",
        "\n\n\n", "```",
        "\n\n#", "\n\nprint(",
        "\n\nEsta", "\n\nSuma", "\n\nExample",
        '"""', "'''",
    ],
}

def get_model_config(model):
    """Obtiene configuración optimizada para un modelo."""
    # Buscar configuración exacta
    if model in MODEL_CONFIGS:
        return MODEL_CONFIGS[model]
    
    # Buscar por patrón
    model_lower = model.lower()
    for pattern, config in MODEL_CONFIGS.items():
        if pattern.split(':')[0] in model_lower:
            return config
    
    # Configuración por defecto (CodeLlama style)
    return MODEL_CONFIGS["codellama:7b-code"]


def get_stop_tokens(fim_format):
    """Obtiene stop tokens por formato."""
    return STOP_TOKENS.get(fim_format, STOP_TOKENS["codellama"])
