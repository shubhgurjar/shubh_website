import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from config import STATIC_DIR, UPLOADS_DIR
from database import init_db, seed_default_data_if_empty
from routers import auth, domains, topics, resources, uploads, backup


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist and seed initial data
    init_db()
    seed_default_data_if_empty()
    yield
    # Shutdown logic if any


app = FastAPI(
    title="Shubh's Software Engineering Knowledge Hub",
    description="Personal career knowledge hub to organize learning, YouTube videos, PDFs, and Google Drive resources.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(domains.router)
app.include_router(topics.router)
app.include_router(resources.router)
app.include_router(uploads.router)
app.include_router(backup.router)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def serve_index():
    return FileResponse(STATIC_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Starting Career Hub server on http://localhost:{port}")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
