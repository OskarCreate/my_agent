from typing import List, Literal, Optional
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Importa el agente "Galleta" definido en src/main.py
from src.main import (
    agent,
    obtener_viajes,
    recargar_viajes_catalogo,
    set_viajes_source,
    set_viajes_catalogo,
)

# --------- Modelos de request/response ---------
class ChatTurn(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str

class ChatRequest(BaseModel):
    message: str
    user_role: Literal["usuario", "cliente", "empleado", "administrador"] = "usuario"
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    history: Optional[List[ChatTurn]] = None  # opcional cuando se usa memoria
    thread_id: Optional[str] = None  # identifica la conversación para memoria

class ChatResponse(BaseModel):
    reply: str

class SetSourceRequest(BaseModel):
    api_url: Optional[str] = None
    json_path: Optional[str] = None

class SetCatalogRequest(BaseModel):
    items: List[dict]

# --------- Utilidades ---------
def to_lc_messages(turns: List[ChatTurn]):
    out = []
    for t in turns or []:
        if t.role == "user":
            out.append(HumanMessage(content=t.content))
        elif t.role == "assistant":
            out.append(AIMessage(content=t.content))
        else:
            out.append(SystemMessage(content=t.content))
    return out

# --------- App FastAPI ---------
app = FastAPI(title="Galleta API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Al iniciar el servidor, fija la fuente al propio endpoint para autoalimentarse
@app.on_event("startup")
def _autoconfigure_source():
    try:
        set_viajes_source(api_url="http://127.0.0.1:8000/api/viajes")
    except Exception:
        # No bloquear el arranque si falla
        pass

@app.get("/")
def read_root():
    return {"status": "ok"}

# Obtener catálogo actual (útil para depurar y mostrar en tu web)
@app.get("/viajes")
def get_viajes():
    return {"viajes": obtener_viajes()}

# Endpoint compatible con el cargador del agente (array o {items: [...]})
@app.get("/api/viajes")
def api_viajes():
    return obtener_viajes()

# Forzar recarga del catálogo desde la fuente configurada (JSON o API)
@app.post("/admin/reload_catalog")
def admin_reload_catalog():
    total = recargar_viajes_catalogo()
    return {"ok": True, "total": total}

# Definir la fuente (api_url/json_path) en caliente y recargar
@app.post("/admin/set_source")
def admin_set_source(req: SetSourceRequest):
    used = set_viajes_source(json_path=req.json_path, api_url=req.api_url)
    return {"ok": True, "used": used, "total": len(obtener_viajes())}

# Establecer el catálogo completo directamente (array de viajes)
@app.post("/admin/set_catalog")
def admin_set_catalog(req: SetCatalogRequest):
    total = set_viajes_catalogo(req.items)
    return {"ok": True, "total": total}

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    # Construye historial y estado para el agente
    history = to_lc_messages(req.history or [])
    state = {
        "messages": history + [HumanMessage(content=req.message)],
        "user_role": req.user_role,
        "user_id": req.user_id,
        "user_name": req.user_name,
    }
    # Determinar thread_id (si no viene, usa user_id o 'default')
    thread_id = req.thread_id or (str(req.user_id) if req.user_id is not None else "default")
    # Invocar con memoria por hilo
    result = agent.invoke(state, config={"configurable": {"thread_id": thread_id}})
    ai_msg = result.get("messages", [])[-1].content if result.get("messages") else ""
    return ChatResponse(reply=ai_msg)
