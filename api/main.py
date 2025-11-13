from typing import List, Literal, Optional
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Importa el agente "Galleta" definido en src/main.py
from src.main import agent

# --------- Modelos de request/response ---------
class ChatTurn(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str

class ChatRequest(BaseModel):
    message: str
    user_role: Literal["usuario", "cliente", "empleado", "administrador"] = "usuario"
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    history: Optional[List[ChatTurn]] = None

class ChatResponse(BaseModel):
    reply: str

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

@app.get("/")
def read_root():
    return {"status": "ok"}

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
    result = agent.invoke(state)
    ai_msg = result.get("messages", [])[-1].content if result.get("messages") else ""
    return ChatResponse(reply=ai_msg)
