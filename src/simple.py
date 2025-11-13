from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, BaseMessage
from langchain.chat_models import init_chat_model
from typing import Literal, TypedDict, List, Dict, Any, Tuple, Optional
import psycopg2
from psycopg2 import sql
import os
import re
import json
from dotenv import load_dotenv
from functools import lru_cache

load_dotenv()

# Mapear GENAI_API_KEY -> GOOGLE_API_KEY si es necesario
if os.getenv("GENAI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GENAI_API_KEY")

# Modelos: Groq como orquestador, Gemini como razonador
# Groq (planner / finalizer)
llm_groq = init_chat_model("llama-3.1-8b-instant", model_provider="groq", temperature=0.2)
# Gemini (reasoning)
llm_gemini = init_chat_model("models/gemini-2.5-flash", model_provider="google_genai", temperature=0.2)

# Configuración de la base de datos por variables de entorno o cadena .NET
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "sslmode": os.getenv("DB_SSLMODE", "require"),
}

DOTNET_CONNSTR = os.getenv("DB_CONNECTION_STRING") or os.getenv("DOTNET_DEFAULT_CONNECTION")


# Definición del estado para LangGraph
class MessagesState(TypedDict):
    messages: List[BaseMessage]

class State(MessagesState, total=False):
    user_role: Literal["usuario", "cliente", "empleado", "administrador"]
    user_id: int
    access_granted: bool

def _parse_dotnet_pg_connstr(conn: str) -> Dict[str, Any]:
    """Convierte una connection string estilo .NET (con ;) a kwargs de psycopg2."""
    parts = [p.strip() for p in conn.strip().split(";") if p.strip()]
    kv = {}
    for p in parts:
        if "=" not in p:
            continue
        k, v = p.split("=", 1)
        kv[k.strip().lower()] = v.strip()
    host = kv.get("host") or kv.get("server")
    database = kv.get("database") or kv.get("dbname")
    user = kv.get("username") or kv.get("user id") or kv.get("user")
    password = kv.get("password")
    port = int(kv.get("port", "5432"))
    sslmode = (kv.get("ssl mode") or kv.get("sslmode") or "require").lower()
    # Trust Server Certificate=true -> mantener sslmode=require; psycopg2 no soporta "trust" explícito
    return {
        "host": host,
        "database": database,
        "user": user,
        "password": password,
        "port": port,
        "sslmode": sslmode,
    }

@lru_cache(maxsize=1)
def _effective_db_config() -> Dict[str, Any]:
    if DOTNET_CONNSTR:
        return _parse_dotnet_pg_connstr(DOTNET_CONNSTR)
    return DB_CONFIG

def get_db_connection():
    """Establece conexión con la base de datos PostgreSQL"""
    cfg = _effective_db_config()
    missing = [k for k, v in cfg.items() if v in (None, "")]
    if missing:
        raise RuntimeError(f"Variables/campos faltantes para DB: {', '.join(missing)}")
    return psycopg2.connect(**cfg)

