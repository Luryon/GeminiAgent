import os
import logging
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langgraph.prebuilt import chat_agent_executor
from langchain_core.messages import SystemMessage

# REFL
# from langchain_community.tools.refl import PythonREPLTool # ¡Elimina o comenta esta línea!
from langchain_experimental.tools.python.tool import PythonREPLTool # ¡Usa esta en su lugar!
from langchain_core.tools import Tool

# Configuración de Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuración OpenAI ---
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("La variable de entorno OPENAI_API_KEY no está configurada.")

# --- Herramienta REFL para manipular Excel ---
# Se provee contexto inicial como sugerencia para que el agente trabaje con Excel
context_code = """
import pandas as pd

# Cargar el archivo Excel
df = pd.read_excel('datos.xlsx')
"""

refl_tool = PythonREPLTool(
    name="python_refl_excel",
    description="Usa esta herramienta para leer, analizar, modificar y guardar archivos Excel usando Python. El archivo se llama 'datos.xlsx'.",
    context=context_code,
)

# Envolvemos en Tool si hace falta estandarizar el tipo
refl_excel_tool = Tool.from_function(
    func=refl_tool.run,
    name="ManipuladorExcel",
    description=refl_tool.description
)

# --- Creación del Agente LangGraph ---
def get_agent():
    """Crea y configura el agente LangGraph."""
    logger.info("Creando el agente LangGraph con Python REFL para Excel...")
    llm = ChatOpenAI(model="o3-mini", temperature=0, openai_api_key=api_key)
    tools = [refl_excel_tool]

    agent_executor = chat_agent_executor.create_tool_calling_executor(llm, tools)

    logger.info("Agente LangGraph creado exitosamente con REFL.")
    return agent_executor