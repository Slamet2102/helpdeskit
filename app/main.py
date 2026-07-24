import os
import asyncio
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from pathlib import Path

from .database import init_db
from .config import UPLOAD_DIR
from .routers import dashboard, tiket, master, auth

# Buat aplikasi
app = FastAPI(
    title="Helpdesk IT Rumah Sakit",
    description="Aplikasi pencatatan tiket kerusakan hardware dan jaringan",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Static files
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Uploads directory
upload_dir = Path(UPLOAD_DIR)
upload_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")


# Register routers
app.include_router(dashboard.router)
app.include_router(tiket.router)
app.include_router(master.router)
app.include_router(auth.router)


@app.on_event("startup")
def startup():
    """Inisialisasi database saat aplikasi mulai."""
    init_db()


@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "Helpdesk IT Rumah Sakit is running"}


@app.get("/api/events")
async def sse_events(request: Request):
    """Server-Sent Events endpoint for real-time updates."""
    from fastapi.responses import StreamingResponse
    from .events import event_manager

    async def event_generator():
        queue = event_manager.subscribe()
        try:
            yield f": connected\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield f"data: {message}\n\n"
                except asyncio.TimeoutError:
                    yield f": keepalive\n\n"
        finally:
            event_manager.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# Serve frontend pages
from .routers.auth import decode_token
from .events import event_manager


def get_authenticated_user(request: Request):
    """Extract token from cookie or Authorization header and return user info dict, or None."""
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        token = request.cookies.get("auth_token")
    if not token:
        return None

    payload = decode_token(token)
    return payload


def require_auth(request: Request):
    """Dependency/helper: redirect to login if not authenticated."""
    user = get_authenticated_user(request)
    if user is None:
        next_url = request.url.path
        if request.query_params:
            next_url += "?" + str(request.query_params)
        return RedirectResponse(url=f"/login?next={next_url}")
    return user


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/tiket/baru", response_class=HTMLResponse)
async def tiket_baru(request: Request):
    # Optional auth — check if user is logged in for UI purposes, but allow access
    return templates.TemplateResponse(request, "tiket_form.html")


@app.get("/tiket", response_class=HTMLResponse)
async def daftar_tiket(request: Request):
    return templates.TemplateResponse(request, "daftar_tiket.html")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    # If already logged in, redirect to dashboard
    user = get_authenticated_user(request)
    if user is not None:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request, "login.html")


@app.get("/tiket/arsip", response_class=HTMLResponse)
async def arsip_tiket(request: Request):
    auth_result = require_auth(request)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    return templates.TemplateResponse(request, "archived_tiket.html")


@app.get("/tiket/{tiket_id}", response_class=HTMLResponse)
async def detail_tiket(request: Request, tiket_id: int):
    return templates.TemplateResponse(
        request,
        "tiket_detail.html",
        {"tiket_id": tiket_id}
    )


@app.get("/master", response_class=HTMLResponse)
async def master_data(request: Request):
    auth_result = require_auth(request)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    return templates.TemplateResponse(request, "master_data.html")
