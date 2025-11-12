from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain.chat_models import init_chat_model
from typing import Literal
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

llm = init_chat_model("groq:llama-3.1-8b-instant", temperature=0.7)

# Configuración de la base de datos
DB_CONFIG = {
    "host": "dpg-d3ustbjipnbc7396v3mg-a.oregon-postgres.render.com",
    "database": "base_de_datos_de_prueba_5kny",
    "user": "base_de_datos_de_prueba_5kny_user",
    "password": "tHDeT28SHA7QAniXKpMlEeKLfqjABGXv",
    "port": 5432,
    "sslmode": "require"
}

# Definición del estado
class State(MessagesState):
    user_role: Literal["usuario", "cliente", "empleado", "administrador"]
    user_id: int
    access_granted: bool

def get_db_connection():
    """Establece conexión con la base de datos PostgreSQL"""
    return psycopg2.connect(**DB_CONFIG)

def check_user_access(state: State):
    """Verifica el rol del usuario y determina sus permisos"""
    new_state = {}
    
    user_role = state.get("user_role", "usuario")
    user_id = state.get("user_id")
    
    # Empleados y administradores tienen acceso completo
    if user_role in ["empleado", "administrador"]:
        new_state["access_granted"] = True
        system_msg = SystemMessage(content=(
            f"Eres un asistente con rol de {user_role}. "
            "Tienes acceso completo a toda la información de la base de datos. "
            "Puedes consultar y modificar cualquier registro."
        ))
    # Usuarios y clientes solo acceden a su propia información
    elif user_role in ["usuario", "cliente"]:
        if user_id:
            new_state["access_granted"] = True
            system_msg = SystemMessage(content=(
                f"Eres un asistente con rol de {user_role}. "
                f"Solo puedes acceder a la información del usuario con ID {user_id}. "
                "No puedes consultar ni modificar información de otros usuarios."
            ))
        else:
            new_state["access_granted"] = False
            system_msg = SystemMessage(content=(
                "Acceso denegado. No se proporcionó un ID de usuario válido."
            ))
    else:
        new_state["access_granted"] = False
        system_msg = SystemMessage(content="Rol de usuario no reconocido.")
    
    # Agregar mensaje del sistema al historial
    messages = [system_msg] + state.get("messages", [])
    new_state["messages"] = messages
    
    return new_state

def process_query(state: State):
    """Procesa la consulta del usuario con LLM"""
    new_state = {}
    
    if not state.get("access_granted", False):
        # Si no hay acceso, responder con mensaje de error
        error_msg = AIMessage(content="❌ Acceso denegado. No tienes permisos suficientes.")
        new_state["messages"] = [error_msg]
        return new_state
    
    # Obtener el historial de mensajes
    history = state.get("messages", [])
    user_role = state.get("user_role")
    user_id = state.get("user_id")
    
    # Agregar contexto adicional para el LLM
    context_msg = SystemMessage(content=(
        f"Información de contexto:\n"
        f"- Rol del usuario: {user_role}\n"
        f"- ID del usuario: {user_id if user_id else 'N/A'}\n"
        f"- Base de datos: PostgreSQL en Render\n"
        f"\n"
        f"Reglas de acceso:\n"
        f"- Empleados/Administradores: Acceso completo a todos los datos\n"
        f"- Usuarios/Clientes: Solo pueden ver y modificar su propia información\n"
        f"\n"
        f"Responde de manera clara y útil según los permisos del usuario."
    ))
    
    full_history = [context_msg] + history
    
    # Invocar el LLM
    ai_message = llm.invoke(full_history)
    new_state["messages"] = [ai_message]
    
    return new_state

def should_continue(state: State) -> Literal["process", "end"]:
    """Decide si procesar la consulta o terminar"""
    if state.get("access_granted", False):
        return "process"
    return "end"

# Construcción del grafo
builder = StateGraph(State)

# Agregar nodos
builder.add_node("check_access", check_user_access)
builder.add_node("process_query", process_query)

# Definir flujo
builder.add_edge(START, "check_access")
builder.add_conditional_edges(
    "check_access",
    should_continue,
    {
        "process": "process_query",
        "end": END
    }
)
builder.add_edge("process_query", END)

agent = builder.compile()
