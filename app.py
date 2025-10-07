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
    # Header beta requerido para ChatKit:
    "OpenAI-Beta": "chatkit_beta=v1",
}

# ========= APP =========
app = FastAPI(title="ChatKit token server")

# CORS abierto (para pruebas). Cuando todo funcione, lo cerramos a tus dominios.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,                  # con "*" debe ser False
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Middleware extra: fuerza headers CORS y responde preflights
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    if request.method == "OPTIONS":
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

# ======== HELPERS =========
async def create_chatkit_session():
    """Llama a /chatkit/sessions con workflow + user y devuelve (ok, payload|error)."""
    payload = {
        "workflow": {"id": WORKFLOW_ID},   # <- CLAVE
        "user": {"id": anon_user_id()},    # <- CLAVE
        "expires_in_seconds": 3600,
    }
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.post(f"{API_BASE}/chatkit/sessions", headers=HEADERS, json=payload)
            # Intenta parsear JSON; si no, conserva el texto
            body_text = await r.aread()
            text = body_text.decode("utf-8", errors="replace") if body_text else ""
            try:
                data = r.json()
            except Exception:
                data = None

            if r.status_code >= 400:
                # Devuelve TODO para diagnóstico
                return False, {
                    "status": r.status_code,
                    "headers": dict(r.headers),
                    "text": text,
                    "json": data,
                    "note": "Fallo al crear sesión de ChatKit",
                }

            # OK: normaliza salida
            if data and isinstance(data.get("client_secret"), dict):
                return True, {
                    "client_secret": data["client_secret"].get("value"),
                    "expires_at": data["client_secret"].get("expires_at"),
                }
            elif data and "client_secret" in data:
                return True, {"client_secret": data["client_secret"]}
            else:
                return False, {
                    "status": r.status_code,
                    "headers": dict(r.headers),
                    "text": text,
                    "json": data,
                    "note": "Respuesta sin client_secret",
                }

    except Exception as e:
        # Devuelve tipo y mensaje de la excepción (a veces str(e) viene vacío)
        return False, {
            "exception": type(e).__name__,
            "message": repr(e),
            "note": "Excepción al llamar a la API de OpenAI",
        }

# ========= ROUTES =========
@app.get("/")
async def root():
    return {
        "ok": True,
        "service": "ChatKit token server",
        "endpoints": ["/health", "/api/chatkit/start", "/api/chatkit/refresh", "/debug/start"],
        "workflow_env_present": bool(WORKFLOW_ID),
    }

@app.get("/health")
async def health():
    return {"ok": True}

# Preflights explícitos
@app.options("/api/chatkit/start")
async def options_start():
    return PlainTextResponse("ok", status_code=200)

@app.options("/api/chatkit/refresh")
async def options_refresh():
    return PlainTextResponse("ok", status_code=200)

@app.post("/api/chatkit/start")
async def start():
    ok, result = await create_chatkit_session()
    if not ok:
        return JSONResponse({"error": result}, status_code=500 if "exception" in result else result.get("status", 500))
    return result

@app.post("/api/chatkit/refresh")
async def refresh():
    # Estrategia simple: emitir un NUEVO client_secret en vez de "refresh"
    ok, result = await create_chatkit_session()
    if not ok:
        return JSONResponse({"error": result}, status_code=500 if "exception" in result else result.get("status", 500))
    return result

# Endpoint de prueba directa (desde el servidor) para ver el detalle sin CORS
@app.get("/debug/start")
async def debug_start():
    ok, result = await create_chatkit_session()
    return {"ok": ok, "result": result}
