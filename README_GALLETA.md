# 🍪 Galleta - Asistente Virtual Conversacional

Galleta es un agente conversacional inteligente y amigable que puede ayudarte con información sobre viajes y mucho más. Lo mejor: **tiene memoria** de tus conversaciones anteriores.

## ✨ Características Principales

- 🧠 **Memoria Conversacional**: Recuerda todo lo que le dices durante la sesión
- 💬 **Conversación Natural**: Habla de cualquier tema, no solo viajes
- ✈️ **Información de Viajes**: Catálogo de 8 destinos increíbles
- 🎯 **Simulación de Reservas**: Puede simular reservaciones (sin base de datos real)
- 🤗 **Personalidad Amigable**: Siempre simpático y servicial

## 🚀 Inicio Rápido

### Requisitos

- Python 3.10+
- API Key de Groq (configurada en `.env`)

### Configuración

1. **Asegúrate de tener tu API key configurada en `.env`:**
```env
GROQ_API_KEY=tu_api_key_aqui
```

2. **Instalar dependencias** (si no lo has hecho):
```bash
pip install -r requirements.txt
```

### Usar el Agente

#### Modo Interactivo (Recomendado)
Chatea directamente con Galleta en la terminal:

```bash
python test_galleta.py
```

Ejemplos de conversación:
```
👤 Tú: Hola, mi nombre es Ana
🍪 Galleta: ¡Hola Ana! 🍪 ¡Mucho gusto! ¿En qué puedo ayudarte hoy?

👤 Tú: ¿Qué viajes tienes disponibles?
🍪 Galleta: Tengo varios destinos increíbles...

👤 Tú: ¿Cuál es mi nombre?
🍪 Galleta: Tu nombre es Ana 😊

👤 Tú: ¿Qué opinas del café?
🍪 Galleta: ¡Me encanta el café! ☕ [...]
```

#### Modo de Pruebas Automatizadas
Ejecuta un conjunto de pruebas predefinidas:

```bash
python test_galleta.py --test
```

#### Desde LangGraph Studio
Visualiza el grafo del agente:

```bash
langgraph dev
```

Abre `http://localhost:8123` en tu navegador.

## 💡 Lo Que Galleta Puede Hacer

### 1. Conversación General
- Responder preguntas sobre cualquier tema
- Mantener conversaciones naturales
- Recordar información que le compartes

```
"¿Qué opinas de la inteligencia artificial?"
"Cuéntame un chiste"
"¿Cómo está el clima hoy?"
```

### 2. Información de Viajes
- Mostrar el catálogo completo
- Detalles de destinos específicos
- Comparar precios y fechas

```
"¿Qué viajes tienes?"
"Cuéntame sobre el viaje a París"
"¿Cuál es el viaje más barato?"
```

### 3. Reservaciones Simuladas
- Crear reservaciones (solo en memoria, no persiste)
- Ver reservaciones del usuario
- Consultar detalles

```
"Quiero reservar el viaje a Cancún"
"Muéstrame mis reservaciones"
```

### 4. Memoria Conversacional
- Recuerda tu nombre y preferencias
- Hace seguimiento del contexto
- Puede retomar temas anteriores

```
Usuario: "Mi nombre es Carlos"
[más tarde...]
Usuario: "¿Cuál es mi nombre?"
Galleta: "Tu nombre es Carlos 😊"
```

## 🗂️ Estructura del Código

```
src/main.py
├── VIAJES_CATALOGO          # Datos estáticos de viajes
├── RESERVACIONES            # Almacenamiento en memoria
├── obtener_viajes()         # Devuelve catálogo
├── crear_reservacion_mock() # Simula reservaciones
├── chatbot()                # Nodo principal del agente
└── agent                    # Agente compilado con memoria
```

## 📊 Catálogo de Viajes

