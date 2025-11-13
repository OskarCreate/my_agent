# 🍪 Agente Galleta - Sistema de Reservaciones de Viajes

Galleta es un agente conversacional inteligente que te ayuda a gestionar reservaciones de viajes de manera natural y amigable.

## 🎯 Funcionalidades

El agente Galleta puede:

1. **Mostrar viajes disponibles**: Ver el catálogo completo de viajes con precios, fechas y cupos
2. **Crear reservaciones**: Reservar viajes de manera conversacional
3. **Ver tus reservaciones**: Consultar todas tus reservaciones activas
4. **Verificar detalles**: Obtener información detallada de una reservación específica

## 🚀 Configuración Inicial

### 1. Configurar variables de entorno

Asegúrate de tener un archivo `.env` con las credenciales de tu base de datos:

```env
DB_HOST=tu-host.postgres.render.com
DB_NAME=tu_base_de_datos
DB_USER=tu_usuario
DB_PASSWORD=tu_password
DB_PORT=5432
DB_SSLMODE=require

# API Key de Groq (necesaria para el LLM)
GROQ_API_KEY=tu_api_key_de_groq
```

### 2. Inicializar la base de datos

Ejecuta el script de setup para crear las tablas y cargar datos de ejemplo:

```bash
python setup_database.py
```

Esto creará:
- Tabla `viajes` con 8 destinos de ejemplo
- Tabla `reservaciones` para guardar las reservas
- Índices para optimizar las consultas

## 💬 Ejemplos de Uso

### Consultar viajes disponibles

```
Usuario: "Hola, ¿qué viajes tienes disponibles?"
Usuario: "Muéstrame los viajes"
Usuario: "Quiero ver el catálogo de viajes"
```

### Crear una reservación

```
Usuario: "Quiero reservar el viaje a Cancún"
Usuario: "Quiero hacer una reservación para 2 personas al viaje 1"
Usuario: "Reservar viaje a París para el 20 de noviembre"
```

### Ver tus reservaciones

```
Usuario: "Muéstrame mis reservaciones"
Usuario: "¿Qué viajes he reservado?"
Usuario: "Ver mis reservas"
```

### Verificar una reservación específica

```
Usuario: "¿Cuáles son los detalles de mi reservación 5?"
Usuario: "Verificar reservación número 3"
Usuario: "Información de la reserva 1"
```

## 🔧 Estructura del Código

```
src/main.py
├── Funciones de Base de Datos
│   ├── obtener_viajes_disponibles()
│   ├── crear_reservacion()
│   ├── obtener_reservaciones_usuario()
│   └── verificar_reservacion()
├── Nodos del Agente (LangGraph)
│   ├── analizar_intencion()    # Detecta qué quiere hacer el usuario
│   ├── ejecutar_accion()       # Ejecuta la acción en la BD
│   └── generar_respuesta()     # Genera respuesta amigable
└── Grafo del Agente
    └── START → Analizar → Ejecutar → Responder → END
```

## 🧪 Testing del Agente

Puedes probar el agente de varias formas:

### Opción 1: LangGraph Studio (Recomendado)
```bash
langgraph dev
```
Luego abre el navegador en `http://localhost:8123`

### Opción 2: Python directo
```python
from src.main import agent
from langchain_core.messages import HumanMessage

# Configurar usuario
state = {
    "messages": [HumanMessage(content="¿Qué viajes tienes?")],
    "user_id": 1,
    "user_name": "Carlos"
}

# Invocar agente
result = agent.invoke(state)
print(result["messages"][-1].content)
```

### Opción 3: Script de prueba
```python
# test_galleta.py
from src.main import agent
from langchain_core.messages import HumanMessage

def test_agent(message: str, user_id: int = 1, user_name: str = "Usuario"):
    state = {
        "messages": [HumanMessage(content=message)],
        "user_id": user_id,
        "user_name": user_name
    }
    result = agent.invoke(state)
    return result["messages"][-1].content

# Ejemplos
print(test_agent("¿Qué viajes tienes?"))
print(test_agent("Quiero reservar el viaje 1 para 2 personas"))
print(test_agent("Muéstrame mis reservaciones"))
```

## 📊 Esquema de Base de Datos

### Tabla `viajes`
```sql
id                  SERIAL PRIMARY KEY
destino             VARCHAR(255)
descripcion         TEXT
precio              DECIMAL(10,2)
fecha_salida        DATE
fecha_regreso       DATE
cupos_disponibles   INTEGER
created_at          TIMESTAMP
```

### Tabla `reservaciones`
```sql
id                  SERIAL PRIMARY KEY
usuario_id          INTEGER
viaje_id            INTEGER (FK -> viajes.id)
num_personas        INTEGER
fecha_reservacion   TIMESTAMP
estado              VARCHAR(50)
total               DECIMAL(10,2)
```

## 🎨 Personalización

### Cambiar el comportamiento del agente

Edita los prompts del sistema en `src/main.py`:

```python
# En analizar_intencion()
system_prompt = f"""
    Eres Galleta 🍪, un asistente...
    [personaliza aquí el comportamiento]
"""

# En generar_respuesta()
system_prompt = f"""
    Eres Galleta 🍪, un asistente...
    [personaliza el tono de las respuestas]
"""
```

### Agregar nuevas acciones

1. Define la función en la sección de funciones de BD
2. Agrégala a `ejecutar_accion()`
3. Documéntala en el prompt de `analizar_intencion()`

## 🐛 Solución de Problemas

### Error de conexión a base de datos
- Verifica tus credenciales en `.env`
- Asegúrate de que la base de datos esté accesible
- Confirma que el SSL mode sea correcto

### El agente no entiende las solicitudes
- Verifica que tengas configurada la API key de Groq
- Intenta formular la solicitud de forma más clara
- Revisa los logs para ver qué intención detectó

### Errores en las reservaciones
- Verifica que el viaje_id exista en la tabla `viajes`
- Confirma que haya cupos disponibles
- Asegúrate de que el user_id sea válido

## 📝 Próximos Pasos

Ideas para extender el agente:
- [ ] Cancelar reservaciones
- [ ] Modificar reservaciones existentes
- [ ] Sistema de notificaciones por email
- [ ] Integración con pasarela de pagos
- [ ] Filtros avanzados de búsqueda (por precio, fecha, destino)
- [ ] Sistema de recomendaciones personalizadas

## 📄 Licencia

Este proyecto es de código abierto y está disponible bajo la licencia MIT.
