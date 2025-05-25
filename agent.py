import os
import pandas as pd
import logging
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langgraph.prebuilt import create_agent_executor
from langchain_core.messages import SystemMessage

# Configuración de Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuración OpenAI (Asegúrate que OPENAI_API_KEY está en las variables de entorno) ---
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("La variable de entorno OPENAI_API_KEY no está configurada.")

# --- Herramienta de Excel ---
@tool
def query_excel(question: str, file_path: str = "datos.xlsx") -> str:
    """
    Responde preguntas específicas sobre un archivo Excel llamado 'datos.xlsx'.
    Úsala cuando la pregunta se refiera a datos tabulares, filas, columnas,
    cálculos o información contenida en el archivo Excel.
    Por ejemplo: '¿Cuántas filas hay en el excel?', '¿Cuáles son las columnas?',
    '¿Cuál es el valor promedio de la columna X?'.
    """
    logger.info(f"Usando herramienta Excel para: {question}")
    try:
        df = pd.read_excel(file_path)

        # Lógica mejorada (ejemplo usando un LLM para interpretar o pandas directo):
        # Aquí puedes implementar una lógica más sofisticada.
        # Por ahora, usamos ejemplos simples:
        q_lower = question.lower()
        if "cuántas filas" in q_lower or "numero de filas" in q_lower:
            return f"El archivo Excel '{file_path}' tiene {len(df)} filas."
        elif "columnas" in q_lower:
            return f"Las columnas en '{file_path}' son: {', '.join(df.columns.tolist())}."
        elif "mostrar datos" in q_lower or "primeras filas" in q_lower:
            return f"Las primeras 5 filas son:\n{df.head().to_string()}"
        else:
            # Podrías intentar usar un LLM para generar código Pandas o dar una respuesta genérica.
            return f"No pude interpretar tu pregunta específica sobre el Excel con las reglas actuales. El archivo tiene las columnas: {df.columns.tolist()}"

    except FileNotFoundError:
        logger.error(f"Archivo no encontrado: {file_path}")
        return f"Error: El archivo '{file_path}' no fue encontrado. Asegúrate de que exista."
    except Exception as e:
        logger.error(f"Error procesando Excel: {e}")
        return f"Ocurrió un error al procesar el archivo Excel: {e}"

# --- Creación del Agente LangGraph ---
def get_agent():
    """Crea y configura el agente LangGraph."""
    logger.info("Creando el agente LangGraph...")
    llm = ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=api_key)
    tools = [query_excel]

    # Añadimos un mensaje de sistema para guiar al LLM
    system_prompt = SystemMessage(
        content="""Eres un asistente conversacional útil.
        Puedes chatear normalmente.
        Tienes una herramienta para consultar un archivo Excel llamado 'datos.xlsx'.
        Si la pregunta del usuario parece referirse a datos tabulares, filas, columnas,
        o información que podría estar en un Excel, usa la herramienta 'query_excel'.
        De lo contrario, responde como un asistente normal.
        Sé claro y conciso en tus respuestas."""
    )

    # Creamos el agente executor, pasando el mensaje de sistema.
    # Usamos 'messages' como clave de entrada/salida.
    agent_executor = create_agent_executor(
        llm,
        tools,
        system_message=system_prompt,
        input_keys=["messages"], # Especificamos que la entrada es una lista de mensajes
        output_keys=["messages"] # Y la salida también
    )
    logger.info("Agente LangGraph creado exitosamente.")
    return agent_executor

# Si quieres probar el agente localmente:
# if __name__ == "__main__":
#     agent = get_agent()
#     from langchain_core.messages import HumanMessage
#     response = agent.invoke({"messages": [HumanMessage(content="Hola, ¿cómo estás?")]})
#     print(response)
#     response = agent.invoke({"messages": [HumanMessage(content="¿Cuántas filas hay en el excel?")]})
#     print(response)