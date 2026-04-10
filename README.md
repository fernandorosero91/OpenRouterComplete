# OllamaComplete - Autocompletado de Código con IA Local

Plugin profesional de autocompletado para Sublime Text 4, similar a GitHub Copilot pero usando modelos locales con Ollama.

## ✨ Características

- 🎯 **Texto fantasma inline** - Sugerencias en gris que no interrumpen tu flujo
- ⚡ **100% Local** - Sin enviar código a la nube, privacidad total
- 🧠 **Contexto inteligente** - Lee archivos del proyecto (models.py, urls.py, views.py)
- 🎨 **Detección de frameworks** - Django, Vue, React, Angular
- 🚀 **Optimizado por modelo** - Prompts FIM nativos para cada modelo
- ⌨️ **Atajos tipo Copilot** - Ctrl+Space, Tab, Escape

## 📦 Instalación

### 1. Instalar Ollama

```bash
# Windows: Descarga desde https://ollama.com/download
# O usa winget:
winget install Ollama.Ollama

# Inicia el servicio
ollama serve
```

### 2. Instalar modelos recomendados

```bash
# Modelo recomendado (balance perfecto)
ollama pull qwen2.5-coder:1.5b

# Alternativas:
ollama pull qwen2.5-coder:0.5b    # Ultra rápido
ollama pull deepseek-coder:1.3b   # Buena alternativa
ollama pull codellama:7b-code     # Mejor calidad (requiere GPU)
```

### 3. Instalar el plugin

1. Abre Sublime Text
2. Ve a `Preferences > Browse Packages`
3. Crea una carpeta llamada `OllamaComplete`
4. Copia estos archivos dentro:
   - `OpenRouterComplete.py`
   - `OpenRouterComplete.sublime-settings`
   - `Default.sublime-keymap`

## 🎮 Uso

### Atajos de teclado

| Atajo | Acción |
|-------|--------|
| `Ctrl+Space` | Solicitar sugerencia de código |
| `Tab` | Aceptar sugerencia |
| `Escape` | Cancelar sugerencia |
| `Ctrl+Shift+E` | Explicar código seleccionado |
| `Ctrl+Shift+M` | Cambiar modelo rápidamente |

### Modo automático (como Copilot)

Edita la configuración (`Preferences > Package Settings > OllamaComplete > Settings`):

```json
{
    "auto_complete": true,
    "auto_complete_delay": 1500
}
```

Ahora las sugerencias aparecerán automáticamente mientras escribes.

## ⚙️ Configuración

### Cambiar modelo

**Opción 1: Atajo rápido**
- Presiona `Ctrl+Shift+M`
- Selecciona el modelo de la lista

**Opción 2: Configuración manual**

```json
{
    "model": "qwen2.5-coder:1.5b",
    "max_tokens": 120,
    "temperature": 0.05
}
```

### Modelos recomendados según tu hardware

| Hardware | Modelo recomendado | Velocidad |
|----------|-------------------|-----------|
| CPU básico | `qwen2.5-coder:0.5b` | ⚡⚡⚡ Ultra rápido |
| CPU medio | `qwen2.5-coder:1.5b` | ⚡⚡ Rápido |
| CPU potente | `deepseek-coder:1.3b` | ⚡⚡ Rápido |
| GPU | `codellama:7b-code` | ⚡ Mejor calidad |

## 🔧 Solución de problemas

### "No se pudo conectar a Ollama"

```bash
# Verifica que Ollama esté corriendo
ollama serve

# En otra terminal, verifica que funcione
ollama list
```

### "Timeout: Ollama tardó demasiado"

- Usa un modelo más pequeño: `qwen2.5-coder:0.5b`
- Reduce `max_tokens` en la configuración

### Las sugerencias no son buenas

- Prueba con `codellama:7b-code` (requiere más recursos)
- Ajusta `temperature` (más bajo = más conservador)
- Asegúrate de tener archivos del proyecto abiertos para contexto

## 🎯 Ejemplos de uso

### Python/Django
```python
# Escribe esto:
def calculate_total_price(items):
    # Presiona Ctrl+Space
    # El modelo sugiere el código completo basándose en tus models.py
```

### JavaScript/React
```javascript
// Escribe esto:
const handleSubmit = async (e) => {
    // Presiona Ctrl+Space
    // Sugerencia inteligente basada en tu código
```

### HTML/Django Templates
```html
<!-- Escribe esto: -->
{% for product in products %}
    <!-- Presiona Ctrl+Space -->
    <!-- Sugerencia basada en tus models.py y urls.py -->
```

## 📊 Comparación de modelos

| Modelo | Tamaño | RAM | Velocidad | Calidad | Mejor para |
|--------|--------|-----|-----------|---------|------------|
| qwen2.5-coder:0.5b | 400MB | 2GB | ⚡⚡⚡ | ⭐⭐⭐ | Auto-complete rápido |
| qwen2.5-coder:1.5b | 986MB | 4GB | ⚡⚡ | ⭐⭐⭐⭐ | Balance perfecto |
| deepseek-coder:1.3b | 776MB | 3GB | ⚡⚡ | ⭐⭐⭐⭐ | Alternativa sólida |
| codellama:7b-code | 3.8GB | 8GB | ⚡ | ⭐⭐⭐⭐⭐ | Máxima calidad |

## 🚀 Tips para mejor rendimiento

1. **Mantén archivos del proyecto abiertos** - El plugin lee `models.py`, `urls.py`, `views.py` para contexto
2. **Usa el modelo adecuado** - Más grande no siempre es mejor
3. **Ajusta max_tokens** - 80-120 es ideal para completado inline
4. **Temperatura baja** - 0.05-0.1 para código más predecible
5. **Auto-complete selectivo** - Desactívalo en archivos grandes

## 📝 Licencia

MIT License - Úsalo libremente en tus proyectos.

## 🤝 Contribuciones

¿Mejoras? ¡Pull requests bienvenidos!

---

**Hecho con ❤️ para desarrolladores que valoran su privacidad**
