# OllamaComplete - Autocompletado Profesional con IA Local

Plugin profesional de autocompletado para Sublime Text 4, optimizado para **todos los modelos Ollama** (pequeños y grandes). Similar a GitHub Copilot pero 100% local y privado.

## ✨ Características

- 🎯 **Texto fantasma inline** - Sugerencias en gris estilo Copilot
- ⚡ **100% Local** - Sin enviar código a la nube, privacidad total
- 🧠 **Optimizado por modelo** - Configuración específica para cada modelo
- 🚀 **Funciona con modelos pequeños** - Optimizado para 0.5B-3B
- 🎨 **Limpieza agresiva** - Solo código, sin explicaciones
- ⌨️ **Atajos tipo Copilot** - Ctrl+Space, Tab, Escape

## 📦 Instalación

### 1. Instalar Ollama

```bash
# Windows: Descarga desde https://ollama.com/download
winget install Ollama.Ollama

# Inicia el servicio
ollama serve
```

### 2. Instalar modelos

```bash
# Modelo recomendado (balance perfecto)
ollama pull codellama:7b-code

# Alternativas:
ollama pull deepseek-coder-v2:16b    # Mejor calidad
ollama pull codellama:13b-code       # Buena calidad
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
| `Ctrl+Shift+M` | Cambiar modelo rápidamente |

## ⚙️ Configuración

El plugin está optimizado automáticamente para cada modelo. Configuración actual:

```json
{
    "model": "codellama:7b-code",
    "max_tokens": 60,
    "temperature": 0.0
}
```

### Cambiar modelo

**Opción 1: Atajo rápido**
- Presiona `Ctrl+Shift+M`
- Selecciona el modelo de la lista

**Opción 2: Configuración manual**
- `Preferences > Package Settings > OllamaComplete > Settings`
- Cambiar `"model": "nombre-del-modelo"`

## 🎯 Modelos Recomendados

| Modelo | Tamaño | Velocidad | Calidad | Uso |
|--------|--------|-----------|---------|-----|
| codellama:7b-code | 3.8GB | ⚡⚡ 3-5s | ⭐⭐⭐⭐ | Diario |
| codellama:13b-code | 7.4GB | ⚡ 5-8s | ⭐⭐⭐⭐⭐ | Mejor calidad |
| deepseek-coder-v2:16b | 8.9GB | ⚡ 5-10s | ⭐⭐⭐⭐⭐ | Máxima calidad |

## 🔧 Optimizaciones Aplicadas

### Para Modelos Pequeños (0.5B-3B)
- ✅ Prompts simplificados
- ✅ Contexto reducido
- ✅ Configuración específica por modelo
- ✅ Limpieza agresiva de respuestas

### Para Modelos Grandes (7B+)
- ✅ Prompts FIM nativos
- ✅ Contexto completo
- ✅ Timeouts optimizados
- ✅ Mejor calidad de código

## 🎯 Ejemplos de Uso

### Python
```python
def calcular_promedio(numeros):
    # Presiona Ctrl+Space
    # Sugerencia: total = sum(numeros) / len(numeros)
```

### JavaScript
```javascript
const handleSubmit = async (e) => {
    // Presiona Ctrl+Space
    // Sugerencia: e.preventDefault(); ...
```

## 🔧 Solución de Problemas

### "No se pudo conectar a Ollama"

```bash
# Verifica que Ollama esté corriendo
ollama serve

# En otra terminal
ollama list
```

### "Timeout"

- Usa un modelo más pequeño
- Pre-carga el modelo: `ollama run codellama:7b-code "test"`
- Primera carga es lenta, las siguientes son rápidas

### "Genera explicaciones"

El plugin ya tiene limpieza agresiva. Si aún genera explicaciones:
- Reduce `max_tokens` a 40-50
- Cambia `temperature` a 0.0
- Usa un modelo más grande (mejor calidad)

## 📊 Rendimiento Esperado

**Primera sugerencia (carga en RAM):**
- codellama:7b-code: 10-15 segundos
- codellama:13b-code: 15-20 segundos
- deepseek-coder-v2:16b: 30-60 segundos

**Siguientes sugerencias (ya en RAM):**
- codellama:7b-code: 3-5 segundos ⚡
- codellama:13b-code: 5-8 segundos
- deepseek-coder-v2:16b: 5-10 segundos

## 🚀 Tips para Mejor Rendimiento

1. **Pre-carga el modelo:**
   ```bash
   ollama run codellama:7b-code "test"
   ```

2. **Mantén Ollama corriendo** - No lo cierres

3. **Usa el modelo adecuado:**
   - Edición rápida: codellama:7b-code
   - Código complejo: codellama:13b-code
   - Máxima calidad: deepseek-coder-v2:16b

## 📝 Licencia

MIT License - Úsalo libremente en tus proyectos.

---

**Hecho con ❤️ para desarrolladores que valoran su privacidad**
