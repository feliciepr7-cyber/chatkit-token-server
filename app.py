import os
import httpx
from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

# ========= CONFIG =========
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
WORKFLOW_ID = os.environ.get("WORKFLOW_ID")              # wf_...
OPENAI_PROJECT = os.environ.get("OPENAI_PROJECT")        # proj_... (opcional pero recomendado)
API_BASE = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")

if not OPENAI_API_KEY:
    raise RuntimeError("Falta OPENAI_API_KEY.")
if not WORKFLOW_ID:
    raise RuntimeError("Falta WORKFLOW_ID (wf_...).")

# HEADERS base
HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "Content-Type": "application/json",
    "OpenAI-Beta": "chatkit_beta=v1",
}
# Forzar Project si se especifica (asegura que el wf_ sea visible)
if OPENAI_PROJECT:
    HEADERS["OpenAI-Project"] = OPENAI_PROJECT  # ver docs de Projects. 

# ========= APP =========
app = FastAPI(title="ChatKit token server")

# CORS abierto para pruebas (luego lo cerramos a tus dominios)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,                  # con "*" debe ser False
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Middleware extra: responde preflight y fuerza headers CORS
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
    """
    Llama a /chatkit/sessions con workflow + user (string).
    Si hay 404 de workflow, casi seguro es Project mismatch o wf_ incorrecto.
    """
    payload = {
        "workflow": {"id": WORKFLOW_ID},
        "user": anon_user_id(),   # string (la API lo exige)
    }
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.post(f"{API_BASE}/chatkit/sessions", headers=HEADERS, json=payload)
            try:
                data = r.json()
            except Exception:
                data = {"raw": (await r.aread()).decode("utf-8", errors="replace")}

            if r.status_code >= 400:
                return False, {"status": r.status_code, "json": data, "note": "Fallo al crear sesión de ChatKit"}

            cs = data.get("client_secret")
            if isinstance(cs, dict):
                return True, {"client_secret": cs.get("value"), "expires_at": cs.get("expires_at")}
            return True, {"client_secret": cs}
    except Exception as e:
        return False, {"exception": type(e).__name__, "message": repr(e)}

# ========= ROUTES =========
@app.get("/")
async def root():
    return {
        "ok": True,
        "service": "ChatKit token server",
        "endpoints": ["/health", "/api/chatkit/start", "/api/chatkit/refresh", "/debug/start"],
        "workflow_env_present": bool(WORKFLOW_ID),
        "project_header_present": bool(OPENAI_PROJECT),
    }

@app.get("/health")
async def health():
    return {"ok": True}

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
        return JSONResponse({"error": result}, status_code=result.get("status", 500))
    return result

@app.post("/api/chatkit/refresh")
async def refresh():
    ok, result = await create_chatkit_session()  # nuevo token simple
    if not ok:
        return JSONResponse({"error": result}, status_code=result.get("status", 500))
    return result

@app.get("/debug/start")
async def debug_start():
    ok, result = await create_chatkit_session()
    return {"ok": ok, "result": result}
