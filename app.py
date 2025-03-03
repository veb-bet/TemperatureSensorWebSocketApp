import asyncio
import json
import random
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

clients = {}

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

async def send_temperature(websocket: WebSocket):
    while True:
        temperature = 150 + random.uniform(-1, 1)
        message = json.dumps({"jsonrpc": "2.0", "result": temperature, "id": None})
        await websocket.send_text(message)
        await asyncio.sleep(1)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients[websocket] = None

    try:
        while True:
            data = await websocket.receive_text()
            request = json.loads(data)

            if request.get("method") == "start":
                if websocket in clients and clients[websocket] is None:
                    clients[websocket] = asyncio.create_task(send_temperature(websocket))

            elif request.get("method") == "stop":
                if websocket in clients and clients[websocket] is not None:
                    clients[websocket].cancel()
                    clients[websocket] = None

    except Exception as e:
        print(f"Connection closed: {e}")
    finally:
        del clients[websocket]

@app.get("/")
async def get():
    return HTMLResponse(content=HTML)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
