from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, BaseMessage, trim_messages
from langchain.chat_models import init_chat_model
from typing import Literal, TypedDict, List, Dict, Any, Annotated, Optional
import os
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

# Modelo LLM
llm = init_chat_model("llama-3.1-8b-instant", model_provider="groq", temperature=0.7)

# Catálogo de viajes (dinámico). Puedes alimentarlo desde tu página.
# Opciones de fuente (por variables de entorno):
# - VIAJES_JSON_PATH: ruta a un JSON local con la lista de viajes
# - VIAJES_API_URL: URL HTTP que devuelve JSON con la lista de viajes
# Si no se proporcionan, se usa un catálogo de ejemplo.
import json
from pathlib import Path

try:
    import requests  # para cargar desde API si se configura VIAJES_API_URL
except Exception:
    requests = None

# Overrides configurables en tiempo de ejecución (vía API)
OVERRIDE_JSON_PATH: Optional[str] = None
OVERRIDE_API_URL: Optional[str] = None

# URL por defecto (tu web local)
DEFAULT_VIAJES_API_URL = "http://localhost:3000/api/viajes"

# Rutas locales candidatas para data en el repo (se usa la primera que exista)
LOCAL_JSON_CANDIDATES = [
    Path(__file__).resolve().with_name("viajes.json"),
    Path(__file__).resolve().parents[1] / "data" / "viajes.json",
]

DEFAULT_VIAJES = [
    {
        "id": 1,
        "destino": "Cusco - Machu Picchu, Perú",
        "descripcion": "City tour + Valle Sagrado + Machu Picchu.",
        "precio": 750.00,
        "fecha_salida": "",
        "fecha_regreso": "",
        "cupos_disponibles": 20,
    },
    {
        "id": 2,
        "destino": "Arequipa, Perú",
        "descripcion": "Ciudad Blanca y Cañón del Colca.",
        "precio": 320.00,
        "fecha_salida": "",
        "fecha_regreso": "",
        "cupos_disponibles": 18,
    },
    {
        "id": 3,
        "destino": "Iquitos (Amazonas), Perú",
        "descripcion": "Selva amazónica y lodge ecológico.",
        "precio": 450.00,
        "fecha_salida": "",
        "fecha_regreso": "",
        "cupos_disponibles": 15,
    },
    {
        "id": 4,
        "destino": "Puno - Lago Titicaca, Perú",
        "descripcion": "Islas Uros y Taquile.",
        "precio": 280.00,
        "fecha_salida": "",
        "fecha_regreso": "",
        "cupos_disponibles": 25,
    },
]

def _normalize_viaje(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza claves comunes provenientes de tu página/API al formato interno.
    Ajusta aquí si tus nombres de campo difieren.
    """
    def pick(*keys, default=None):
        for k in keys:
            if k in item and item[k] not in (None, ""):
                return item[k]
        return default

    return {
        "id": pick("id", "ID", "codigo", default=None),
        "destino": pick("destino", "nombre", "titulo", "title", default=""),
        "descripcion": pick("descripcion", "descripcion_corta", "descripcion_larga", "description", default=""),
        "precio": float(pick("precio", "precio_soles", "price", default=0) or 0),
        "fecha_salida": pick("fecha_salida", "salida", "desde", "start_date", default=""),
        "fecha_regreso": pick("fecha_regreso", "regreso", "hasta", "end_date", default=""),
        "cupos_disponibles": int(pick("cupos_disponibles", "cupos", "stock", "seats", default=0) or 0),
    }

def _load_from_json(path: str) -> List[Dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "items" in data:
        data = data["items"]
    return [_normalize_viaje(d) for d in data]

def _load_from_api(url: str) -> List[Dict[str, Any]]:
    if not requests:
        return []
    try:
        r = requests.get(url, timeout=4)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and "items" in data:
            data = data["items"]
        return [_normalize_viaje(d) for d in data]
    except Exception:
        return []

def _load_viajes_catalogo() -> List[Dict[str, Any]]:
    # 1) Overrides establecidos en tiempo de ejecución
    if OVERRIDE_JSON_PATH:
        items = _load_from_json(OVERRIDE_JSON_PATH)
        if items:
            return items
    if OVERRIDE_API_URL:
        items = _load_from_api(OVERRIDE_API_URL)
        if items:
            return items

    # 2) Variables de entorno
    json_path = os.getenv("VIAJES_JSON_PATH")
    api_url = os.getenv("VIAJES_API_URL")
    if json_path:
        items = _load_from_json(json_path)
        if items:
            return items
    if api_url:
        items = _load_from_api(api_url)
        if items:
            return items

    # 3) Archivo local del repo (data/viajes.json o src/viajes.json)
    for candidate in LOCAL_JSON_CANDIDATES:
        try:
            items = _load_from_json(str(candidate))
            if items:
                return items
        except Exception:
            pass

    # 4) URL por defecto de tu web local (si está corriendo)
    items = _load_from_api(DEFAULT_VIAJES_API_URL)
    if items:
        return items

    # 5) Fallback de ejemplo
    return DEFAULT_VIAJES

VIAJES_CATALOGO = _load_viajes_catalogo()

# Almacenamiento temporal de reservaciones (en memoria)
RESERVACIONES = {}
RESERVACION_COUNTER = 1

# ------------------ FUNCIONES HELPER ------------------

def obtener_viajes() -> List[Dict[str, Any]]:
    """Devuelve el catálogo de viajes."""
    return VIAJES_CATALOGO

def recargar_viajes_catalogo() -> int:
    """Recarga el catálogo desde la fuente configurada. Retorna el total de viajes."""
    global VIAJES_CATALOGO
    VIAJES_CATALOGO = _load_viajes_catalogo()
    return len(VIAJES_CATALOGO)

def set_viajes_source(*, json_path: Optional[str] = None, api_url: Optional[str] = None) -> Dict[str, Optional[str]]:
    """Define la fuente del catálogo en tiempo de ejecución y recarga."""
    global OVERRIDE_JSON_PATH, OVERRIDE_API_URL
    OVERRIDE_JSON_PATH = json_path or None
    OVERRIDE_API_URL = api_url or None
    recargar_viajes_catalogo()
    return {"json_path": OVERRIDE_JSON_PATH, "api_url": OVERRIDE_API_URL}

def set_viajes_catalogo(items: List[Dict[str, Any]]) -> int:
    """Sobrescribe el catálogo actual con items ya normalizados o crudos."""
    global VIAJES_CATALOGO
    VIAJES_CATALOGO = [_normalize_viaje(it) for it in (items or [])]
    return len(VIAJES_CATALOGO)

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
    - Si no sabes algo, dilo honestamente
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

# Compilar el grafo con memoria persistente por hilo (thread_id)
checkpointer = MemorySaver()
agent = builder.compile(checkpointer=checkpointer)
agent.name = "Galleta"

