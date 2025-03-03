import asyncio
import logging
import json
import random
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# Настройка логгера для отслеживания событий в приложении
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)  # Получаем основной логгер

# Создание экземпляра FastAPI приложения
app = FastAPI()

# Добавление поддержки CORS для всех доменов и методов
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем запросы с любых источников
    allow_credentials=True,
    allow_methods=["*"],  # Разрешаем любые HTTP-методы
    allow_headers=["*"]  # Разрешаем любые заголовки
)

# Словарь для хранения активных WebSocket-соединений
clients = {}

# HTML-шаблон для главной страницы
HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebSocket Temperature Sensor</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f4f4;
            margin: 0;
            padding: 20px;
            color: #333;
        }
        h1 {
            text-align: center;
        }
        .container {
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        button {
            margin: 5px;
            padding: 10px 15px;
            font-size: 16px;
            cursor: pointer;
            border: none;
            border-radius: 5px;
            background-color: #5cba47;
            color: white;
            transition: background-color 0.3s, transform 0.2s;
        }
        button:hover {
            background-color: #4cae4f;
            transform: scale(1.05);
        }
        #messages {
            margin-top: 20px;
            background: white;
            border-radius: 5px;
            padding: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            max-width: 400px;
            width: 100%;
        }
        .message {
            padding: 5px;
            border-bottom: 1px solid #eee;
            transition: background-color 0.3s;
        }
        .message:last-child {
            border-bottom: none;
        }
        .message:hover {
            background-color: #f0f0f0;
        }
        #last-message {
            font-size: 18px;
            margin-top: 20px;
            padding: 10px;
            background: #eaeaea;
            border-radius: 5px;
            width: 100%;
            text-align: center;
        }
        .copy-button {
            margin-top: 10px;
            padding: 8px;
            cursor: pointer;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 5px;
            transition: background-color 0.3s, transform 0.2s;
        }
        .copy-button:hover {
            background-color: #0056b3;
            transform: scale(1.05);
        }
    </style>
    <script>
        var ws;

        function connect() {
            ws = new WebSocket("ws://localhost:8000/ws");
            ws.onmessage = function(event) {
                var message = JSON.parse(event.data);
                var messagesDiv = document.getElementById("messages");
                var newMessage = document.createElement("div");
                newMessage.className = "message";
                newMessage.innerText = "Temperature: " + message.result.toFixed(2) + " °C";
                messagesDiv.appendChild(newMessage);

                document.getElementById("last-message").innerText = "Последняя температура: " + message.result.toFixed(2) + " °C";
            };
        }

        function startSending() {
            ws.send(JSON.stringify({"jsonrpc": "2.0", "method": "start", "params": []}));
            document.getElementById("last-message").innerText = "Последняя температура: Не получена";
        }

        function stopSending() {
            ws.send(JSON.stringify({"jsonrpc": "2.0", "method": "stop", "params": []}));
        }

        function copyLastMessage() {
            var lastMessage = document.getElementById("last-message").innerText;
            navigator.clipboard.writeText(lastMessage).then(function() {
                alert("Скопировано в буфер обмена: " + lastMessage);
            });
        }

        window.onload = connect;
    </script>
</head>
<body>
    <h1>WebSocket Temperature Sensor</h1>
    <div class="container">
        <button onclick="startSending()">Начать отправлять</button>
        <button onclick="stopSending()">Остановить отправку</button>
        <div id="last-message">Последняя температура: Не получена</div>
        <button class="copy-button" onclick="copyLastMessage()">Скопировать последнее значение</button>
        <div id="messages"></div>
    </div>
</body>
</html>
"""

# Асинхронная функция для отправки температуры каждому подключенному клиенту
async def send_temperature(websocket: WebSocket):
    logger.info(f"Sending temperature task started for client {websocket.client}")  # Логируем запуск задачи
    while True:
        # Генерация случайной температуры
        temperature = 150 + random.uniform(-1, 1)

        # Форматируем сообщение в формате JSON-RPC
        message = json.dumps({
            "jsonrpc": "2.0",
            "result": temperature,  # Передаем текущее значение температуры
            "id": None  # ID запроса оставляем пустым
        })

        # Отправляем сообщение клиенту через WebSocket
        await websocket.send_text(message)

        # Логируем отправленное значение температуры
        logger.debug(f"Sent temperature: {temperature:.2f}°C to client {websocket.client}")

        # Пауза перед следующей отправкой (каждую секунду)
        await asyncio.sleep(1)


# Обработчик WebSocket соединений
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()  # Принять новое соединение
    clients[websocket] = None  # Добавляем новый клиент в словарь
    logger.info(f"New WebSocket connection from {websocket.client}")  # Логируем новое подключение

    try:
        while True:
            # Ждем поступающих команд от клиента
            data = await websocket.receive_text()
            request = json.loads(data)  # Парсим JSON-запрос

            # Если команда 'start', начинаем отправлять температуру
            if request.get("method") == "start":
                if websocket in clients and clients[websocket] is None:
                    # Запускаем асинхронную задачу для отправки температуры
                    clients[websocket] = asyncio.create_task(send_temperature(websocket))
                    logger.info(f"Started sending temperature to client {websocket.client}")

            # Если команда 'stop', останавливаем отправку температуры
            elif request.get("method") == "stop":
                if websocket in clients and clients[websocket] is not None:
                    # Отменяем задачу отправки температуры
                    clients[websocket].cancel()
                    clients[websocket] = None
                    logger.info(f"Stopped sending temperature to client {websocket.client}")

    # Обработка исключений
    except asyncio.CancelledError:
        logger.warning(f"Task cancelled for client {websocket.client}")
    except Exception as e:
        logger.error(f"An error occurred during WebSocket handling: {str(e)}")
    finally:
        # Удаление клиента из списка после завершения работы
        del clients[websocket]
        logger.info(f"Disconnected WebSocket from {websocket.client}")


# Маршрут для получения HTML-страницы
@app.get("/")
async def get():
    return HTMLResponse(content=HTML)


# Запуск сервера
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)

