from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

from base_swarm import Mode
from simulation_manager import SimulationManager, SimulationSettings


app = FastAPI(title="Swarm Simulation Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

simulation_manager = SimulationManager()

MODE_LOOKUP = {mode.value: mode for mode in Mode}


class SimulationCreateRequest(BaseModel):
    num_agents: int = Field(default=20, ge=1, le=500)
    mode: str = Field(default=Mode.SWARM.value)
    timestep: float = Field(default=0.1, gt=0.0)
    update_interval: float = Field(default=0.1, gt=0.0)

    @validator("mode")
    def validate_mode(cls, value: str) -> str:
        if value not in MODE_LOOKUP:
            raise ValueError(f"Unsupported mode '{value}'. Allowed: {list(MODE_LOOKUP)}")
        return value


class SimulationCreateResponse(BaseModel):
    simulation_id: str
    num_agents: int
    mode: str


class SimulationListItem(BaseModel):
    simulation_id: str
    num_agents: int
    mode: str
    tick: int


class SimulationSnapshot(BaseModel):
    simulation_id: str
    tick: int
    params: dict
    agents: List[dict]


@app.post("/api/simulations", response_model=SimulationCreateResponse)
async def create_simulation(payload: SimulationCreateRequest) -> SimulationCreateResponse:
    mode = MODE_LOOKUP[payload.mode]
    settings = SimulationSettings(
        num_agents=payload.num_agents,
        mode=mode,
        timestep=payload.timestep,
        update_interval=payload.update_interval,
    )
    instance = await simulation_manager.create(settings)
    return SimulationCreateResponse(
        simulation_id=instance.id,
        num_agents=payload.num_agents,
        mode=payload.mode,
    )


@app.get("/api/simulations", response_model=List[SimulationListItem])
async def list_simulations() -> List[SimulationListItem]:
    simulations = await simulation_manager.list_simulations()
    return [
        SimulationListItem(
            simulation_id=item["simulation_id"],
            num_agents=item["num_agents"],
            mode=item["mode"],
            tick=item["tick"],
        )
        for item in simulations
    ]


@app.get("/api/simulations/{simulation_id}", response_model=SimulationSnapshot)
async def fetch_simulation(simulation_id: str) -> SimulationSnapshot:
    instance = await simulation_manager.get(simulation_id)
    if instance is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    snapshot = await instance.snapshot()
    return SimulationSnapshot(**snapshot)


@app.delete("/api/simulations/{simulation_id}")
async def delete_simulation(simulation_id: str) -> dict:
    removed = await simulation_manager.delete(simulation_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return {"status": "deleted", "simulation_id": simulation_id}


@app.websocket("/ws/simulations/{simulation_id}")
async def simulation_stream(websocket: WebSocket, simulation_id: str) -> None:
    instance = await simulation_manager.get(simulation_id)
    await websocket.accept()
    if instance is None:
        await websocket.send_json({"type": "error", "message": "Simulation not found"})
        await websocket.close(code=1008)
        return

    queue = await instance.register()
    try:
        snapshot = await instance.snapshot()
        await websocket.send_json({"type": "snapshot", **snapshot})
        while True:
            payload = await queue.get()
            if payload.get("type") == "shutdown":
                await websocket.send_json({"type": "shutdown"})
                break
            try:
                await websocket.send_json({"type": "tick", **payload})
            except WebSocketDisconnect:
                break
    except WebSocketDisconnect:
        pass
    finally:
        instance.unregister(queue)
        try:
            await websocket.close()
        except RuntimeError:
            pass


@app.get("/health")
async def healthcheck() -> dict:
    return {"status": "ok"}
