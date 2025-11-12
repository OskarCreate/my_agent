import os
from fastapi import FastAPI, Header, HTTPException
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Literal, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from src.simple import agent  # tu agente compilado

AGENT_API_KEY = os.getenv("AGENT_API_KEY")

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
    history: Optional[List[ChatTurn]] = None

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

    history = to_lc_messages(req.history)
    state = {
        "messages": history + [HumanMessage(content=req.message)],
        "user_role": req.user_role,
        "user_id": req.user_id,
    }
    result = agent.invoke(state)
    ai_msg = result.get("messages", [])[-1].content if result.get("messages") else ""
    return {"reply": ai_msg}