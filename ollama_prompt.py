"""
Construcción de prompts optimizados
"""

def build_prompt_codellama(prefix, suffix, max_prefix=1200, max_suffix=250):
    """Prompt ultra optimizado para CodeLlama - Máxima velocidad."""
    # Reducir contexto agresivamente para velocidad
    if len(prefix) > max_prefix:
        lines = prefix.split('\n')
        # Tomar solo las últimas 20 líneas relevantes
        prefix = '\n'.join(lines[-20:])
    
    # Reducir suffix también
    if len(suffix) > max_suffix:
        lines = suffix.split('\n')
        suffix = '\n'.join(lines[:4])
    
    # Formato SPM de CodeLlama
    return "<PRE> {0} <SUF>{1} <MID>".format(prefix, suffix)


def build_prompt_deepseek(prefix, suffix, max_prefix=1500, max_suffix=300):
    """Prompt optimizado para DeepSeek."""
    if len(prefix) > max_prefix:
        lines = prefix.split('\n')
        prefix = '\n'.join(lines[-25:])
    
    if len(suffix) > max_suffix:
        lines = suffix.split('\n')
        suffix = '\n'.join(lines[:6])
    
    return "<|fim_prefix|>{0}<|fim_suffix|>{1}<|fim_middle|>".format(prefix, suffix)


def build_prompt_qwen(prefix, suffix, max_prefix=800, max_suffix=150):
    """Prompt ultra optimizado para Qwen - Modelos pequeños."""
    # Contexto muy reducido para modelos pequeños
    if len(prefix) > max_prefix:
        lines = prefix.split('\n')
        # Solo últimas 10 líneas para modelos pequeños
        prefix = '\n'.join(lines[-10:])
    
    if len(suffix) > max_suffix:
        lines = suffix.split('\n')
        suffix = '\n'.join(lines[:2])
    
    # Formato directo sin instrucciones
    return "<|fim_prefix|>{0}<|fim_suffix|>{1}<|fim_middle|>".format(prefix, suffix)


def build_prompt(prefix, suffix, fim_format, max_prefix=1200, max_suffix=250):
    """Construye el prompt óptimo según el formato."""
    if fim_format == "codellama":
        return build_prompt_codellama(prefix, suffix, max_prefix, max_suffix)
    elif fim_format == "deepseek":
        return build_prompt_deepseek(prefix, suffix, max_prefix, max_suffix)
    elif fim_format == "qwen":
        return build_prompt_qwen(prefix, suffix, max_prefix, max_suffix)
    else:
        # Fallback simple
        return prefix
