from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, BaseMessage, trim_messages
from langchain.chat_models import init_chat_model
from typing import Literal, TypedDict, List, Dict, Any, Annotated
import os
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

# Modelo LLM
llm = init_chat_model("llama-3.1-8b-instant", model_provider="groq", temperature=0.7)

# Datos estáticos de viajes (sin base de datos)
VIAJES_CATALOGO = [
    {
        "id": 1,
        "destino": "Cancún, México",
        "descripcion": "Playas paradisíacas con todo incluido. Hotel 5 estrellas frente al mar.",
        "precio": 1299.99,
        "fecha_salida": "2025-12-15",
        "fecha_regreso": "2025-12-22",
        "cupos_disponibles": 20
    },
    {
        "id": 2,
        "destino": "París, Francia",
        "descripcion": "Tour romántico por la ciudad del amor. Incluye Torre Eiffel y Louvre.",
        "precio": 2499.99,
        "fecha_salida": "2025-11-20",
        "fecha_regreso": "2025-11-27",
        "cupos_disponibles": 15
    },
    {
        "id": 3,
        "destino": "Machu Picchu, Perú",
        "descripcion": "Aventura histórica en las ruinas incas. Incluye guía y transporte.",
        "precio": 1899.99,
        "fecha_salida": "2026-01-10",
        "fecha_regreso": "2026-01-17",
        "cupos_disponibles": 12
    },
    {
        "id": 4,
        "destino": "Tokyo, Japón",
        "descripcion": "Experiencia cultural única. Templos, tecnología y gastronomía.",
        "precio": 3299.99,
        "fecha_salida": "2026-02-05",
        "fecha_regreso": "2026-02-15",
        "cupos_disponibles": 10
    },
    {
        "id": 5,
        "destino": "Cartagena, Colombia",
        "descripcion": "Ciudad amurallada y playas caribeñas. Historia y diversión.",
        "precio": 899.99,
        "fecha_salida": "2025-12-01",
        "fecha_regreso": "2025-12-08",
        "cupos_disponibles": 25
    },
    {
        "id": 6,
        "destino": "Nueva York, USA",
        "descripcion": "La Gran Manzana te espera. Broadway, museos y Times Square.",
        "precio": 1799.99,
        "fecha_salida": "2025-11-25",
        "fecha_regreso": "2025-12-02",
        "cupos_disponibles": 18
    },
    {
        "id": 7,
        "destino": "Barcelona, España",
        "descripcion": "Arte, arquitectura y playa mediterránea. Sagrada Familia y más.",
        "precio": 2199.99,
        "fecha_salida": "2026-03-15",
        "fecha_regreso": "2026-03-22",
        "cupos_disponibles": 14
    },
    {
        "id": 8,
        "destino": "Río de Janeiro, Brasil",
        "descripcion": "Carnaval, playas y el Cristo Redentor. Pura alegría.",
        "precio": 1599.99,
        "fecha_salida": "2026-02-20",
        "fecha_regreso": "2026-02-27",
        "cupos_disponibles": 22
    }
]

# Almacenamiento temporal de reservaciones (en memoria)
RESERVACIONES = {}
RESERVACION_COUNTER = 1

# ------------------ FUNCIONES HELPER ------------------

def obtener_viajes() -> List[Dict[str, Any]]:
    """Devuelve el catálogo de viajes."""
    return VIAJES_CATALOGO

def crear_reservacion_mock(user_id: str, viaje_id: int, num_personas: int = 1) -> Dict[str, Any]:
    """Crea una reservación simulada en memoria."""
    global RESERVACION_COUNTER
    
    # Buscar el viaje
    viaje = next((v for v in VIAJES_CATALOGO if v["id"] == viaje_id), None)
    if not viaje:
        return {"success": False, "error": "El viaje no existe"}
    
    if viaje["cupos_disponibles"] < num_personas:
        return {"success": False, "error": f"Solo hay {viaje['cupos_disponibles']} cupos disponibles"}
    
    # Crear reservación
    reservacion_id = RESERVACION_COUNTER
    RESERVACION_COUNTER += 1
    
    reservacion = {
        "id": reservacion_id,
        "usuario_id": user_id,
        "viaje": viaje,
        "num_personas": num_personas,
        "total": viaje["precio"] * num_personas,
        "estado": "confirmada"
    }
    
    if user_id not in RESERVACIONES:
        RESERVACIONES[user_id] = []
    RESERVACIONES[user_id].append(reservacion)
    
    return {
        "success": True,
        "reservacion_id": reservacion_id,
        "destino": viaje["destino"],
        "num_personas": num_personas,
        "total": reservacion["total"]
    }

def obtener_reservaciones(user_id: str) -> List[Dict[str, Any]]:
    """Obtiene las reservaciones de un usuario."""
    return RESERVACIONES.get(user_id, [])

# ------------------ NODO DEL AGENTE ------------------

def chatbot(state: MessagesState):
    """Nodo principal del chatbot que responde con contexto y memoria."""
    # Sistema de prompts con contexto de viajes
    system_message = SystemMessage(content="""
    Eres Galleta 🍪, un asistente virtual simpático, servicial y conversacional.
    
    IMPORTANTE: Puedes hablar de CUALQUIER tema, no solo de viajes. Si el usuario quiere charlar,
    hacer preguntas generales, o hablar de otros temas, respóndele de forma natural y amigable.
    
    Cuando se trate de viajes, tienes acceso a un catálogo de viajes y puedes:
    - Mostrar los viajes disponibles
    - Ayudar a hacer reservaciones (simuladas, sin persistencia real)
    - Consultar reservaciones del usuario
    - Dar información sobre destinos
    
    Catálogo de viajes disponibles:
    """ + "\n".join([f"- {v['destino']}: ${v['precio']} ({v['fecha_salida']} - {v['fecha_regreso']}) - {v['cupos_disponibles']} cupos" 
                       for v in VIAJES_CATALOGO]) + """
    
    Características:
    - Sé amigable, cálido y cercano
    - Usa emojis cuando sea apropiado
    - Recuerda el contexto de la conversación
    - Si no sabes algo, adí telo honestamente
    - Ayuda con cualquier consulta, no solo viajes
    - Mantén un tono conversacional natural
    """)
    
    # Mantener historial limitado para no exceder tokens
    messages = [system_message] + state["messages"]
    
    # Invocar el modelo
    response = llm.invoke(messages)
    
    return {"messages": [response]}

# ------------------ GRAFO ------------------

builder = StateGraph(MessagesState)
builder.add_node("chatbot", chatbot)
builder.add_edge(START, "chatbot")
builder.add_edge("chatbot", END)

# Compilar el grafo
# Nota: LangGraph Studio maneja la persistencia automáticamente,
# por lo que NO usamos checkpointer aquí para compatibilidad.
# Para uso local con memoria, ver test_galleta.py que usa MemorySaver
agent = builder.compile()
agent.name = "Galleta"

