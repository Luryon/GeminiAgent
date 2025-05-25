import os
import logging
from fastapi import FastAPI, WebSocket, Request, UploadFile, File, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import openai
import aiofiles
from langchain_core.messages import HumanMessage

# Importa la función para obtener el agente desde agent.py
from agent import get_agent

# Configuración de Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuración OpenAI (para Whisper) ---
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("La variable de entorno OPENAI_API_KEY no está configurada.")
client = openai.OpenAI(api_key=api_key)

# --- Inicialización FastAPI y Agente ---
app = FastAPI()
agent_executor = get_agent() # Obtenemos el agente al iniciar la app

# Montar directorios estáticos y de plantillas
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- Endpoints HTTP ---
@app.get("/", response_class=HTMLResponse)
async def get_chat_page(request: Request):
    """Sirve la página principal del chat."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Recibe audio, lo transcribe con Whisper y devuelve el texto."""
    logger.info(f"Recibido archivo de audio: {file.filename}")
    # Usar un nombre de archivo temporal más seguro si es posible
    temp_file_path = f"/tmp/{file.filename}" # Usar /tmp es común en entornos de nube

    try:
        # Crear directorio /tmp si no existe (importante para Railway)
        os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)

        async with aiofiles.open(temp_file_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
        logger.info(f"Archivo guardado temporalmente en: {temp_file_path}")

        with open(temp_file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="json"
            )
        logger.info(f"Transcripción recibida: {transcription.text}")
        return JSONResponse(content={"transcription": transcription.text})

    except Exception as e:
        logger.error(f"Error durante la transcripción: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e)}, status_code=500)
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            logger.info(f"Archivo temporal eliminado: {temp_file_path}")

# --- WebSocket ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Maneja la conexión WebSocket para el chat en tiempo real."""
    await websocket.accept()
    logger.info("Cliente WebSocket conectado.")
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("text")
            logger.info(f"Mensaje recibido por WebSocket: {message}")

            if message:
                try:
                    # Llama al agente LangGraph de forma asíncrona
                    response = await agent_executor.ainvoke(
                        {"messages": [HumanMessage(content=message)]}
                    )
                    # Extrae la última respuesta del agente (AIMessage)
                    agent_response = response.get("messages", [])[-1].content
                    logger.info(f"Respuesta del agente: {agent_response}")
                    await websocket.send_text(f"{agent_response}")
                except Exception as e:
                    logger.error(f"Error al invocar el agente: {e}", exc_info=True)
                    await websocket.send_text(f"Error: No pude procesar tu solicitud.")

    except WebSocketDisconnect:
        logger.info("Cliente WebSocket desconectado.")
    except Exception as e:
        logger.error(f"Error inesperado en WebSocket: {e}", exc_info=True)
        try:
            # Intenta cerrar la conexión si aún está abierta
            await websocket.close(code=1011) # Internal Error
        except RuntimeError:
            pass # La conexión ya podría estar cerrada

# --- Para ejecución local (opcional) ---
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)