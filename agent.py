import os
import pandas as pd
import logging
from langchain_openai import ChatOpenAI
from langchain.tools import tool
# CAMBIO: Importamos chat_agent_executor en lugar de create_agent_executor
from langgraph.prebuilt import chat_agent_executor
from langchain_core.messages import SystemMessage

# Configuración de Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuración OpenAI ---
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("La variable de entorno OPENAI_API_KEY no está configurada.")

# --- Herramienta de Excel (Sin cambios) ---
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

        q_lower = question.lower()
        if "cuántas filas" in q_lower or "numero de filas" in q_lower:
            return f"El archivo Excel '{file_path}' tiene {len(df)} filas."
        elif "columnas" in q_lower:
            return f"Las columnas en '{file_path}' son: {', '.join(df.columns.tolist())}."
        elif "mostrar datos" in q_lower or "primeras filas" in q_lower:
            return f"Las primeras 5 filas son:\n{df.head().to_string()}"
        else:
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

    # CAMBIO: Usamos chat_agent_executor.
    # Nota: chat_agent_executor es más simple. Generalmente no se le pasa
    # un SystemMessage directamente ni las keys. La forma de pasar el
    # SystemMessage dependería de cómo chat_agent_executor lo maneje internamente
    # o si se necesita construir el grafo manualmente para más control.
    # Por ahora, confiamos en que el LLM y las descripciones de las tools
    # funcionen bien. Si necesitas un SystemMessage persistente, podrías
    # necesitar un enfoque de StateGraph más detallado.
    agent_executor = chat_agent_executor.create_tool_calling_executor(llm, tools)

    logger.info("Agente LangGraph creado exitosamente.")
    return agent_executor