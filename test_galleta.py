"""
Script de prueba para el agente Galleta con memoria conversacional
"""
from src.main import builder
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

# Compilar el agente con memoria para uso local
memory = MemorySaver()
agent = builder.compile(checkpointer=memory)

def chat_with_galleta():
    """
    Inicia una conversación interactiva con Galleta.
    La memoria se mantiene durante toda la sesión.
    """
    print("\n" + "="*60)
    print("🍪 CHAT CON GALLETA 🍪")
    print("="*60)
    print("Escribe 'salir' o 'exit' para terminar la conversación\n")
    
    # Configuración de thread para mantener memoria
    config = {"configurable": {"thread_id": "test_conversation_1"}}
    
    while True:
        try:
            # Obtener mensaje del usuario
            user_input = input("👤 Tú: ")
            
            # Salir si el usuario lo indica
            if user_input.lower() in ['salir', 'exit', 'quit', 'adiós', 'adios']:
                print("\n👋 ¡Hasta luego!\n")
                break
            
            if not user_input.strip():
                continue
            
            # Invocar al agente con memoria
            result = agent.invoke(
                {"messages": [HumanMessage(content=user_input)]},
                config=config
            )
            
            # Mostrar respuesta
            response = result["messages"][-1].content
            print(f"\n🍪 Galleta: {response}\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 ¡Hasta luego!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")

def run_automated_tests():
    """
    Ejecuta pruebas automatizadas demostrando memoria conversacional
    """
    print("\n🧪 INICIANDO PRUEBAS AUTOMATIZADAS 🍪\n")
    
    # Configuración de thread para mantener memoria
    config = {"configurable": {"thread_id": "test_session_1"}}
    
    test_messages = [
        "Hola, mi nombre es Carlos",
        "¿Qué viajes tienes disponibles?",
        "Cuéntame más sobre el viaje a París",
        "¿Cuál es mi nombre?",  # Test de memoria
        "¿Qué opinas del cambio climático?",  # Test de tema no relacionado
        "Volviendo a los viajes, ¿cuál es el más barato?",
        "¿Cuánto cuesta el viaje a Tokyo?",
        "Gracias por tu ayuda"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n[Test {i}/{len(test_messages)}]")
        print(f"👤 Usuario: {message}")
        print("-" * 60)
        
        try:
            result = agent.invoke(
                {"messages": [HumanMessage(content=message)]},
                config=config
            )
            response = result["messages"][-1].content
            print(f"🍪 Galleta: {response}")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    print("\n" + "="*60)
    print("✅ PRUEBAS COMPLETADAS")
    print("="*60 + "\n")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Ejecutar pruebas automatizadas
        run_automated_tests()
    else:
        # Ejecutar chat interactivo
        chat_with_galleta()
