"""Computed research results (FastAPI). Mirrors /api/research/* in server.py."""
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from research.common import FIG_DIR, load_json

router = APIRouter()


@router.get("/results")
def results():
    figs = sorted(f for f in os.listdir(FIG_DIR) if f.endswith(".png")) if os.path.isdir(FIG_DIR) else []
    return {"disease": load_json("disease_results.json"), "noshow": load_json("noshow_results.json"),
            "scheduling": load_json("scheduling_results.json"), "figures": figs}


@router.get("/figures/{name}")
def figure(name: str):
    path = os.path.join(FIG_DIR, os.path.basename(name))
    if not name.endswith(".png") or not os.path.isfile(path):
        raise HTTPException(404, "Not found")
    return FileResponse(path, media_type="image/png")
