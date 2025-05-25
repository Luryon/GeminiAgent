const messageText = document.getElementById('messageText');
const sendButton = document.getElementById('sendButton');
const recordButton = document.getElementById('recordButton');
const chatbox = document.getElementById('chatbox');

let ws; // Variable para el WebSocket
let mediaRecorder;
let audioChunks = [];
let isRecording = false;

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    ws = new WebSocket(`${protocol}//${host}/ws`);

    ws.onopen = (event) => {
        console.log("WebSocket conectado.");
        enableInputs();
    };

    ws.onmessage = (event) => {
        addMessageToChatbox(event.data, 'agent-message');
        enableInputs();
    };

    ws.onclose = (event) => {
        console.log("WebSocket desconectado. Intentando reconectar...", event);
        addMessageToChatbox("Conexión perdida. Intentando reconectar...", 'agent-message');
        disableInputs("Reconectando...");
        setTimeout(connectWebSocket, 3000); // Intenta reconectar cada 3 segundos
    };

    ws.onerror = (error) => {
        console.error("Error de WebSocket:", error);
        addMessageToChatbox("Error de conexión.", 'agent-message');
        ws.close(); // Cierra para forzar la reconexión
    };
}

function addMessageToChatbox(message, type) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', type);
    msgDiv.textContent = message;
    chatbox.appendChild(msgDiv);
    chatbox.scrollTop = chatbox.scrollHeight;
}

function sendMessage() {
    const message = messageText.value.trim();
    if (message && ws && ws.readyState === WebSocket.OPEN) {
        addMessageToChatbox(`Tú: ${message}`, 'user-message');
        ws.send(JSON.stringify({ text: message }));
        messageText.value = '';
        disableInputs("Esperando respuesta...");
    }
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        event.preventDefault(); // Evita el salto de línea si es un textarea
        sendMessage();
    }
}

async function sendAudioToServer(audioBlob) {
    const formData = new FormData();
    formData.append("file", audioBlob, "audio.webm");

    addMessageToChatbox("Enviando audio para transcripción...", 'user-message');
    disableInputs("Transcribiendo...");

    try {
        const response = await fetch('/transcribe', {
            method: 'POST',
            body: formData,
        });

        if (response.ok) {
            const data = await response.json();
            if (data.transcription) {
                const transcribedText = data.transcription;
                addMessageToChatbox(`Tú (voz): ${transcribedText}`, 'user-message');
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({ text: transcribedText }));
                    disableInputs("Esperando respuesta...");
                } else {
                     addMessageToChatbox("Error: No se pudo enviar la transcripción.", 'agent-message');
                     enableInputs();
                }
            } else {
                throw new Error(data.error || "La transcripción falló.");
            }
        } else {
            const errorData = await response.json();
            throw new Error(errorData.error || `Error del servidor: ${response.status}`);
        }
    } catch (error) {
        console.error("Error al transcribir el audio:", error);
        addMessageToChatbox(`Error al procesar tu voz: ${error.message}`, 'agent-message');
        enableInputs();
    }
}

recordButton.addEventListener('click', async () => {
    if (!isRecording) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = event => audioChunks.push(event.data);

            mediaRecorder.onstop = () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                sendAudioToServer(audioBlob);
                recordButton.textContent = 'Grabar';
                recordButton.classList.remove('recording');
                isRecording = false;
                stream.getTracks().forEach(track => track.stop()); // Libera el micrófono
            };

            mediaRecorder.start();
            recordButton.textContent = 'Detener';
            recordButton.classList.add('recording');
            isRecording = true;
            disableInputs("Grabando...");
            recordButton.disabled = false; // El botón de grabar debe seguir activo

        } catch (err) {
            console.error("Error al acceder al micrófono:", err);
            alert("No se pudo acceder al micrófono.");
        }
    } else {
        mediaRecorder.stop();
    }
});

function disableInputs(message = "Procesando...") {
    messageText.disabled = true;
    sendButton.disabled = true;
    recordButton.disabled = true;
    messageText.placeholder = message;
    if (isRecording && recordButton) recordButton.disabled = false; // Permitir detener la grabación
}

function enableInputs() {
    messageText.disabled = false;
    sendButton.disabled = false;
    recordButton.disabled = false;
    messageText.placeholder = 'Escribe un mensaje o usa la voz...';
}

// Iniciar la conexión WebSocket al cargar la página
document.addEventListener('DOMContentLoaded', connectWebSocket);