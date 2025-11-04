import { defineStore } from 'pinia';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
const WS_BASE = import.meta.env.VITE_WS_BASE || 'ws://localhost:8000';

export const useSimulationStore = defineStore('simulation', {
  state: () => ({
    simulationId: null,
    agents: [],
    tick: 0,
    status: 'idle',
    errorMessage: null,
    socket: null,
  }),
  actions: {
    async startSimulation({ numAgents, mode, timestep, updateInterval }) {
      if (this.status === 'running' || this.status === 'starting') {
        return;
      }

      await this.stopSimulation();
      this.status = 'starting';
      this.errorMessage = null;
      try {
        const response = await fetch(`${API_BASE}/api/simulations`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            num_agents: numAgents,
            mode,
            timestep,
            update_interval: updateInterval,
          }),
        });

        if (!response.ok) {
          const message = await response.text();
          throw new Error(message || 'Failed to create simulation');
        }
        const payload = await response.json();
        this.simulationId = payload.simulation_id;
        this.tick = 0;
        this.agents = [];
        this._connectSocket();
      } catch (error) {
        this.status = 'error';
        this.errorMessage = error.message;
        throw error;
      }
    },
    _connectSocket() {
      if (!this.simulationId) {
        return;
      }

      const socket = new WebSocket(`${WS_BASE}/ws/simulations/${this.simulationId}`);
      this.socket = socket;

      socket.onopen = () => {
        this.status = 'running';
      };

      socket.onerror = () => {
        this.errorMessage = 'WebSocket connection failed';
        this.status = 'error';
      };

      socket.onclose = () => {
        if (this.status !== 'stopping') {
          this.status = 'idle';
        }
        this.socket = null;
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          switch (data.type) {
            case 'snapshot':
            case 'tick':
              this.tick = data.tick;
              this.agents = data.agents;
              break;
            case 'shutdown':
              this.status = 'idle';
              this.agents = [];
              this.simulationId = null;
              break;
            case 'error':
              this.status = 'error';
              this.errorMessage = data.message || 'Simulation error';
              break;
            default:
              break;
          }
        } catch (err) {
          console.error('Failed to parse socket message', err);
        }
      };
    },
    async stopSimulation() {
      if (this.status === 'idle' && !this.simulationId) {
        return;
      }

      this.status = 'stopping';
      if (this.socket) {
        try {
          this.socket.close(1000, 'Client closed connection');
        } catch (error) {
          console.warn('Error closing websocket', error);
        }
        this.socket = null;
      }

      if (this.simulationId) {
        try {
          await fetch(`${API_BASE}/api/simulations/${this.simulationId}`, {
            method: 'DELETE',
          });
        } catch (error) {
          console.warn('Failed to stop simulation', error);
        }
      }

      this.simulationId = null;
      this.agents = [];
      this.tick = 0;
      this.status = 'idle';
    },
  },
});
