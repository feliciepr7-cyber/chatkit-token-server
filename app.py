from fastapi.middleware.cors import CORSMiddleware

ALLOWED_ORIGINS = [
    "https://frankiefelicie.net",
    "https://www.frankiefelicie.net",
    "https://ministerioai.com",
    "https://www.ministerioai.com",
    "https://lakestationchurch.com",
    "http://localhost:5500",  # para pruebas locales
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,   # OK con lista explícita
    allow_methods=["*"],
    allow_headers=["*"],
)