| Destino | Precio | Salida | Regreso | Cupos |
|---------|--------|--------|---------|-------|
| Cancún, México | $1,299.99 | 2025-12-15 | 2025-12-22 | 20 |
| París, Francia | $2,499.99 | 2025-11-20 | 2025-11-27 | 15 |
| Machu Picchu, Perú | $1,899.99 | 2026-01-10 | 2026-01-17 | 12 |
| Tokyo, Japón | $3,299.99 | 2026-02-05 | 2026-02-15 | 10 |
| Cartagena, Colombia | $899.99 | 2025-12-01 | 2025-12-08 | 25 |
| Nueva York, USA | $1,799.99 | 2025-11-25 | 2025-12-02 | 18 |
| Barcelona, España | $2,199.99 | 2026-03-15 | 2026-03-22 | 14 |
| Río de Janeiro, Brasil | $1,599.99 | 2026-02-20 | 2026-02-27 | 22 |

## 🔧 Personalización

### Modificar la Personalidad

Edita el `system_message` en `src/main.py`:

```python
system_message = SystemMessage(content="""
    Eres Galleta 🍪, un asistente virtual...
    [Personaliza aquí el comportamiento]
""")
```

### Agregar Más Viajes

Edita la lista `VIAJES_CATALOGO` en `src/main.py`:

```python
VIAJES_CATALOGO.append({
    "id": 9,
    "destino": "Tu Destino",
    "descripcion": "Descripción del viaje",
    "precio": 999.99,
    # ...
})
```

### Cambiar el Modelo LLM

```python
llm = init_chat_model(
    "llama-3.1-70b-versatile",  # Modelo más potente
    model_provider="groq",
    temperature=0.7
)
```

## 🧪 Ejemplos de Uso Programático

### Conversación Simple
```python
from src.main import agent
from langchain_core.messages import HumanMessage

config = {"configurable": {"thread_id": "user_123"}}

result = agent.invoke(
    {"messages": [HumanMessage(content="Hola, ¿qué tal?")]},
    config=config
)

print(result["messages"][-1].content)
```

### Conversación con Memoria
```python
# Primera interacción
result1 = agent.invoke(
    {"messages": [HumanMessage(content="Mi nombre es María")]},
    config=config
)

# Segunda interacción (recuerda el nombre)
result2 = agent.invoke(
    {"messages": [HumanMessage(content="¿Cuál es mi nombre?")]},
    config=config
)
```

## ⚙️ Cómo Funciona la Memoria

Galleta usa **LangGraph's MemorySaver** que:
- Mantiene el historial completo de mensajes por thread
- Cada `thread_id` es una conversación separada
- La memoria persiste mientras el programa está corriendo
- Se reinicia cuando cierras y vuelves a abrir

## 🎯 Casos de Uso

1. **Página Web Estática**: Integra con frontend para chatbot de viajes
2. **Asistente Personal**: Responde preguntas generales y ayuda con tareas
3. **Demo de Agencia de Viajes**: Muestra capacidades conversacionales
4. **Prototipo de Chatbot**: Base para desarrollar funcionalidades más complejas

## 🔄 Diferencias con Versión Anterior

| Antes | Ahora |
|-------|-------|
| ❌ No recordaba conversaciones | ✅ Memoria completa |
| ❌ Solo hablaba de viajes | ✅ Cualquier tema |
| ❌ Necesitaba base de datos | ✅ Todo en memoria |
| ❌ Complejo (3 nodos) | ✅ Simple (1 nodo) |

## 🐛 Solución de Problemas

### El agente no responde
- Verifica que tengas la API key de Groq configurada
- Revisa la conexión a internet

### No recuerda conversaciones anteriores
- Asegúrate de usar el mismo `thread_id` en las invocaciones
- La memoria se reinicia al cerrar el programa

### Respuestas poco naturales
- Ajusta el `temperature` del modelo (0.5-0.9)
- Modifica el system prompt para ser más específico

## 📝 Próximos Pasos

Ideas para mejorar:
- [ ] Persistir memoria en archivo/DB (SQLite, JSON)
- [ ] Integrar con frontend web (Flask, FastAPI)
- [ ] Agregar más acciones (cancelar reservas, etc.)
- [ ] Sistema de recomendaciones basado en preferencias
- [ ] Múltiples idiomas
- [ ] Voice input/output

## 🤝 Contribuir

Este es un proyecto personal, pero siéntete libre de:
- Reportar bugs
- Sugerir mejoras
- Hacer fork y personalizar

---

**¡Disfruta conversando con Galleta! 🍪**
