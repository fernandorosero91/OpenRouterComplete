# OllamaComplete - Autocompletado Profesional con IA Local

Plugin profesional de autocompletado para Sublime Text 4 usando modelos locales de Ollama. Similar a GitHub Copilot pero 100% local y privado.

## ✨ Características Principales

- 🚀 **Ultra rápido** - Arquitectura modular optimizada para máxima velocidad
- 💻 **100% Local** - Sin internet, sin cloud, privacidad total
- 🎯 **Caché inteligente** - Completions instantáneas para código repetido
- � **Pre-calentamiento** - Modelo listo desde el inicio .de Sublime
- ⚡ **Contexto optimizado** - Mínimo contexto para máxima velocidad
- 🎨 **UI tipo Copilot** - Texto fantasma gris, Tab para aceptar
- 🏗️ **Arquitectura modular** - 6 módulos especializados para rendimiento

## 🎯 Modelos Recomendados

| Modelo | RAM | Velocidad | Calidad | Recomendación |
|--------|-----|-----------|---------|---------------|
| **codellama:7b-code** | 8GB | ⚡⚡⚡ 2-3s | ⭐⭐⭐⭐⭐ | **MEJOR OPCIÓN** |
| codellama:13b-code | 16GB | ⚡⚡ 3-5s | ⭐⭐⭐⭐⭐ | Más lento pero mejor |
| deepseek-coder-v2:16b | 20GB | ⚡ 5-8s | ⭐⭐⭐⭐⭐ | Máxima calidad |

⚠️ **Modelos <3B NO funcionan bien** - Generan explicaciones en lugar de código limpio.

## 📦 Instalación

### 1. Instalar Ollama

```bash
# Windows: Descargar de https://ollama.ai
# Verificar instalación
ollama --version
```

### 2. Descargar modelo recomendado

```bash
ollama pull codellama:7b-code
```

### 3. Iniciar Ollama

```bash
ollama serve
```

### 4. Instalar plugin

1. Abre Sublime Text
2. Ve a `Preferences > Browse Packages`
3. Crea carpeta `OllamaComplete`
4. Copia todos los archivos `.py`, `.sublime-settings` y `.sublime-keymap`
5. Reinicia Sublime Text

## ⌨️ Atajos de Teclado

| Atajo | Acción |
|-------|--------|
| `Ctrl+Space` | Solicitar sugerencia |
| `Tab` | Aceptar sugerencia |
| `Escape` | Cancelar sugerencia |
| `Ctrl+Shift+M` | Cambiar modelo |

## ⚙️ Configuración

Archivo: `Preferences > Package Settings > OllamaComplete > Settings`

```json
{
    "model": "codellama:7b-code"
}
```

## 🏗️ Arquitectura Modular Profesional

```
OllamaComplete/
├── OpenRouterComplete.py      # Plugin principal + comandos
├── ollama_client.py            # Cliente API + caché inteligente
├── ollama_config.py            # Configuraciones optimizadas por modelo
├── ollama_prompt.py            # Construcción de prompts FIM
├── ollama_cleaner.py           # Limpieza ultra agresiva
└── ollama_ui.py                # Interfaz phantom + status bar
```

## � Optimizaciones Implementadas

### 1. Contexto Ultra Reducido
- Prefijo: 1200 chars (solo últimas 20 líneas)
- Sufijo: 250 chars (solo próximas 4 líneas)
- Resultado: 3x más rápido

### 2. Caché Inteligente
- Guarda últimas 50 completions
- Respuesta instantánea (<100ms) para código repetido
- Hash MD5 para identificación rápida

### 3. Pre-calentamiento de Modelo
- Modelo se carga al iniciar Sublime
- Primera completion ya es rápida
- Sin espera de 10-15s en primera ejecución

### 4. Parámetros Optimizados
- `max_tokens`: 40 (solo lo necesario)
- `temperature`: 0.0 (determinista)
- `num_ctx`: 1536 (contexto mínimo)
- `num_thread`: 6 (optimizado para i7)
- `num_batch`: 256 (procesamiento rápido)

### 5. Limpieza Ultra Agresiva
- Remueve tokens basura
- Corta explicaciones
- Limita a 10 líneas máximo
- Máximo 300 caracteres
- Solo código puro

### 6. Thread Management
- Worker threads no bloquean UI
- Cancelación automática de requests antiguos
- Limpieza de recursos al cerrar vistas

## 📊 Rendimiento Real

Con CodeLlama 7B en Core i7 32GB RAM:

| Situación | Tiempo |
|-----------|--------|
| Primera completion (con pre-calentamiento) | ~2-3s ⚡⚡⚡ |
| Completions siguientes | ~2-3s ⚡⚡⚡ |
| Completions en caché | <100ms ⚡⚡⚡⚡⚡ |

## 🎯 Ejemplos de Uso

### Python
```python
def calculate_fibonacci(
# Ctrl+Space → Sugerencia aparece en gris
# Tab → Acepta
n):
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)
```

### JavaScript
```javascript
const handleSubmit = async (e) => {
// Ctrl+Space
e.preventDefault();
const data = await fetch('/api/submit', {
    method: 'POST',
    body: JSON.stringify(formData)
});
```

## � Troubleshooting

### Error: "Ollama no está corriendo"
```bash
ollama serve
```

### Muy lento (>5s)
- ✅ Usar `codellama:7b-code` (no 13b)
- ✅ Verificar que Ollama está corriendo
- ✅ Cerrar otras aplicaciones pesadas
- ✅ Pre-calentar: `ollama run codellama:7b-code "test"`

### Genera explicaciones
- ✅ Modelos <3B no funcionan bien
- ✅ Usar CodeLlama 7B o superior
- ✅ Plugin ya tiene limpieza ultra agresiva

### Primera completion muy lenta
- ✅ Normal: modelo se carga en RAM
- ✅ Plugin pre-calienta automáticamente
- ✅ Siguientes completions son rápidas

## 🎯 Comparación con Copilot

| Característica | OllamaComplete | GitHub Copilot |
|----------------|----------------|----------------|
| Privacidad | ✅ 100% local | ❌ Cloud |
| Velocidad | ⚡⚡⚡ 2-3s | ⚡⚡⚡⚡ <1s |
| Costo | ✅ Gratis | 💰 $10/mes |
| Offline | ✅ Sí | ❌ No |
| Calidad | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Arquitectura | ✅ Modular | ❓ Propietaria |

## 🚀 Tips para Máximo Rendimiento

1. **Mantén Ollama corriendo** - No lo cierres entre sesiones
2. **Usa CodeLlama 7B** - Mejor balance velocidad/calidad
3. **Deja que el caché trabaje** - Código repetido es instantáneo
4. **Pre-calienta al inicio** - Plugin lo hace automáticamente
5. **Cierra apps pesadas** - Más RAM para el modelo

## 📄 Licencia

MIT License - Uso libre para proyectos personales y comerciales

## 🤝 Contribuciones

Pull requests bienvenidos para:
- Mejorar velocidad
- Optimizar limpieza de respuestas
- Soporte para más modelos
- Nuevas características

---

**Desarrollado con ❤️ para desarrolladores que valoran privacidad y velocidad**

**Arquitectura modular profesional - 6 módulos especializados**
