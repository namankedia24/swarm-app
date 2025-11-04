<template>
  <div class="app-shell">
    <header class="app-header">
      <h1>Swarm Navigation Simulator</h1>
      <p class="subtitle">Experiment with decentralized flocking behaviours in real time.</p>
    </header>

    <main class="app-main">
      <section class="controls-panel">
        <form @submit.prevent="startSimulation">
          <div class="control-group">
            <label for="numAgents">Agents</label>
            <input
              id="numAgents"
              type="number"
              min="1"
              max="500"
              v-model.number="form.numAgents"
              required
            />
          </div>

          <div class="control-group">
            <label for="mode">Mode</label>
            <select id="mode" v-model="form.mode">
              <option value="swarm">Swarm</option>
              <option value="torus">Torus</option>
              <option value="hpp">Hard-Packed</option>
              <option value="dpp">Density-Aware</option>
            </select>
          </div>

          <div class="control-group">
            <label for="timestep">Timestep (Δt)</label>
            <input
              id="timestep"
              type="number"
              min="0.01"
              step="0.01"
              v-model.number="form.timestep"
              required
            />
          </div>

          <div class="control-group">
            <label for="updateInterval">Update Interval (s)</label>
            <input
              id="updateInterval"
              type="number"
              min="0.01"
              step="0.01"
              v-model.number="form.updateInterval"
              required
            />
          </div>

          <div class="buttons-row">
            <button class="primary-btn" type="submit" :disabled="startDisabled">
              {{ status === 'starting' ? 'Connecting…' : status === 'running' ? 'Streaming' : 'Launch' }}
            </button>
            <button class="secondary-btn" type="button" @click="stopSimulation" :disabled="stopDisabled">
              Stop
            </button>
          </div>
        </form>

        <div class="status-card">
          <span class="status-label">Simulation Status</span>
          <span :class="['status-value-' + statusClass]">{{ statusText }}</span>
          <span class="status-label">Tick</span>
          <span>{{ tick }}</span>
          <span class="status-label">Agent Count</span>
          <span>{{ agentsCount }}</span>
        </div>

        <div v-if="errorMessage" class="error-banner">
          {{ errorMessage }}
        </div>
      </section>

      <section class="simulation-panel">
        <SimulationCanvas :agents="agents" />
      </section>
    </main>
  </div>
</template>

<script setup>
import { reactive, computed, onBeforeUnmount } from 'vue';
import { storeToRefs } from 'pinia';
import SimulationCanvas from './components/SimulationCanvas.vue';
import { useSimulationStore } from './stores/simulationStore';

const simulationStore = useSimulationStore();
const { agents, status, tick, errorMessage } = storeToRefs(simulationStore);

const form = reactive({
  numAgents: 30,
  mode: 'hpp',
  timestep: 1,
  updateInterval: 0.1,
});

const startDisabled = computed(() => status.value === 'starting' || status.value === 'running');
const stopDisabled = computed(() => status.value === 'idle');
const statusClass = computed(() => status.value || 'idle');
const statusText = computed(() => {
  switch (status.value) {
    case 'starting':
      return 'Starting';
    case 'running':
      return 'Running';
    case 'stopping':
      return 'Stopping';
    case 'error':
      return 'Error';
    default:
      return 'Idle';
  }
});

const agentsCount = computed(() => agents.value.length);

const startSimulation = async () => {
  try {
    await simulationStore.startSimulation(form);
  } catch (error) {
    console.error('Failed to start simulation', error);
  }
};

const stopSimulation = async () => {
  await simulationStore.stopSimulation();
};

onBeforeUnmount(() => {
  simulationStore.stopSimulation();
});
</script>

<style scoped>
.subtitle {
  margin: 0.45rem 0 0;
  font-size: 0.95rem;
  color: rgba(203, 212, 255, 0.7);
}
</style>
