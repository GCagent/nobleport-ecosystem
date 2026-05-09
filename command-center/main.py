from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path
from agents import get_all_agents, get_system_metrics, DIVISIONS
from control_plane import router as control_plane_router

app = FastAPI(title="Nobleport Command Center", version="1.0.0")
app.include_router(control_plane_router)

STATIC_DIR = Path(__file__).parent / "static"
TEMPLATE_DIR = Path(__file__).parent / "templates"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return (TEMPLATE_DIR / "dashboard.html").read_text()


@app.get("/api/agents")
async def api_agents(division: int | None = None, status: str | None = None, search: str | None = None):
    agents = get_all_agents()
    if division:
        agents = [a for a in agents if a.division_id == division]
    if status:
        agents = [a for a in agents if a.status == status]
    if search:
        q = search.lower()
        agents = [a for a in agents if q in a.name.lower() or q in a.description.lower()]
    return {"agents": [a.model_dump() for a in agents], "count": len(agents)}


@app.get("/api/metrics")
async def api_metrics():
    return get_system_metrics()


@app.get("/api/divisions")
async def api_divisions():
    return {"divisions": DIVISIONS}


@app.get("/api/agents/{agent_id}")
async def api_agent_detail(agent_id: int):
    agents = get_all_agents()
    for a in agents:
        if a.id == agent_id:
            return a.model_dump()
    return {"error": "Agent not found"}


@app.get("/api/revenue-engine")
async def api_revenue_engine():
    agents = get_all_agents()
    engine = [a for a in agents if a.is_revenue_engine]
    return {"agents": [a.model_dump() for a in engine]}
