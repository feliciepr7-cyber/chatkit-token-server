import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from starlette.responses import JSONResponse

# === Config ===
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
WORKFLOW_ID = os.environ.get("WORKFLOW_ID", "")  # Pon aquí tu wf_... en Render

client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(title="ChatKit token server")

# CORS: permite tu(s) dominio(s). Si prefieres, usa ["*"] durante pruebas.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # o ["https://frankiefelicie.net", "https://www.frankiefelicie.net"]
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RefreshBody(BaseModel):
    currentClientSecret: str | None = None

@app.get("/health")
def health():
    ok = bool(OPENAI_API_KEY) and bool(WORKFLOW_ID)
    return {
        "ok": ok,
        "service": "ChatKit token server",
        "endpoints": ["/health", "/api/chatkit/start", "/api/chatkit/refresh"],
        "workflow_id_present": bool(WORKFLOW_ID),
    }

@app.post("/api/chatkit/start")
def start_session():
    if not OPENAI_API_KEY:
        return JSONResponse(status_code=500, content={"error": "Missing OPENAI_API_KEY env var"})
    if not WORKFLOW_ID:
        return JSONResponse(status_code=500, content={"error": "Missing WORKFLOW_ID env var"})

    # 🔧 FIX CLAVE: usar `workflow` (no `workflow_id`)
    session = client.beta.chatkit.sessions.create({
        "workflow": {"id": WORKFLOW_ID},
        "expires_in_seconds": 3600,
    })
    return {"client_secret": session.client_secret}

@app.post("/api/chatkit/refresh")
def refresh_session(body: RefreshBody):
    # Sencillo y robusto: en vez de "refresh", emitimos un nuevo token.
    if not OPENAI_API_KEY or not WORKFLOW_ID:
        return JSONResponse(status_code=500, content={"error": "Server not configured"})

    session = client.beta.chatkit.sessions.create({
        "workflow": {"id": WORKFLOW_ID},
        "expires_in_seconds": 3600,
    })
    return {"client_secret": session.client_secret}
