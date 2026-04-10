"""
Limpieza ultra agresiva de respuestas
"""
import re

# Tokens basura comunes
BAD_TOKENS = [
    "<|endoftext|>", "<|fim_suffix|>", "<|fim_prefix|>", "<|fim_middle|>",
    "<EOT>", "</s>", "<s>", "[INST]", "[/INST]",
    "<PRE>", "<SUF>", "<MID>", "<FILL_HERE>",
    "<|eot_id|>", "<|im_end|>", "<|im_start|>", "<|end|>",
    "<fim_prefix>", "<fim_suffix>", "<fim_middle>",
    "<|assistant|>", "<|user|>",
    "```python", "```javascript", "```java", "```cpp", "```c", "```",
    "```", "'''", '"""',
]

# Palabras que indican explicación (más agresivo)
EXPLANATION_KEYWORDS = [
    'the function', 'this function', 'the code', 'this code',
    'here is', "here's", 'this is', 'the provided', 'in this',
    'note:', 'explanation:', 'step-by-step', 'breakdown',
    'how it works', 'what this does', 'to understand',
    'la función', 'el código', 'esta función', 'este código',
    'aquí está', 'esto es', 'nota:', 'explicación:', 'esta función',
    'it looks', 'however', 'note that', 'you can', 'we can',
    'this will', 'this should', 'let me', 'i will',
    'first,', 'second,', 'then,', 'finally,',
    'example:', 'usage:', 'output:', 'result:', 'ejemplo',
    'suma dos', 'toma dos', 'realiza', 'devuelve',
    'args:', 'returns:', 'salida:', 'el primer', 'el segundo',
]

# Patrones de explicación
EXPLANATION_PATTERNS = [
    r'^\s*#\s*(explanation|note|example|usage|output|result|ejemplo|salida|args|returns):',
    r'^\s*//\s*(explanation|note|example|usage|output|result):',
    r'^\s*\d+\.\s+',  # Listas numeradas
    r'^\s*[-*]\s+',   # Listas con bullets
    r'^\s*""".*"""',  # Docstrings
    r"^\s*'''.*'''",  # Docstrings
]


def remove_bad_tokens(text):
    """Remueve tokens basura."""
    for token in BAD_TOKENS:
        text = text.replace(token, "")
    return text


def remove_code_fences(text):
    """Remueve code fences de markdown - Ultra agresivo."""
    # Remover bloques completos de código markdown
    text = re.sub(r'```[a-z]*\n', '', text)
    text = re.sub(r'```', '', text)
    
    # Si empieza con lenguaje (python, javascript, etc)
    if text.startswith(('python', 'javascript', 'java', 'cpp', 'c\n')):
        lines = text.split('\n', 1)
        if len(lines) > 1:
            text = lines[1]
    
    return text.strip()


def remove_docstrings(text):
    """Remueve docstrings de Python."""
    # Remover docstrings de triple comilla
    text = re.sub(r'""".*?"""', '', text, flags=re.DOTALL)
    text = re.sub(r"'''.*?'''", '', text, flags=re.DOTALL)
    return text


def cut_at_explanation(text):
    """Corta el texto en la primera explicación detectada."""
    # Patrones de explicación
    patterns = [
        r'\n\n(It looks|However|Note that|This code|The code|Here is|Esta función|Suma dos)',
        r'\n\n(Parece que|Sin embargo|Nota|Este código)',
        r'\n\n\d+\.',  # Listas numeradas
        r'\n\n[*-]\s',  # Listas con bullets
        r'\n# (Ejemplo|Example|Usage|Uso)',
        r'\nprint\(',  # Ejemplos de uso
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return text[:match.start()].strip()
    
    return text


def filter_explanation_lines(text):
    """Filtra líneas que son explicaciones - Ultra agresivo."""
    lines = text.split('\n')
    code_lines = []
    in_docstring = False
    
    for line in lines:
        stripped = line.strip()
        
        # Detectar inicio/fin de docstring
        if '"""' in stripped or "'''" in stripped:
            in_docstring = not in_docstring
            continue
        
        if in_docstring:
            continue
        
        # Saltar líneas vacías al inicio
        if not stripped and not code_lines:
            continue
        
        # Saltar líneas explicativas
        lower = stripped.lower()
        if any(lower.startswith(kw) for kw in EXPLANATION_KEYWORDS):
            break
        
        # Saltar patrones de explicación
        skip = False
        for pattern in EXPLANATION_PATTERNS:
            if re.match(pattern, stripped, re.IGNORECASE):
                skip = True
                break
        if skip:
            continue
        
        # Saltar líneas markdown
        if stripped.startswith(('**', '##', '###', '---')):
            continue
        
        # Saltar comentarios largos que son explicaciones
        if stripped.startswith('#'):
            # Si tiene palabras clave de explicación, saltar
            if any(kw in lower for kw in ['suma', 'toma', 'devuelve', 'realiza', 'args', 'returns', 'ejemplo']):
                continue
            # Si es muy largo sin código, saltar
            if len(stripped) > 50 and not any(c in stripped for c in ['=', '(', ')', '[', ']', '{', '}']):
                continue
        
        # Saltar líneas con print (ejemplos)
        if 'print(' in stripped:
            break
        
        code_lines.append(line)
    
    return '\n'.join(code_lines)


def remove_prefix_repetition(text, prefix):
    """Remueve repetición del prefijo."""
    if not prefix:
        return text
    
    prefix_lines = prefix.rstrip().split('\n')
    for line in prefix_lines[-3:]:
        line_clean = line.strip()
        if line_clean and text.startswith(line_clean):
            text = text[len(line_clean):].lstrip()
    
    return text


def clean_completion(text, prefix):
    """Limpieza profesional ultra agresiva - SOLO CÓDIGO."""
    if not text:
        return ""
    
    text = text.strip()
    
    # Pipeline de limpieza EXTREMADAMENTE agresivo
    text = remove_code_fences(text)
    text = remove_bad_tokens(text)
    text = remove_docstrings(text)
    text = cut_at_explanation(text)
    text = filter_explanation_lines(text)
    text = remove_prefix_repetition(text, prefix)
    
    # Cortar en triple salto de línea
    if '\n\n\n' in text:
        text = text.split('\n\n\n')[0]
    
    # Cortar en doble salto si después hay texto sin indentación (explicación)
    parts = text.split('\n\n')
    if len(parts) > 1:
        second_part = parts[1].strip()
        if second_part and not second_part[0] in ' \t' and len(second_part) > 30:
            text = parts[0]
    
    # Limitar a máximo 5 líneas para modelos pequeños
    lines = text.split('\n')
    if len(lines) > 5:
        text = '\n'.join(lines[:5])
    
    # Cortar si es muy largo (>200 chars para modelos pequeños)
    if len(text) > 200:
        # Cortar en la última línea completa
        text = text[:200].rsplit('\n', 1)[0]
    
    # Remover líneas vacías al final
    text = text.rstrip()
    
    return text