def execute_query(query: str, params: tuple = None) -> List[tuple]:
    """Ejecuta una consulta SQL y retorna las filas."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            if cur.description:
                return cur.fetchall()
            return []
    finally:
        if conn:
            conn.close()

def get_table_list(include_system: bool = False) -> List[tuple]:
    """Obtiene lista de tablas (schema, table_name)."""
    if include_system:
        query = (
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_type='BASE TABLE' ORDER BY table_schema, table_name"
        )
    else:
        query = (
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_type='BASE TABLE' AND table_schema NOT IN ('pg_catalog','information_schema') "
            "ORDER BY table_schema, table_name"
        )
    return execute_query(query)

def get_table_count(include_system: bool = False) -> int:
    """Cuenta tablas totales."""
    if include_system:
        query = (
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_type='BASE TABLE'"
        )
    else:
        query = (
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_type='BASE TABLE' AND table_schema NOT IN ('pg_catalog','information_schema')"
        )
    rows = execute_query(query)
    return int(rows[0][0]) if rows else 0

def get_last_user_message(state: State) -> str:
    msgs = state.get("messages", [])
    for m in reversed(msgs):
        if isinstance(m, HumanMessage):
            return str(m.content)
    return ""

def detect_db_intent(text: str) -> Optional[str]:
    """Detecta intención relacionada a BD.
    Retorna uno de: 'count', 'list', 'columns', 'rowcount', 'sample', 'overview', o None.
    """
    t = (text or "").lower()
    ask_total = ["cuantas tablas", "cuántas tablas", "numero de tablas", "número de tablas", "total de tablas", "how many tables", "count tables"]
    ask_list = ["lista de tablas", "listar tablas", "muestrame las tablas", "muéstrame las tablas", "show tables", "list tables"]
    if any(k in t for k in ask_total):
        return "count"
    if any(k in t for k in ask_list) or ("tablas" in t and "columnas" not in t):
        return "list"
    if any(k in t for k in ["columnas", "campos", "estructura", "schema de", "describe", "describir"]):
        return "columns"
    if any(k in t for k in ["cuantas filas", "cuántas filas", "numero de filas", "número de filas", "registros totales", "row count", "count rows"]):
        return "rowcount"
    if any(k in t for k in ["muestra filas", "muestrame filas", "primeros", "primeras", "sample", "mostrar filas", "ver filas"]):
        return "sample"
    # visión general
    if any(k in t for k in ["toda la base de datos", "toda su información", "estructura completa", "overview", "esquema completo", "todas las tablas y columnas", "diagrama"]):
        return "overview"
    return None

def extract_table_mention(text: str) -> Optional[str]:
    """Extrae posible mención de tabla (opcionalmente con esquema)."""
    if not text:
        return None
    m = re.search(r"(?:tabla|table|de)\s+([A-Za-z_][\w\.\"]*)", text, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip().strip('"')
    m2 = re.search(r"([A-Za-z_][\w]*)\.([A-Za-z_][\w]*)", text)
    if m2:
        return f"{m2.group(1)}.{m2.group(2)}"
    return None


def resolve_table_identifier(raw_name: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Resuelve nombre de tabla a (schema, table). Devuelve (schema, table, error)."""
    if not raw_name:
        return None, None, None
    raw = raw_name.strip()
    parts = raw.split(".")
    if len(parts) == 2:
        schema, table = parts[0], parts[1]
        rows = execute_query(
            """
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_type='BASE TABLE'
              AND table_schema NOT IN ('pg_catalog','information_schema')
              AND table_schema=%s AND table_name=%s
            """,
            (schema, table),
        )
        if rows:
            return rows[0][0], rows[0][1], None
        return None, None, f"La tabla {raw} no existe."
    else:
        table = raw
        rows = execute_query(
            """
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_type='BASE TABLE'
              AND table_schema NOT IN ('pg_catalog','information_schema')
              AND table_name=%s
            """,
            (table,),
        )
        if not rows:
            return None, None, f"La tabla {table} no existe."
        if len(rows) > 1:
            schemas = ", ".join(sorted({r[0] for r in rows}))
            return None, None, f"La tabla {table} existe en múltiples esquemas: {schemas}. Especifica el esquema."
        return rows[0][0], rows[0][1], None


def get_columns(schema: str, table: str) -> List[tuple]:
    return execute_query(
        """
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema=%s AND table_name=%s
        ORDER BY ordinal_position
        """,
        (schema, table),
    )


def get_row_count_for_table(schema: str, table: str) -> int:
    query = sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
        sql.Identifier(schema), sql.Identifier(table)
    )
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(query)
            return int(cur.fetchone()[0])
    finally:
        if conn:
            conn.close()


def get_sample_rows(schema: str, table: str, limit: int = 5) -> List[tuple]:
    if limit <= 0 or limit > 100:
        limit = 5
    query = sql.SQL("SELECT * FROM {}.{} LIMIT {}").format(
        sql.Identifier(schema), sql.Identifier(table), sql.Literal(limit)
    )
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            headers = [desc[0] for desc in cur.description]
            return [tuple(headers)] + rows
    finally:
        if conn:
            conn.close()


def get_primary_key(schema: str, table: str) -> List[str]:
    rows = execute_query(
        """
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        WHERE tc.table_schema=%s AND tc.table_name=%s AND tc.constraint_type='PRIMARY KEY'
        ORDER BY kcu.ordinal_position
        """,
        (schema, table),
    )
    return [r[0] for r in rows]


def get_foreign_keys(schema: str, table: str) -> List[Dict[str, Any]]:
    rows = execute_query(
        """
        SELECT
          tc.constraint_name,
          kcu.column_name,
          ccu.table_schema AS foreign_table_schema,
          ccu.table_name AS foreign_table_name,
          ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
         AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = %s AND tc.table_name = %s
        ORDER BY tc.constraint_name, kcu.ordinal_position
        """,
        (schema, table),
    )
    fks: Dict[str, Dict[str, Any]] = {}
    for name, col, rs, rt, rc in rows:
        fks.setdefault(name, {"constraint": name, "columns": [], "ref_schema": rs, "ref_table": rt, "ref_columns": []})
        fks[name]["columns"].append(col)
        fks[name]["ref_columns"].append(rc)
    return list(fks.values())


def get_indexes(schema: str, table: str) -> List[Dict[str, Any]]:
    rows = execute_query(
        """
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE schemaname=%s AND tablename=%s
        ORDER BY indexname
        """,
        (schema, table),
    )
    return [{"name": r[0], "def": r[1]} for r in rows]


