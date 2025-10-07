import os
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ========= CONFIG =========
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
WORKFLOW_ID = os.environ.get("WORKFLOW_ID")
API_BASE = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")

if not OPENAI_API_KEY:
    raise RuntimeError("Falta OPENAI_API_KEY en variables de entorno.")
if not WORKFLOW_ID:
    raise RuntimeError("Falta WORKFLOW_ID en variables de entorno.")

HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "Content-Type": "application/json",
    "OpenAI-Beta": "chatkit_beta=v1",
}

# ========= APP =========
app = FastAPI(title="ChatKit token server")

# CORS abierto para superar preflight mientras probamos
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],         # Cuando ya funcione, puedes cambiar a la lista de tus dominios
    allow_credentials=False,     # IMPORTANTE: con "*" debe ser False
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ========= ROUTES =========
@app.get("/")
async def root():
    return {
        "ok": True,
        "service": "ChatKit token server",
        "endpoints": ["/health", "/api/chatkit/start", "/api/chatkit/refresh"],
        "workflow_env_present": bool(WORKFLOW_ID),
    }

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/api/chatkit/start")
async def start():
    """
    Crea una sesión de ChatKit y devuelve el client_secret (token corto).
    """
    payload = {
        "workflow": {"id": WORKFLOW_ID},   # CLAVE: usar 'workflow' -> {'id': ...}
        "expires_in_seconds": 3600,
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(f"{API_BASE}/chatkit/sessions",
                                  headers=HEADERS, json=payload)
            data = r.json()
            if r.status_code >= 400:
                return JSONResponse({"error": data}, status_code=r.status_code)

            # La API devuelve {"client_secret": {"value": "...", "expires_at": "..."}}
            secret = data.get("client_secret", {})
            if isinstance(secret, dict):
                return {"client_secret": secret.get("value"), "expires_at": secret.get("expires_at")}
            return {"client_secret": secret}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/chatkit/refresh")
async def refresh(request: Request):
    """
    Renovación sencilla: emitimos un NUEVO client_secret (evita edge-cases de refresh).
    """
    payload = {
        "workflow": {"id": WORKFLOW_ID},
        "expires_in_seconds": 3600,
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(f"{API_BASE}/chatkit/sessions",
                                  headers=HEADERS, json=payload)
            data = r.json()
            if r.status_code >= 400:
                return JSONResponse({"error": data}, status_code=r.status_code)

            secret = data.get("client_secret", {})
            if isinstance(secret, dict):
                return {"client_secret": secret.get("value"), "expires_at": secret.get("expires_at")}
            return {"client_secret": secret}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
