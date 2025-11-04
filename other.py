import numpy as np
import enum
from fish_agent import agent

from mpl_toolkits import mplot3d
import matplotlib.pyplot as plt
import mpl_toolkits.mplot3d.axes3d as p3
from matplotlib import animation

class Mode(enum.Enum):
    SWARM = 'swarm'
    TORUS = 'torus'
    HPP = 'hpp'
    DPP = 'dpp'

def unit_vector(vector):
    """Normalize a vector to unit length."""
    magnitude = np.linalg.norm(vector)
    return vector / magnitude if magnitude != 0 else vector

def angle_between(v1, v2):
    """Calculate angle between two vectors."""
    v1_u = unit_vector(v1)
    v2_u = unit_vector(v2)
    return np.arccos(np.clip(np.dot(v1_u, v2_u), -1.0, 1.0))

def euclidean_distance(r1, r2):
    """Calculate Euclidean distance between two points."""
    return np.linalg.norm(r2 - r1)

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
        xdata = 10 * np.random.random(num_agents)
        ydata = np.sin(xdata) + 1 * np.random.randn(num_agents)
        zdata = np.cos(xdata) + 1 * np.random.randn(num_agents)
        
        # Create agents
        self.agents = [
            agent(i, (xdata[i],ydata[i],zdata[i]), speed=None, velocity_unit_vector=None, 
				theta = None, turning_angle = None)
            for i in range(num_agents)
        ]
    
    def update_agent_distance_table(self):
        """Update distance table between agents."""
        for i in range(self.num_agents):
            for j in range(self.num_agents):
                if self.agents[i].id == self.agents[j].id or \
                   self.agent_distance_magnitude_table[i][j] != np.inf:
                    continue
                
                r1 = np.array(self.agents[i].pos)
                r2 = np.array(self.agents[j].pos)
                
                self.agent_distance_vector_table[i][j] = unit_vector(r2 - r1)
                self.agent_distance_vector_table[j][i] = unit_vector(r1 - r2)
                
                distance = euclidean_distance(r1, r2)
                self.agent_distance_magnitude_table[i][j] = distance
                self.agent_distance_magnitude_table[j][i] = distance
    
    def update_agent_position(self):
        """
        Update agent positions based on swarm behavior.
        To be implemented by child classes.
        """
        raise NotImplementedError("Subclasses must implement update_agent_position method")

    def _common_update_logic(self):
        """Common update logic shared by all models"""
        self.update_agent_distance_table()
        for i in range(self.num_agents):
            my_distance = self.agent_distance_magnitude_table[i]
            repulsion_mode = 0 if (my_distance[my_distance <= self.zor].size == 0) else 1
            repulsion_vector = my_distance[my_distance <= self.zor]
            flag_o = 0 
            flag_a = 0
            for j in range(self.num_agents):
                distance = self.agent_distance_magnitude_table[i][j]
                if self.agents[i].id == self.agents[j].id:
                    continue
                if repulsion_mode and distance > self.zor:
                    continue
                elif repulsion_mode and distance <= self.zor:
                    self.agent_new_direction[i] -=  self.agent_distance_vector_table[i][j]
                elif distance > self.zor and distance <= self.zoo:
                    vj = np.array(self.agents[j].velocity_unit_vector)
                    vj /= 2
                    self.agent_new_direction[i] +=  vj
                    flag_o = 1
                elif distance > self.zoo and distance <= self.zoa:
                    self.agent_new_direction[i] +=  (self.agent_distance_vector_table[i][j]/2)
                    flag_a = 1

            if (not repulsion_mode) and not (flag_o==1 and flag_a==1):
                self.agent_new_direction[i] *= 2

            if np.any(self.agent_new_direction[i]):
                v = np.array(self.agents[i].velocity_unit_vector)
                angle_to_turn = angle_between(v, self.agent_new_direction[i])
                final_angle_ratio = 1 if angle_to_turn <= self.agents[i].turning_angle else (self.agents[i].turning_angle/angle_to_turn) 
                self.agent_new_direction[i] = unit_vector(self.agent_new_direction[i])
            else:
                v = np.array(self.agents[i].velocity_unit_vector)
                self.agent_new_direction[i] = v 
        
        # Reset distance tables
        self.agent_distance_vector_table = np.full((self.num_agents, self.num_agents, 3), np.inf)
        self.agent_distance_magnitude_table = np.full((self.num_agents, self.num_agents), np.inf)

class SwarmModel(BaseSwarmModel):
    def __init__(self, num_agents):
        super().__init__(num_agents, Mode.SWARM)
        self.zor = 2
        self.zoo = 3
        self.zoa = 7
    
    def update_agent_position(self):
        """Standard swarm behavior update"""
        self._common_update_logic()
        
        # Additional swarm-specific logic can be added here
        # For example, additional boundary conditions or behavior modifiers

