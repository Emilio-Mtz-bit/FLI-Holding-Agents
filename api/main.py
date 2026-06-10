import sys
from pathlib import Path

# Must come before any rga-copilot imports
sys.path.insert(0, str(Path(__file__).parent.parent / "rga-copilot"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.run import router as run_router
from routes.jobs import router as jobs_router

app = FastAPI(title="RGA Copilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(run_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")
