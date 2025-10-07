import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI

# --- Config básica ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY no está configurada")

WORKFLOW_ID = os.environ.get(
    "WORKFLOW_ID",
    "wf_68e51771e33c8190a73d77c930b53fbd09426d7625ac0c1f"
)

# Orígenes permitidos (CORS) desde env var o default
origins_env = os.environ.get("ALLOWED_ORIGINS", "")
if origins_env.strip():
    ALLOWED_ORIGINS = [o.strip() for o in origins_env.split(",") if o.strip()]
else:
    ALLOWED_ORIGINS = [
        "https://frankiefelicie.net",
        "https://ministerioai.com",
        "https://lakestationchurch.com",
        "http://localhost:5500",  # para pruebas locales con live-server, etc.
    ]

# Cliente OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# App FastAPI
app = FastAPI()

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Rutas ---
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/api/chatkit/start")
async def start_session():
    # Crea sesión ChatKit y devuelve client_secret (token corto)
    session = client.chatkit.sessions.create({
        "workflow_id": WORKFLOW_ID,
        "user": { "id": "anon_" + os.urandom(4).hex() }
    })
    return {"client_secret": session.client_secret}

@app.post("/api/chatkit/refresh")
async def refresh_session(req: Request):
    data = await req.json()
    current = data.get("currentClientSecret")
    session = client.chatkit.sessions.refresh({
        "client_secret": current
    })
    return {"client_secret": session.client_secret}
