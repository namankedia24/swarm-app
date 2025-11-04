import asyncio
import uuid
from dataclasses import dataclass
from typing import Dict, Optional, Set, List, Any

from base_swarm import Mode, SwarmModel, TorusModel, HPPModel, DPPModel


MODE_CLASS_MAP = {
    Mode.SWARM: SwarmModel,
    Mode.TORUS: TorusModel,
    Mode.HPP: HPPModel,
    Mode.DPP: DPPModel,
}


@dataclass
class SimulationSettings:
    num_agents: int = 20
    mode: Mode = Mode.SWARM
    timestep: float = 0.1
    update_interval: float = 0.1


class SimulationInstance:
    def __init__(self, settings: SimulationSettings):
        self.id: str = str(uuid.uuid4())
        self.settings = settings
        model_cls = MODE_CLASS_MAP[settings.mode]
        self.model = model_cls(settings.num_agents)
        self.timestep = settings.timestep
        self.update_interval = settings.update_interval
        self.tick: int = 0
        self._subscribers: Set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()
        self._runner_task: Optional[asyncio.Task] = None
        self._running = False

    async def snapshot(self) -> Dict[str, Any]:
        async with self._lock:
            state = [
                {
                    "id": agent.id,
                    "position": agent.pos,
                    "velocity": agent.velocity_unit_vector,
                }
                for agent in self.model.agents
            ]
            return {
                "simulation_id": self.id,
                "tick": self.tick,
                "params": {
                    "num_agents": self.settings.num_agents,
                    "mode": self.settings.mode.value,
                    "timestep": self.timestep,
                    "update_interval": self.update_interval,
                },
                "agents": state,
            }

    async def register(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(queue)
        if not self._running:
            await self._start()
        return queue

    def unregister(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)
        if not self._subscribers:
            asyncio.create_task(self._stop())

    async def _start(self) -> None:
        if self._runner_task and not self._runner_task.done():
            return
        self._running = True
        self._runner_task = asyncio.create_task(self._run())

    async def _stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._runner_task:
            self._runner_task.cancel()
            try:
                await self._runner_task
            except asyncio.CancelledError:
                pass
            self._runner_task = None

    async def _run(self) -> None:
        try:
            while self._running:
                async with self._lock:
                    agents_state: List[Dict[str, Any]] = self.model.step(self.timestep)
                    self.tick += 1
                    payload = {
                        "simulation_id": self.id,
                        "tick": self.tick,
                        "agents": agents_state,
                    }
                await self._broadcast(payload)
                await asyncio.sleep(self.update_interval)
        except asyncio.CancelledError:
            pass

    async def _broadcast(self, payload: Dict[str, Any]) -> None:
        if not self._subscribers:
            return
        for subscriber in list(self._subscribers):
            await subscriber.put(payload)

    async def close(self) -> None:
        await self._stop()
        for queue in self._subscribers:
            queue.put_nowait({"type": "shutdown"})
        self._subscribers.clear()


class SimulationManager:
    def __init__(self) -> None:
        self._instances: Dict[str, SimulationInstance] = {}
        self._lock = asyncio.Lock()

    async def create(self, settings: SimulationSettings) -> SimulationInstance:
        instance = SimulationInstance(settings)
        async with self._lock:
            self._instances[instance.id] = instance
        return instance

    async def get(self, simulation_id: str) -> Optional[SimulationInstance]:
        async with self._lock:
            return self._instances.get(simulation_id)

    async def list_simulations(self) -> List[Dict[str, Any]]:
        async with self._lock:
            return [
                {
                    "simulation_id": sim_id,
                    "num_agents": instance.settings.num_agents,
                    "mode": instance.settings.mode.value,
                    "tick": instance.tick,
                }
                for sim_id, instance in self._instances.items()
            ]

    async def delete(self, simulation_id: str) -> bool:
        async with self._lock:
            instance = self._instances.pop(simulation_id, None)
        if instance is None:
            return False
        await instance.close()
        return True

