<template>
  <div class="layout">
    <aside class="sidebar">
      <header class="app-header">
        <MapIcon class="text-primary icon-xl" />
        <h2>Reitti</h2>
      </header>

      <section class="card">
        <h3 class="section-title"><Settings class="icon-sm" />Definicja wycieczki</h3>

        <div class="input-group">
          <label><Flag class="icon-xs text-muted" /> Punkt startowy:</label>
          <div class="autocomplete-container">
            <input
              type="text"
              v-model="startSearch"
              placeholder="Wpisz punkt startowy..."
              class="modern-input"
            />
            <ul class="suggestions-list" v-if="filteredStartPlaces.length > 0">
              <li
                v-for="place in filteredStartPlaces"
                :key="'start-' + place.id"
                @click="selectStartPlace(place)"
              >
                <MapPin class="icon-xs text-muted" /> {{ place.name }}
              </li>
            </ul>
          </div>
        </div>

        <div class="time-row mt-2">
          <div class="input-group">
            <label><Clock class="icon-xs text-muted" /> Godzina rozpoczęcia:</label>
            <input type="time" v-model="store.startTime" class="modern-input" />
          </div>
          <div class="input-group">
            <label><Clock class="icon-xs text-muted" /> Godzina zakończenia:</label>
            <input type="time" v-model="store.endTime" class="modern-input" />
          </div>
        </div>

        <div class="input-group mt-2">
          <label><Calendar class="icon-xs text-muted" /> Dzień wycieczki:</label>
          <select
            class="modern-input"
            :value="store.visitDay"
            @change="store.setVisitDay(Number($event.target.value))"
          >
            <option v-for="d in weekdays" :key="d.day" :value="d.day">{{ d.label }}</option>
          </select>
          <span class="text-sm text-muted">Wybrany dzień: {{ selectedDayLabel }}</span>
        </div>
      </section>

      <section class="card">
        <h3 class="section-title"><MapPinPlus class="icon-sm" />Dodaj miejsce</h3>

        <div class="autocomplete-container">
          <input
              type="text"
              v-model="newAttraction.name"
              placeholder="Zacznij wpisywać nazwę miejsca..."
              class="modern-input"
          />
          <ul class="suggestions-list" v-if="filteredPlaces.length > 0">
            <li
                v-for="place in filteredPlaces"
                :key="place.id"
                @click="selectPlace(place.name)"
            >
              <MapPin class="icon-xs text-muted" /> {{ place.name }}
            </li>
          </ul>
        </div>

        <div v-if="previewPlace" class="opening-hours-container mt-2">
          <div class="hours-title"><Calendar class="icon-xs" /> Godziny otwarcia</div>
          <ul class="hours-list">
            <li
              v-for="h in previewPlace.hours"
              :key="h.day"
              class="hours-item"
              :class="{ 'is-selected': h.day === store.visitDay }"
            >
              <span class="day-name">{{ h.label }}</span>
              <span class="day-time">{{ h.time }}</span>
            </li>
          </ul>
        </div>

        <div class="time-row mt-2">
          <div class="input-group">
            <label><Clock class="icon-xs text-muted" /> Czas od (h):</label>
            <input type="number" step="0.5" min="0" v-model="newAttraction.stayMin" class="modern-input" />
          </div>
          <div class="input-group">
            <label><Clock class="icon-xs text-muted" /> Czas do (h):</label>
            <input type="number" step="0.5" min="0" v-model="newAttraction.stayMax" class="modern-input" />
          </div>
        </div>

        <button class="btn btn-secondary mt-3" @click="handleAddAttraction">
          <Plus class="icon-sm" /> Dodaj do listy
        </button>
      </section>

      <section class="card" v-if="store.attractions.length">
        <h3 class="section-title"><List class="icon-sm" /> Wybrane miejsca ({{ store.attractions.length }})</h3>
        <ul class="attraction-list">
          <li v-for="item in store.attractions" :key="item.id" class="attraction-item">
            <div class="attraction-info">
              <strong>{{ item.name }}</strong>
              <span class="text-sm text-muted"><Clock class="icon-xs" /> {{ item.stayMin }} - {{ item.stayMax }}h</span>
            </div>
            <button class="btn-icon btn-danger" @click="store.removeAttraction(item.id)" title="Usuń">
              <Trash2 class="icon-sm" />
            </button>
          </li>
        </ul>
      </section>

      <div class="spacer"></div>

      <button
        class="btn btn-primary btn-large"
        @click="store.calculateRoute"
        :disabled="!store.attractions.length || store.isLoading"
      >
        <Navigation class="icon-sm" />
        {{ store.isLoading ? 'Obliczanie…' : 'Wyznacz optymalną trasę' }}
      </button>

      <section class="card error-panel" v-if="store.error">
        <h3 class="section-title text-danger">Błąd</h3>
        <p class="text-sm">{{ store.error }}</p>
      </section>

      <section class="card results" v-if="store.isRouteCalculated">
        <h3 class="section-title text-success"><CheckCircle2 class="icon-sm text-success" /> Sukces</h3>
        <p class="text-sm"><strong>Czas wycieczki:</strong> {{ store.totalDuration }}</p>
        <h4 class="results-subtitle">Kolejność odwiedzin</h4>
        <ol class="visit-order-list">
          <li v-for="(visit, index) in store.visitOrder" :key="index" class="visit-order-item">
            <strong>{{ visit.name }}</strong>
            <span class="text-sm text-muted">
              {{ visit.arrival }} – {{ visit.departure }}, pobyt {{ visit.stay }} min
            </span>
          </li>
        </ol>
        <p class="text-sm text-muted mt-2">Trasa została zaktualizowana na mapie.</p>
      </section>
    </aside>

    <main class="map-container">
      <l-map ref="map" :zoom="13" :center="store.mapCenter">
        <l-tile-layer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" layer-type="base" name="OpenStreetMap"></l-tile-layer>

        <l-marker
          v-for="place in availablePlaces"
          :key="'avail-' + place.id"
          :lat-lng="[place.lat, place.lng]"
        >
          <l-tooltip>Dostępne: {{ place.name }}</l-tooltip>
          <l-popup>
            <div class="map-popup">
              <h4>{{ place.name }}</h4>
              <template v-if="place.hours">
                <p class="popup-subtitle">Godziny otwarcia</p>
                <ul class="popup-hours">
                  <li v-for="h in place.hours" :key="h.day" :class="{ 'is-selected': h.day === store.visitDay }">
                    <span>{{ h.label }}</span><span>{{ h.time }}</span>
                  </li>
                </ul>
              </template>
            </div>
          </l-popup>
        </l-marker>

        <l-marker v-if="store.startPoint && store.startPoint.lat" :lat-lng="[store.startPoint.lat, store.startPoint.lng]">
          <l-icon
            icon-url="https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png"
            shadow-url="https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png"
            :icon-size="[25, 41]" :icon-anchor="[12, 41]" :popup-anchor="[1, -34]" :shadow-size="[41, 41]"
          />
          <l-tooltip>Start: {{ store.startPoint.name }}</l-tooltip>
          <l-popup>
            <div class="map-popup">
              <h4>🏁 {{ store.startPoint.name }} (START)</h4>
              <template v-if="store.startPoint.hours">
                <p class="popup-subtitle">Godziny otwarcia</p>
                <ul class="popup-hours">
                  <li v-for="h in store.startPoint.hours" :key="h.day" :class="{ 'is-selected': h.day === store.visitDay }">
                    <span>{{ h.label }}</span><span>{{ h.time }}</span>
                  </li>
                </ul>
              </template>
            </div>
          </l-popup>
        </l-marker>

        <l-marker v-for="item in store.attractions" :key="'selected-' + item.id" :lat-lng="[item.lat, item.lng]">
          <l-icon
            icon-url="https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png"
            shadow-url="https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png"
            :icon-size="[25, 41]" :icon-anchor="[12, 41]" :popup-anchor="[1, -34]" :shadow-size="[41, 41]"
          />
          <l-tooltip>Wybrane: {{ item.name }}</l-tooltip>
          <l-popup>
            <div class="map-popup">
              <h4>{{ item.name }}</h4>
              <template v-if="item.hours">
                <p class="popup-subtitle">Godziny otwarcia</p>
                <ul class="popup-hours">
                  <li v-for="h in item.hours" :key="h.day" :class="{ 'is-selected': h.day === store.visitDay }">
                    <span>{{ h.label }}</span><span>{{ h.time }}</span>
                  </li>
                </ul>
              </template>
            </div>
          </l-popup>
        </l-marker>

        <l-marker v-if="previewPlace" :lat-lng="[previewPlace.lat, previewPlace.lng]" :opacity="0.5">
          <l-tooltip>Podgląd: {{ previewPlace.name }}</l-tooltip>
        </l-marker>

        <l-polyline
          v-if="store.routePolyline.length"
          :lat-lngs="store.routePolyline"
          color="#3b82f6"
          :weight="5"
        ></l-polyline>
      </l-map>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick } from 'vue'