def get_db_overview(max_tables: int | None = None) -> str:
    rows = get_table_list()
    if not rows:
        return "No se encontraron tablas (excluyendo schemas del sistema)."
    lines: List[str] = []
    count = 0
    for schema, table in rows:
        if max_tables is not None and count >= max_tables:
            break
        count += 1
        lines.append(f"# {schema}.{table}")
        cols = get_columns(schema, table)
        if cols:
            lines.append("- Columnas:")
            for c, t, n in cols:
                lines.append(f"  - {c}: {t} nullable={n}")
        pk = get_primary_key(schema, table)
        if pk:
            lines.append(f"- PK: {', '.join(pk)}")
        fks = get_foreign_keys(schema, table)
        if fks:
            lines.append("- FKs:")
            for fk in fks:
                cols_s = ", ".join(fk["columns"]) 
                ref_cols_s = ", ".join(fk["ref_columns"]) 
                lines.append(f"  - {fk['constraint']}: ({cols_s}) -> {fk['ref_schema']}.{fk['ref_table']}({ref_cols_s})")
        idx = get_indexes(schema, table)
        if idx:
            lines.append("- Índices:")
            for i in idx:
                lines.append(f"  - {i['name']}: {i['def']}")
        lines.append("")
    return "\n".join(lines)


def check_user_access(state: State):
    """Verifica el rol del usuario y determina sus permisos"""
    new_state: Dict[str, Any] = {}
    
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

# ------------------ NODOS DESGLOSADOS ------------------

# Ampliamos el estado con artefactos intermedios
class State(State, total=False):
    plan: Dict[str, Any]
    db_results: List[Dict[str, Any]]
    reasoned_answer: str


def plan_with_groq(state: State):
    """Groq planifica acciones a partir del último mensaje del usuario y su rol."""
    if not state.get("access_granted", False):
        return {"messages": [AIMessage(content="❌ Acceso denegado. No tienes permisos suficientes.")]} 

    user_role = state.get("user_role")
    user_text = get_last_user_message(state)

    plan_prompt = (
        "Eres un planificador. Dada la petición del usuario y su rol, genera un plan JSON mínimo.\n"
        "Incluye: intent (string), actions (array), clarifications (array).\n"
        "Actions: overview, count_tables, list_tables, columns(table), rowcount(table), sample(table, limit).\n"
        "Si falta la tabla/esquema, agrega una pregunta en clarifications y NO incluyas esa action.\n"
        "Responde SOLO con JSON válido.\n"
        f"Rol: {user_role}\nUsuario: {user_text}"
    )
    plan_msg = llm_groq.invoke([SystemMessage(content="Planificador de acciones"), HumanMessage(content=plan_prompt)])

    try:
        plan: Dict[str, Any] = json.loads(plan_msg.content)
    except Exception:
        intent = detect_db_intent(user_text)
        plan = {"intent": intent or "general", "actions": [], "clarifications": []}
        if intent == "overview":
            plan["actions"].append({"type": "overview"})
        elif intent == "count":
            plan["actions"].append({"type": "count_tables"})
        elif intent == "list":
            plan["actions"].append({"type": "list_tables"})
        elif intent in ("columns", "rowcount", "sample"):
            raw = extract_table_mention(user_text)
            if raw:
                plan["actions"].append({"type": intent, "table": raw, **({"limit": 5} if intent == "sample" else {})})
            else:
                plan["clarifications"].append("¿De qué tabla? Indica 'schema.tabla' o solo 'tabla'.")

    return {"plan": plan}


def should_clarify(state: State) -> Literal["clarify", "exec"]:
    plan = state.get("plan") or {}
    if plan.get("clarifications"):
        return "clarify"
    return "exec"


def ask_for_clarification(state: State):
    plan = state.get("plan") or {}
    question = (plan.get("clarifications") or ["Necesito una aclaración adicional."])[0]
    return {"messages": [AIMessage(content=question)]}


