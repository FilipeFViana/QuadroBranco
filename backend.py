from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import json
import asyncio

app = FastAPI()

# Rota raiz para checagem de status no Render
@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <html>
        <head><title>Quadro Branco - Backend</title></head>
        <body>
            <h1>Servidor FastAPI do Quadro Branco</h1>
            <p>Status: Online ✅</p>
        </body>
    </html>
    """

# "Banco de dados" do grupo
quadro_dados = {}

# Conexões ativas com frontends
frontends = set()

# Conexão com o Core
core_ws = None


@app.websocket("/ws/frontend")
async def websocket_frontend(websocket: WebSocket):
    await websocket.accept()
    frontends.add(websocket)
    print("🔌 Frontend conectado.")

    try:
        while True:
            data = await websocket.receive_json()

            usuario = data.get("usuario", "Desconhecido")
            conteudo = data.get("conteudo")
            tipo = data.get('tipo')
            acao = data.get('acao')

            # Atualiza o "banco de dados"
            quadro_dados[usuario] = conteudo
            print(f"📥 {usuario} enviou: {conteudo}")

            # Envia para o Core, se conectado
            if core_ws:
                await core_ws.send_json({
                    "grupo": "G1",
                    "acao": "atualizacao",
                    "dados": {
                        "usuario": usuario,
                        "tipo": tipo,
                        "acao": acao,
                        "conteudo": conteudo
                    }
                })

            # Envia para todos os frontends (inclusive quem enviou, para testes locais)
            for ws in frontends:
                await ws.send_json({
                    "usuario": usuario,
                    "tipo": tipo,
                    "acao": acao,
                    "conteudo": conteudo
                })

    except Exception as e:
        frontends.remove(websocket)
        print("⚠️ Frontend desconectado.")
        print("❌ Erro ao decodificar JSON:", e)


@app.websocket("/ws/core")
async def websocket_core(websocket: WebSocket):
    global core_ws
    await websocket.accept()
    core_ws = websocket
    print("🔗 Conectado ao core.")

    try:
        while True:
            data = await websocket.receive_json()
            print(f"🔁 Recebido do core: {data}")

            # Repassa a todos os frontends
            for ws in frontends:
                await ws.send_json(data)

    except WebSocketDisconnect:
        core_ws = None
        print("❌ Core desconectado.")
