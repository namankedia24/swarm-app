<template>
  <div ref="container" class="simulation-canvas"></div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, watch, ref } from 'vue';
import * as THREE from 'three';

const props = defineProps({
  agents: {
    type: Array,
    default: () => [],
  },
});

const container = ref(null);
let renderer;
let scene;
let camera;
let animationId;
const meshes = new Map();

const agentGeometry = new THREE.ConeGeometry(0.6, 1.5, 12);
const agentMaterial = new THREE.MeshStandardMaterial({
  color: 0x4cc4ff,
  emissive: 0x0,
  metalness: 0.1,
  roughness: 0.45,
  flatShading: true,
});

const ensureRendererDimensions = () => {
  if (!container.value || !renderer) {
    return;
  }
  const width = container.value.clientWidth || 1;
  const height = container.value.clientHeight || 1;
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height);
};

const updateAgents = (agents) => {
  if (!scene) return;

  const activeIds = new Set();
  agents.forEach((agent) => {
    const { id, position, velocity } = agent;
    let mesh = meshes.get(id);
    if (!mesh) {
      mesh = new THREE.Mesh(agentGeometry.clone(), agentMaterial.clone());
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      scene.add(mesh);
      meshes.set(id, mesh);
    }

    mesh.position.set(position[0], position[1], position[2]);

    if (velocity) {
      const direction = new THREE.Vector3(velocity[0], velocity[1], velocity[2]);
      if (direction.lengthSq() > 1e-6) {
        direction.normalize();
        const axis = new THREE.Vector3(0, 1, 0);
        const quaternion = new THREE.Quaternion().setFromUnitVectors(axis, direction);
        mesh.setRotationFromQuaternion(quaternion);
      }
    }

    activeIds.add(id);
  });

  meshes.forEach((mesh, id) => {
    if (!activeIds.has(id)) {
      scene.remove(mesh);
      mesh.geometry.dispose();
      mesh.material.dispose();
      meshes.delete(id);
    }
  });
};

const animate = () => {
  animationId = requestAnimationFrame(animate);
  renderer.render(scene, camera);
};

const onResize = () => {
  ensureRendererDimensions();
};

watch(
  () => props.agents,
  (agents) => updateAgents(agents),
  { deep: true }
);

onMounted(() => {
  scene = new THREE.Scene();
  scene.background = new THREE.Color('#050b1b');

  camera = new THREE.PerspectiveCamera(60, 1, 0.1, 500);
  camera.position.set(0, 30, 60);
  camera.lookAt(0, 0, 0);

  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.shadowMap.enabled = true;
  renderer.setPixelRatio(window.devicePixelRatio);

  if (container.value) {
    container.value.appendChild(renderer.domElement);
  }

  const ambientLight = new THREE.AmbientLight(0x8faaff, 0.35);
  scene.add(ambientLight);

  const keyLight = new THREE.DirectionalLight(0xffffff, 0.65);
  keyLight.position.set(50, 60, 25);
  keyLight.castShadow = true;
  scene.add(keyLight);

  const fillLight = new THREE.PointLight(0x0095ff, 0.35, 200);
  fillLight.position.set(-40, 20, -30);
  scene.add(fillLight);

  const grid = new THREE.GridHelper(180, 18, 0x1f2d63, 0x14204a);
  grid.position.y = -5;
  scene.add(grid);

  ensureRendererDimensions();
  window.addEventListener('resize', onResize);
  animate();
});

onBeforeUnmount(() => {
  cancelAnimationFrame(animationId);
  window.removeEventListener('resize', onResize);

  meshes.forEach((mesh) => {
    scene.remove(mesh);
    mesh.geometry.dispose();
    mesh.material.dispose();
  });
  meshes.clear();

  if (renderer) {
    renderer.dispose();
  }
});
</script>

<style scoped>
.simulation-canvas {
  width: 100%;
  height: 100%;
}
</style>