def execute_db_actions(state: State):
    """Ejecuta acciones planificadas en la BD (si el rol lo permite)."""
    plan: Dict[str, Any] = state.get("plan") or {}
    user_role = state.get("user_role")
    user_text = get_last_user_message(state)

    # Restringir acciones globales para roles limitados
    if user_role not in ("empleado", "administrador"):
        if any(a.get("type") in ("count_tables", "list_tables", "overview") for a in plan.get("actions", [])):
            return {"messages": [AIMessage(content="❌ No tienes permisos para consultar metadatos globales de BD.")]}

    db_results: List[Dict[str, Any]] = []
    try:
        for action in plan.get("actions", []):
            a_type = action.get("type")
            if a_type == "overview":
                overview = get_db_overview()
                db_results.append({"action": a_type, "result": overview})
            elif a_type == "count_tables":
                total = get_table_count()
                db_results.append({"action": a_type, "result": total})
            elif a_type == "list_tables":
                rows = get_table_list()
                db_results.append({"action": a_type, "result": [f"{s}.{t}" for s, t in rows]})
            elif a_type in ("columns", "rowcount", "sample"):
                raw = action.get("table") or extract_table_mention(user_text)
                if not raw:
                    db_results.append({"action": a_type, "error": "Tabla no especificada"})
                    continue
                schema, table, err = resolve_table_identifier(raw)
                if err:
                    db_results.append({"action": a_type, "error": err})
                    continue
                if a_type == "columns":
                    cols = get_columns(schema, table)
                    db_results.append({
                        "action": a_type,
                        "table": f"{schema}.{table}",
                        "result": [{"name": c, "type": t, "nullable": n} for c, t, n in cols],
                    })
                elif a_type == "rowcount":
                    cnt = get_row_count_for_table(schema, table)
                    db_results.append({"action": a_type, "table": f"{schema}.{table}", "result": cnt})
                else:  # sample
                    limit = int(action.get("limit") or 5)
                    rows = get_sample_rows(schema, table, limit=limit)
                    if not rows:
                        db_results.append({"action": a_type, "table": f"{schema}.{table}", "result": []})
                    else:
                        headers = rows[0]
                        data = [dict(zip(headers, r)) for r in rows[1:]]
                        db_results.append({"action": a_type, "table": f"{schema}.{table}", "result": data})
    except Exception as e:
        return {"messages": [AIMessage(content=f"Error al consultar la BD: {e}")]}

    return {"db_results": db_results}


def should_reason(state: State) -> Literal["reason", "end"]:
    # Si ya se devolvió un mensaje (p. ej. error/permiso) y no hay resultados, terminamos.
    if state.get("db_results") is None and state.get("messages"):
        return "end"
    return "reason"


def reason_with_gemini(state: State):
    """Gemini razona sobre plan + resultados."""
    plan: Dict[str, Any] = state.get("plan") or {}
    db_results = state.get("db_results") or []
    user_role = state.get("user_role")
    user_text = get_last_user_message(state)

    gemini_msg = llm_gemini.invoke([
        SystemMessage(content="Razonador de consultas de BD"),
        HumanMessage(content=json.dumps({
            "plan": plan,
            "user": user_text,
            "role": user_role,
            "db_results": db_results,
        }, ensure_ascii=False))
    ])
    return {"reasoned_answer": gemini_msg.content}


def finalize_with_groq(state: State):
    """Groq orquesta y entrega la respuesta final (o passthrough de overview)."""
    plan: Dict[str, Any] = state.get("plan") or {}
    db_results = state.get("db_results") or []
    user_role = state.get("user_role")
    user_text = get_last_user_message(state)
    reasoned = state.get("reasoned_answer")

    # Si es overview, devolver tal cual
    if any(r.get("action") == "overview" for r in db_results):
        overview_text = next((r.get("result") for r in db_results if r.get("action") == "overview"), reasoned or "")
        return {"messages": [AIMessage(content=overview_text)]}

    groq_final = llm_groq.invoke([
        SystemMessage(content="Orquestador - respuesta final"),
        HumanMessage(content=json.dumps({
            "user": user_text,
            "role": user_role,
            "plan": plan,
            "db_results": db_results,
            "reasoned_answer": reasoned,
        }, ensure_ascii=False))
    ])
    return {"messages": [AIMessage(content=groq_final.content)]}


# ------------------ GRAFO ------------------
_builder = StateGraph(State)
_builder.add_node("check_access", check_user_access)
_builder.add_node("plan", plan_with_groq)
_builder.add_node("clarify", ask_for_clarification)
_builder.add_node("execute", execute_db_actions)
_builder.add_node("reason", reason_with_gemini)
_builder.add_node("finalize", finalize_with_groq)

_builder.add_edge(START, "check_access")

# Si hay acceso, planificamos; si no, terminamos
def _after_access(state: State) -> Literal["plan", "end"]:
    return "plan" if state.get("access_granted", False) else "end"

_builder.add_conditional_edges(
    "check_access",
    _after_access,
    {"plan": "plan", "end": END},
)

# Si faltan datos, pedimos aclaración y terminamos ciclo; si no, ejecutamos
_builder.add_conditional_edges(
    "plan",
    should_clarify,
    {"clarify": "clarify", "exec": "execute"},
)
_builder.add_edge("clarify", END)

# Tras ejecutar, si no hay resultados por error/permiso, terminamos; si hay, razonamos
_builder.add_conditional_edges(
    "execute",
    should_reason,
    {"reason": "reason", "end": END},
)
_builder.add_edge("reason", "finalize")
_builder.add_edge("finalize", END)

# Objeto esperado por 'langgraph dev'
agent = _builder.compile()