import { useRouteStore } from '../stores/routeStore'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { LMap, LTileLayer, LMarker, LTooltip, LPolyline, LPopup, LIcon } from '@vue-leaflet/vue-leaflet'

import {
  Map as MapIcon, MapPin, Clock, Flag, Calendar,
  Plus, Trash2, Navigation, Settings,
  List, CheckCircle2, MapPinPlus
} from 'lucide-vue-next'

const weekdays = [
  { day: 1, label: 'Poniedziałek' },
  { day: 2, label: 'Wtorek' },
  { day: 3, label: 'Środa' },
  { day: 4, label: 'Czwartek' },
  { day: 5, label: 'Piątek' },
  { day: 6, label: 'Sobota' },
  { day: 0, label: 'Niedziela' }
]

const store = useRouteStore()

const selectedDayLabel = computed(() =>
  weekdays.find(d => d.day === store.visitDay)?.label ?? ''
)
const map = ref(null)

watch(
  () => store.routePolyline,
  async (points) => {
    if (!points.length) return
    await nextTick()
    const leafletMap = map.value?.leafletObject
    if (!leafletMap) return
    leafletMap.fitBounds(L.latLngBounds(points), { padding: [32, 32] })
  }
)

const startSearch = ref(store.startPoint.name)

const availablePlaces = computed(() => {
  if (store.isRouteCalculated) return []

  return store.helsinkiPlaces.filter(p => {
    const isStart = store.startPoint && store.startPoint.lat === p.lat && store.startPoint.lng === p.lng
    const isSelected = store.attractions.some(a => a.lat === p.lat && a.lng === p.lng)

    return !isStart && !isSelected
  })
})

