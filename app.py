import os
import httpx
from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

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

# (1) CORS completamente abierto para pruebas (sin credenciales)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],               # luego podremos cerrarlo a tus dominios
    allow_credentials=False,           # con "*" debe ser False
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# (2) Middleware extra para forzar headers CORS en TODAS las respuestas
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    if request.method == "OPTIONS":
        # Respuesta directa a preflight
        response = PlainTextResponse("ok", status_code=200)
    else:
        response = await call_next(request)

    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Expose-Headers"] = "*"
    return response

def anon_user_id() -> str:
    return f"anon_{uuid4().hex}"

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

# (3) Endpoints OPTIONS explícitos (preflight)
@app.options("/api/chatkit/start")
async def options_start():
    return PlainTextResponse("ok", status_code=200)

@app.options("/api/chatkit/refresh")
async def options_refresh():
    return PlainTextResponse("ok", status_code=200)

@app.post("/api/chatkit/start")
async def start():
    """
    Crea una sesión de ChatKit y devuelve el client_secret (token corto).
    Requiere: workflow + user
    """
    payload = {
        "workflow": {"id": WORKFLOW_ID},
        "user": {"id": anon_user_id()},
        "expires_in_seconds": 3600,
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
                return JSONResponse({"error": data}, status_code=r.status_code)

            secret = data.get("client_secret", {})
            if isinstance(secret, dict):
                return {"client_secret": secret.get("value"), "expires_at": secret.get("expires_at")}
            return {"client_secret": secret}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/chatkit/refresh")
async def refresh(request: Request):
    """
    Estrategia simple: emitir un NUEVO client_secret (en lugar de 'refresh').
    También incluye 'user'.
    """
    payload = {
        "workflow": {"id": WORKFLOW_ID},
        "user": {"id": anon_user_id()},
        "expires_in_seconds": 3600,
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
                return JSONResponse({"error": data}, status_code=r.status_code)

            secret = data.get("client_secret", {})
            if isinstance(secret, dict):
                return {"client_secret": secret.get("value"), "expires_at": secret.get("expires_at")}
            return {"client_secret": secret}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
