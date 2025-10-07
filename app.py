import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
WORKFLOW_ID = os.environ.get(
    "CHATKIT_WORKFLOW_ID",
    "wf_68e51771e33c8190a73d77c930b53fbd09426d7625ac0c1f"  # tu ID
)
API_BASE = os.environ.get("CHATKIT_API_BASE", "https://api.openai.com/v1")

if not OPENAI_API_KEY:
    raise RuntimeError("Falta OPENAI_API_KEY en variables de entorno.")

app = FastAPI()

# Permite llamadas desde tu sitio (puedes cambiar "*" por tu dominio)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "Content-Type": "application/json",
    # Este header es necesario para ChatKit hospedado
    "OpenAI-Beta": "chatkit_beta=v1",
}

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/api/chatkit/start")
async def start():
    """Crea una sesión y devuelve el client_secret corto-vencimiento."""
    payload = {
        "workflow_id": WORKFLOW_ID,
        "expires_in_seconds": 3600  # 1 hora
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(f"{API_BASE}/chatkit/sessions",
                              headers=HEADERS, json=payload)
        data = r.json()
        if r.status_code >= 400:
            return JSONResponse({"error": data}, status_code=r.status_code)
        # ChatKit quiere el string, no el objeto completo
        return {
            "client_secret": data["client_secret"]["value"],
            "expires_at": data["client_secret"]["expires_at"]
        }

@app.post("/api/chatkit/refresh")
async def refresh(request: Request):
    """Refresca el token cuando esté por expirar."""
    body = await request.json()
    current = body.get("currentClientSecret")
    if not current:
        return JSONResponse({"error": "Falta currentClientSecret"},
                            status_code=400)

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(f"{API_BASE}/chatkit/sessions/refresh",
                              headers=HEADERS, json={"client_secret": current})
        data = r.json()
        if r.status_code >= 400:
            return JSONResponse({"error": data}, status_code=r.status_code)
        return {
            "client_secret": data["client_secret"]["value"],
            "expires_at": data["client_secret"]["expires_at"]
        }
@app.get("/")
async def root():
    return {
        "ok": True,
        "service": "ChatKit token server",
        "endpoints": ["/health", "/api/chatkit/start", "/api/chatkit/refresh"]
    }