const filteredStartPlaces = computed(() => {
  const query = startSearch.value.toLowerCase()
  if (!query) return []
  return store.helsinkiPlaces.filter(p => p.name.toLowerCase().includes(query) && p.name !== startSearch.value)
})

const selectStartPlace = (place) => {
  startSearch.value = place.name
  store.startPoint = { name: place.name, lat: place.lat, lng: place.lng, hours: place.hours }
  store.clearRouteResult()
}

const newAttraction = reactive({
  name: '',
  stayMin: 1,
  stayMax: 2
})

const filteredPlaces = computed(() => {
  const query = newAttraction.name.toLowerCase()
  if (!query) return []
  return store.helsinkiPlaces.filter(p => p.name.toLowerCase().includes(query) && p.name !== newAttraction.name)
})

const selectPlace = (placeName) => {
  newAttraction.name = placeName
}

const previewPlace = computed(() => {
  if (!newAttraction.name) return null
  return store.helsinkiPlaces.find(p => p.name === newAttraction.name) || null
})

const handleAddAttraction = () => {
  const foundPlace = store.helsinkiPlaces.find(p => p.name === newAttraction.name)
  if (!foundPlace) {
    alert('Proszę wybrać poprawne miejsce z listy podpowiedzi!')
    return
  }
  store.addAttraction({
    ...newAttraction,
    lat: foundPlace.lat,
    lng: foundPlace.lng,
    hours: foundPlace.hours
  })
  newAttraction.name = ''
  newAttraction.stayMin = 1
  newAttraction.stayMax = 2
}
</script>

<style>
:root {
  --primary: #2563eb;
  --primary-hover: #1d4ed8;
  --secondary: #f1f5f9;
  --secondary-hover: #e2e8f0;
  --danger: #ef4444;
  --danger-hover: #dc2626;
  --success: #16a34a;
  --success-bg: #dcfce7;

  --bg-app: #f8fafc;
  --bg-card: #ffffff;

  --text-main: #0f172a;
  --text-muted: #64748b;
  --border-color: #cbd5e1;

  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;

  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
}

* { box-sizing: border-box; font-family: 'Inter', system-ui, -apple-system, sans-serif; }
body, html, #app { margin: 0; padding: 0; width: 100%; height: 100%; }

.layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  background-color: var(--bg-app);
}

.sidebar {
  width: 420px;
  min-width: 420px;
  background-color: var(--bg-app);
  padding: 24px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
  border-right: 1px solid var(--border-color);
  box-shadow: var(--shadow-sm);
  z-index: 10;
}

.map-container { flex: 1; height: 100%; z-index: 1; }
.spacer { flex-grow: 1; }

