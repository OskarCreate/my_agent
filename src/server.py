import os
import json
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Literal, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from src.simple import agent  # tu agente compilado

AGENT_API_KEY = os.getenv("AGENT_API_KEY")

# Carpeta para persistencia simple (historial y perfiles)
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = (BASE_DIR / ".." / "data").resolve()
HISTORY_DIR = DATA_DIR / "history"
PROFILE_DIR = DATA_DIR / "profiles"
for d in (HISTORY_DIR, PROFILE_DIR):
    d.mkdir(parents=True, exist_ok=True)

app = FastAPI()
# En dev no es necesario CORS si llamas vía proxy .NET (mismo origen).
# Si vas a llamar directo desde el browser, ajusta allow_origins con tu dominio.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

class ChatTurn(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str

class ChatRequest(BaseModel):
    message: str
    user_role: Literal["usuario", "cliente", "empleado", "administrador"] = "usuario"
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    history: Optional[List[ChatTurn]] = None

def _history_path(user_id: int) -> Path:
    return HISTORY_DIR / f"{user_id}.json"

def _profile_path(user_id: int) -> Path:
    return PROFILE_DIR / f"{user_id}.json"

def load_history(user_id: Optional[int]) -> List[ChatTurn]:
    if not user_id:
        return []
    p = _history_path(int(user_id))
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return [ChatTurn(**t) for t in data]
    except Exception:
        return []

def save_history(user_id: Optional[int], turns: List[ChatTurn]) -> None:
    if not user_id:
        return
    # Limitar tamaño del historial para evitar crecimiento infinito
    trimmed = turns[-50:]
    _history_path(int(user_id)).write_text(
        json.dumps([t.model_dump() for t in trimmed], ensure_ascii=False, indent=0),
        encoding="utf-8",
    )

def load_profile(user_id: Optional[int]) -> dict:
    if not user_id:
        return {}
    p = _profile_path(int(user_id))
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_profile(user_id: Optional[int], profile: dict) -> None:
    if not user_id:
        return
    _profile_path(int(user_id)).write_text(
        json.dumps(profile, ensure_ascii=False, indent=0), encoding="utf-8"
    )

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

@app.post("/api/chat")
def chat(req: ChatRequest, authorization: Optional[str] = Header(None)):
    # Protección simple por token (opcional pero recomendable)
    if AGENT_API_KEY:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Unauthorized")
        token = authorization.split(" ", 1)[1]
        if token != AGENT_API_KEY:
            raise HTTPException(status_code=403, detail="Forbidden")

    # Cargar historial persistido (si hay user_id)
    persisted: List[ChatTurn] = load_history(req.user_id)
    profile = load_profile(req.user_id)

    # Actualizar nombre en el perfil si se envía uno nuevo
    if req.user_name:
        profile["name"] = req.user_name
        save_profile(req.user_id, profile)

    # Elegir la fuente de historial: prioriza persistido si existe
    base_history = persisted if persisted else (req.history or [])

    # Agregar una instrucción de sistema con el nombre recordado, si está
    sys_msgs: List[ChatTurn] = []
    if profile.get("name"):
        sys_msgs.append(ChatTurn(role="system", content=f"El usuario se llama {profile['name']}. Dirígete a él por su nombre cuando sea natural."))

    # Construir historial LC + mensaje actual
    history = to_lc_messages(sys_msgs + base_history)
    state = {
        "messages": history + [HumanMessage(content=req.message)],
        "user_role": req.user_role,
        "user_id": req.user_id,
        "user_name": profile.get("name"),
    }
    result = agent.invoke(state)
    ai_msg = result.get("messages", [])[-1].content if result.get("messages") else ""

    # Persistir historial si hay user_id
    if req.user_id:
        new_history = base_history + [ChatTurn(role="user", content=req.message), ChatTurn(role="assistant", content=ai_msg)]
        save_history(req.user_id, new_history)

    return {"reply": ai_msg, "remembered_name": profile.get("name")}
