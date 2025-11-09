from langchain.agents import create_agent
from dotenv import load_dotenv

load_dotenv()

def get_weather(city: str) -> str:
    """Obtiene el clima de una ciudad dada."""
    return f"¡Siempre hace sol en {city}!"

# Creamos el agente con identidad propia
agent = create_agent(
    model="groq:llama-3.1-8b-instant",
    tools=[get_weather],
    system_prompt=(
        "Tu nombre es Galleta 🍪. "
        "Eres un asistente virtual simpático y servicial. "
        "Preséntate como Galleta cuando alguien te salude o te pregunte tu nombre. "
        "Responde siempre de forma clara, útil y amable."
    ),
)
agent.name = "Galleta"

