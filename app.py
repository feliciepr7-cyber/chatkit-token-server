import os
import json
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx

# ========= CONFIG =========
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    raise RuntimeError("Falta OPENAI_API_KEY en variables de entorno.")

# Puedes sobreescribir por ENV si quieres:
WORKFLOW_ID = os.environ.get(
    "CHATKIT_WORKFLOW_ID",
    "wf_68e51771e33c8190a73d77c930b53fbd09426d7625ac0c1f"  # <-- tu workflow
)
API_BASE = os.environ.get("CHATKIT_API_BASE", "https://api.openai.com/v1")

# Encabezados necesarios para ChatKit
HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "Content-Type": "application/json",
    "OpenAI-Beta": "chatkit_beta=v1",
}

# ========= APP =========
app = FastAPI()

# ---- CORS (opción con lista explícita de orígenes) ----
ALLOWED_ORIGINS = [
    "https://frankiefelicie.net",
    "https://www.frankiefelicie.net",
    "https://ministerioai.com",
    "https://www.ministerioai.com",
    "https://lakestationchurch.com",
    "https://www.lakestationchurch.com",
    "http://localhost:5500",  # útil para pruebas locales con live-server
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,      # ok con lista explícita
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========= ROUTES =========
@app.get("/")
async def root():
    return {
        "ok": True,
        "service": "ChatKit token server",
        "endpoints": ["/health", "/api/chatkit/start", "/api/chatkit/refresh"],
        "workflow_id": WORKFLOW_ID,
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
        "workflow_id": WORKFLOW_ID,
        "expires_in_seconds": 3600,  # 1 hora (ajustable)
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                f"{API_BASE}/chatkit/sessions",
                headers=HEADERS,
                json=payload,
            )
            data = r.json()
            if r.status_code >= 400:
                # Propaga el error de OpenAI para diagnóstico
                return JSONResponse({"error": data}, status_code=r.status_code)

            # ChatKit requiere devolver el string del client_secret
            return {
                "client_secret": data["client_secret"]["value"],
                "expires_at": data["client_secret"]["expires_at"],
            }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/chatkit/refresh")
async def refresh(request: Request):
    """
    Refresca el client_secret cuando esté por expirar.
    El frontend enviará { currentClientSecret: "..." }.
    """
    try:
        body = await request.json()
        current = body.get("currentClientSecret")
        if not current:
            return JSONResponse({"error": "Falta currentClientSecret"}, status_code=400)

        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                f"{API_BASE}/chatkit/sessions/refresh",
                headers=HEADERS,
                json={"client_secret": current},
            )
            data = r.json()
            if r.status_code >= 400:
                return JSONResponse({"error": data}, status_code=r.status_code)

            return {
                "client_secret": data["client_secret"]["value"],
                "expires_at": data["client_secret"]["expires_at"],
            }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