.app-header { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.app-header h2 { margin: 0; color: var(--text-main); font-size: 1.5rem; font-weight: 700; letter-spacing: -0.5px; }

.card {
  background: var(--bg-card);
  padding: 20px;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  border: 1px solid rgba(0,0,0,0.05);
}

.section-title {
  display: flex; align-items: center; gap: 8px;
  font-size: 1rem; font-weight: 600; color: var(--text-main);
  margin: 0 0 16px 0; padding-bottom: 12px; border-bottom: 1px solid var(--secondary);
}

.input-group { display: flex; flex-direction: column; gap: 6px; flex: 1; }
label { display: flex; align-items: center; gap: 6px; font-size: 0.85rem; font-weight: 500; color: var(--text-muted); }

.time-row { display: flex; gap: 16px; }
.mt-2 { margin-top: 12px; }
.mt-3 { margin-top: 16px; }

.modern-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  font-size: 0.95rem;
  color: var(--text-main);
  background-color: #fff;
  transition: all 0.2s ease;
}
.modern-input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}

.btn {
  display: inline-flex; justify-content: center; align-items: center; gap: 8px;
  padding: 10px 16px; border: none; border-radius: var(--radius-sm);
  font-weight: 600; font-size: 0.95rem; cursor: pointer; transition: all 0.2s ease;
}
.btn-secondary { background-color: var(--secondary); color: var(--text-main); }
.btn-secondary:hover { background-color: var(--secondary-hover); }

.btn-primary { background-color: var(--primary); color: white; box-shadow: var(--shadow-md); }
.btn-primary:hover:not(:disabled) { background-color: var(--primary-hover); transform: translateY(-1px); }
.btn-primary:disabled { background-color: var(--text-muted); opacity: 0.6; cursor: not-allowed; box-shadow: none; }
.btn-large { padding: 14px 20px; font-size: 1.05rem; border-radius: var(--radius-md); }

.btn-icon {
  display: flex; justify-content: center; align-items: center;
  width: 32px; height: 32px; border: none; border-radius: var(--radius-sm);
  cursor: pointer; transition: 0.2s;
}
.btn-danger { background-color: #fee2e2; color: var(--danger); }
.btn-danger:hover { background-color: var(--danger); color: white; }

.attraction-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 10px; }
.attraction-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px; background: var(--bg-app); border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
}
.attraction-info { display: flex; flex-direction: column; gap: 4px; }
.text-sm { font-size: 0.85rem; }
.text-muted { color: var(--text-muted); }

.results { background-color: var(--success-bg); border-color: #bbf7d0; }
.results-subtitle {
  margin: 12px 0 8px;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-main);
}
.visit-order-list {
  margin: 0;
  padding-left: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.visit-order-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.error-panel { background-color: #fee2e2; border-color: #fecaca; }
.text-success { color: var(--success); }
.text-danger { color: var(--danger); }

.autocomplete-container { position: relative; width: 100%; }
.suggestions-list {
  position: absolute; top: calc(100% + 4px); left: 0; right: 0;
  background: white; border: 1px solid var(--border-color);
  border-radius: var(--radius-sm); list-style: none; padding: 4px; margin: 0;
  max-height: 200px; overflow-y: auto; z-index: 1000;
  box-shadow: var(--shadow-md);
}
.suggestions-list li {
  display: flex; align-items: center; gap: 8px;
  padding: 10px; cursor: pointer; font-size: 0.9rem; color: var(--text-main);
  border-radius: 4px;
}
.suggestions-list li:hover { background-color: var(--secondary); color: var(--primary); }

.icon-xs { width: 14px; height: 14px; }
.icon-sm { width: 18px; height: 18px; }
.icon-lg { width: 24px; height: 24px; }
.icon-xl { width: 32px; height: 32px; }
.text-primary { color: var(--primary); }

.opening-hours-container {
  background: var(--secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 12px;
  font-size: 0.85rem;
  animation: fadeIn 0.3s ease;
}

.hours-title {
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 8px;
}

.hours-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.hours-item {
  display: flex;
  justify-content: space-between;
  color: var(--text-muted);
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.hours-item.is-selected {
  background: var(--primary);
  color: white;
  font-weight: 600;
  box-shadow: var(--shadow-sm);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-5px); }
  to { opacity: 1; transform: translateY(0); }
}

.map-popup h4 {
  margin: 0 0 6px 0;
  font-size: 1rem;
  color: var(--text-main);
  text-align: center;
}
.popup-subtitle {
  margin: 0 0 6px 0;
  font-size: 0.8rem;
  color: var(--text-muted);
  font-weight: 600;
  text-align: center;
}
.popup-hours {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: 0.85rem;
  min-width: 240px;
}
.popup-hours li {
  display: flex;
  justify-content: space-between;
  padding: 2px 4px;
  border-radius: 3px;
}
.popup-hours li.is-selected {
  background-color: var(--primary);
  color: white;
  font-weight: 600;
}
</style>