class TorusModel(BaseSwarmModel):
    def __init__(self, num_agents):
        super().__init__(num_agents, Mode.TORUS)
        self.zor = 0.3
        self.zoo = 0.8
        self.zoa = 15
    
    def update_agent_position(self):
        """Torus-specific positioning logic with periodic boundary conditions"""
        self._common_update_logic()
        
        # Apply torus-specific boundary conditions (wrap around)
        for i in range(self.num_agents):
            # Assuming a boundary of [-10, 10] in each dimension
            pos = np.array(self.agents[i].pos)
            
            # Apply periodic boundary conditions (wrap around)
            pos = np.mod(pos + 10, 20) - 10
            
            # Update agent position
            self.agents[i].pos = tuple(pos)

class HPPModel(BaseSwarmModel):
    def __init__(self, num_agents):
        super().__init__(num_agents, Mode.HPP)
        self.zor = 0.5
        self.zoo = 10
        self.zoa = 20
    
    def update_agent_position(self):
        """HPP-specific positioning logic with hard boundary conditions"""
        self._common_update_logic()
        
        # Apply HPP-specific logic (hard boundaries)
        boundary = 10
        for i in range(self.num_agents):
            pos = np.array(self.agents[i].pos)
            v = np.array(self.agents[i].velocity_unit_vector)
            
            # Check if agent is approaching boundary
            for dim in range(3):
                if abs(pos[dim]) > boundary * 0.9:
                    # If approaching boundary, add repulsion
                    boundary_vector = np.zeros(3)
                    boundary_vector[dim] = -np.sign(pos[dim])
                    
                    # Add boundary repulsion to agent direction
                    repulsion_strength = 1.0 - (boundary - abs(pos[dim])) / boundary
                    self.agent_new_direction[i] += boundary_vector * repulsion_strength
                    self.agent_new_direction[i] = unit_vector(self.agent_new_direction[i])
            
            # Apply hard boundary constraints
            pos = np.clip(pos, -boundary, boundary)
            self.agents[i].pos = tuple(pos)

class DPPModel(BaseSwarmModel):
    def __init__(self, num_agents):
        super().__init__(num_agents, Mode.DPP)
        self.zor = 0.2
        self.zoo = 4
        self.zoa = 10
        
        # DPP-specific parameters
        self.density_factor = 0.5
        self.perception_radius = 5.0
    
    def update_agent_position(self):
        """DPP-specific positioning with density-dependent perception"""
        # First, calculate local density for each agent
        local_density = np.zeros(self.num_agents)
        for i in range(self.num_agents):
            pos_i = np.array(self.agents[i].pos)
            neighbor_count = 0
            
            for j in range(self.num_agents):
                if i == j:
                    continue
                    
                pos_j = np.array(self.agents[j].pos)
                dist = euclidean_distance(pos_i, pos_j)
                
                if dist < self.perception_radius:
                    neighbor_count += 1
            
            local_density[i] = neighbor_count / (4/3 * np.pi * self.perception_radius**3)
        
        # Run common update logic
        self._common_update_logic()
        
        # Apply density-dependent modifications
        for i in range(self.num_agents):
            # Adjust direction based on local density
            if local_density[i] > self.density_factor:
                # In high-density regions, increase repulsion
                self.agent_new_direction[i] *= (1 + local_density[i] * 0.1)
            else:
                # In low-density regions, increase attraction
                pass  # Default behavior already handles this
            
            # Normalize the direction vector
            if np.any(self.agent_new_direction[i]):
                self.agent_new_direction[i] = unit_vector(self.agent_new_direction[i])

def update_plot_points(num,x,z, point, model, timestep=0.1):
	model.update_agent_position()
	new_data = model.agent_new_direction
	for i in range(model.num_agents):
		model.agents[i].velocity_unit_vector = tuple(new_data[i])
		x[i] += new_data[i][0]*model.agents[i].speed*timestep
		# y[i] += new_data[i][1]*model.agents[i].speed*timestep
		z[i] += new_data[i][2]*model.agents[i].speed*timestep
		model.agents[i].pos = (x[i],0,z[i])
	ax = plt.axes(projection='3d')
	ax.set_xlim(-5,5)
	ax.set_ylim(-20,20)
	# ax.set_zlim(-50,50)
	point = ax.scatter(x, z, color='b')

	return point

Writer = animation.writers['ffmpeg']
writer = Writer(fps=6000, metadata=dict(artist='Me'), bitrate=180)
num_agents = 10
FLAG = 0
fig = plt.figure(figsize=(8,8))
ax = plt.axes(projection='3d')
ax.set_xlim(-5,5)
ax.set_ylim(-50,50)
# ax.set_zlim(-50,50)
zdata =  10 * np.random.random(num_agents)
xdata = np.sin(zdata) + 5 * np.random.randn(num_agents)
# ydata = np.cos(zdata) + 5 * np.random.randn(num_agents)
# print((xdata,ydata,zdata))
point = ax.scatter([], [], [], color='b')
model = SwarmModel(num_agents)
# model = Model(10 , Mode.swarm)
ani=animation.FuncAnimation(fig, update_plot_points, frames=3, fargs=(xdata,zdata,point, model))
plt.show(block=True)
ani.save('temp.mp4',fps = 100)
