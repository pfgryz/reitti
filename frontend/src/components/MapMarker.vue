<template>
  <div class="map-marker" :class="{ 'map-marker--bus': kind === 'bus' }">
    <Bus v-if="kind === 'bus'" :size="22" color="#ea580c" :stroke-width="2.5" />
    <MapPin v-else :size="32" :color="color" :stroke-width="2.5" fill="white" />
    <span v-if="n != null" class="map-marker__n" :style="{ background: badge }">{{ n }}</span>
  </div>
</template>

<script setup>
import { Bus, MapPin } from 'lucide-vue-next'

defineProps({
  kind: { type: String, default: 'pin' },
  n: { type: [Number, String], default: null },
  color: { type: String, default: '#2563eb' },
  badge: { type: String, default: '#1e40af' }
})
</script>

<style>
.map-marker {
  position: relative;
  width: 32px;
  height: 40px;
  line-height: 0;
}

.map-marker--bus {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border: 2px solid #ea580c;
  border-radius: 50%;
  box-shadow: 0 1px 4px rgb(0 0 0 / 0.2);
}

.map-marker__n {
  position: absolute;
  top: 4px;
  left: 50%;
  transform: translateX(-50%);
  min-width: 16px;
  padding: 0 4px;
  font-size: 11px;
  font-weight: 700;
  line-height: 16px;
  text-align: center;
  color: #fff;
  border-radius: 8px;
  border: 1.5px solid #fff;
}
</style>
