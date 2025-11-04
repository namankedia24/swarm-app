import enum
import numpy as np

from backend.models.fish_agent import agent, euclidean_distance, angle_between


class Mode(enum.Enum):
    SWARM = "swarm"
    TORUS = "torus"
    HPP = "hpp"
    DPP = "dpp"


def unit_vector(vector):
    """Normalize a vector to unit length."""
    magnitude = np.linalg.norm(vector)
    return vector / magnitude if magnitude != 0 else vector


class BaseSwarmModel:
    def __init__(self, num_agents, mode=None):
        """
        Base class for swarm models with common initialization and methods.

        :param num_agents: Number of agents in the swarm
        :param mode: Mode of swarm behavior
        """
        self.num_agents = num_agents
        self.mode = mode if mode is not None else Mode.SWARM

        self.agent_distance_vector_table = np.full((num_agents, num_agents, 3), np.inf)
        self.agent_distance_magnitude_table = np.full((num_agents, num_agents), np.inf)

        self.agent_new_direction = np.zeros((num_agents, 3), dtype=np.float32)

        self.zor = 0.5
        self.zoo = 10
        self.zoa = 20

                # Generate initial agent positions
        xdata = np.random.uniform(-15, 15, num_agents)
        # xdata = np.random.uniform(0, 0, num_agents)
        ydata = np.random.uniform(-15, 15, num_agents)
        # ydata = np.random.uniform(-0, 0, num_agents)
        # zdata = np.random.uniform(-10, 10, num_agents)
        zdata = np.random.uniform(-0, 0, num_agents)

        # R = 8.0
        # theta = np.random.uniform(0, 2*np.pi, self.num_agents)
        # xdata = R * np.cos(theta)
        # ydata = np.random.normal(0, 0.2, self.num_agents)  # small thickness
        # zdata = R * np.sin(theta)


        self.agents = [
            agent(
                i,
                (xdata[i], ydata[i], zdata[i]),
                speed=None,
                velocity_unit_vector=None,
                theta=None,
                turning_angle=None,
            )
            for i in range(num_agents)
        ]

    def update_agent_distance_table(self):
        """Update distance table between agents."""
        for k in range(self.num_agents):
            self.agent_new_direction[k] = 0
        for i in range(self.num_agents):
            for j in range(self.num_agents):
                if self.agents[i].id == self.agents[j].id or self.agent_distance_magnitude_table[i][j] != np.inf:
                    continue

                r1 = np.array(self.agents[i].pos)
                r2 = np.array(self.agents[j].pos)

                self.agent_distance_vector_table[i][j] = unit_vector(r2 - r1)
                self.agent_distance_vector_table[j][i] = unit_vector(r1 - r2)

                distance = euclidean_distance(r1, r2)
                self.agent_distance_magnitude_table[i][j] = distance
                self.agent_distance_magnitude_table[j][i] = distance

    def update_agent_position(self):
        """Update agent positions based on swarm behavior."""
        raise NotImplementedError("Subclasses must implement update_agent_position method")

    def _common_update_logic(self):
        self.update_agent_distance_table()
        for i in range(self.num_agents):
            my_distance = self.agent_distance_magnitude_table[i]
            repulsion_mode = 0 if (my_distance[my_distance <= self.zor].size == 0) else 1
            flag_o = 0
            flag_a = 0
            self.agent_new_direction[i] = 0
            for j in range(self.num_agents):
                distance = self.agent_distance_magnitude_table[i][j]
                if self.agents[i].id == self.agents[j].id:
                    continue
                if repulsion_mode and distance > self.zor:
                    continue
                elif repulsion_mode and distance <= self.zor:
                    self.agent_new_direction[i] -= self.agent_distance_vector_table[i][j]
                elif distance > self.zor and distance <= self.zoo:
                    vj = np.array(self.agents[j].velocity_unit_vector)
                    vj /= 2
                    self.agent_new_direction[i] += vj
                    flag_o = 1
                elif distance > self.zoo and distance <= self.zoa:
                    self.agent_new_direction[i] += self.agent_distance_vector_table[i][j] / 2
                    flag_a = 1

            if (not repulsion_mode) and not (flag_o == 1 and flag_a == 1):
                self.agent_new_direction[i] *= 2

            if np.any(self.agent_new_direction[i]):
                self.agent_new_direction[i] = unit_vector(self.agent_new_direction[i])
            else:
                v = np.array(self.agents[i].velocity_unit_vector)
                self.agent_new_direction[i] = v

        self.agent_distance_vector_table = np.full((self.num_agents, self.num_agents, 3), np.inf)
        self.agent_distance_magnitude_table = np.full((self.num_agents, self.num_agents), np.inf)

    def step(self, timestep=0.1):
        """Advance the simulation by one timestep and return agent states."""
        self.update_agent_position()
        updates = []
        for i in range(self.num_agents):
            agent_ref = self.agents[i]
            new_direction = self.agent_new_direction[i]
            if not np.any(new_direction):
                new_direction = np.array(agent_ref.velocity_unit_vector, dtype=np.float32)
            else:
                new_direction = unit_vector(new_direction)
            agent_ref.velocity_unit_vector = tuple(new_direction.tolist())
            displacement = new_direction * agent_ref.speed * timestep
            new_position = np.array(agent_ref.pos, dtype=np.float32) + displacement
            agent_ref.pos = tuple(new_position.tolist())
            updates.append(
                {
                    "id": agent_ref.id,
                    "position": agent_ref.pos,
                    "velocity": agent_ref.velocity_unit_vector,
                }
            )
        self.agent_new_direction = np.zeros((self.num_agents, 3), dtype=np.float32)
        return updates


class SwarmModel(BaseSwarmModel):
    def __init__(self, num_agents):
        super().__init__(num_agents, Mode.SWARM)
        self.zor = 2
        self.zoo = 3
        self.zoa = 7

    def update_agent_position(self):
        """Standard swarm behavior update."""
        self._common_update_logic()


class TorusModel(BaseSwarmModel):
    def __init__(self, num_agents):
        super().__init__(num_agents, Mode.TORUS)
        self.zor = 0.3
        self.zoo = 0.8
        self.zoa = 15

    def update_agent_position(self):
        """Torus-specific positioning logic with periodic boundary conditions."""
        self._common_update_logic()


class HPPModel(BaseSwarmModel):
    def __init__(self, num_agents):
        super().__init__(num_agents, Mode.HPP)
        self.zor = 0.5
        self.zoo = 10
        self.zoa = 20

    def update_agent_position(self):
        """HPP-specific positioning logic with hard boundary conditions."""
        self._common_update_logic()


class DPPModel(BaseSwarmModel):
    def __init__(self, num_agents):
        super().__init__(num_agents, Mode.DPP)
        self.zor = 0.2
        self.zoo = 4
        self.zoa = 10

    def update_agent_position(self):
        """DPP-specific positioning with density-dependent perception."""
        self._common_update_logic()

