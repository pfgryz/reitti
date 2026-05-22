import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useRouteStore = defineStore('route', () => {
  const helsinkiPlaces = [
    { id: 0, name: 'Dworzec Główny, Helsinki', lat: 60.1718, lng: 24.9414 },
    { id: 1, name: 'Katedra w Helsinkach', lat: 60.1704, lng: 24.9522 },
    { id: 2, name: 'Plac Targowy (Kauppatori)', lat: 60.1676, lng: 24.9538 },
    { id: 3, name: 'Kaplica Kamppi', lat: 60.1691, lng: 24.9365 },
    { id: 4, name: 'Kościół w Skale (Temppeliaukio)', lat: 60.1730, lng: 24.9252 },
    { id: 5, name: 'Twierdza Suomenlinna', lat: 60.1436, lng: 24.9844 },
    { id: 6, name: 'Muzeum Narodowe Finlandii', lat: 60.1749, lng: 24.9314 },
    { id: 7, name: 'Park Sibeliusa', lat: 60.1821, lng: 24.9134 },
    { id: 8, name: 'Sobór Uspieński', lat: 60.1683, lng: 24.9599 },
    { id: 9, name: 'Muzeum Kiasma', lat: 60.1717, lng: 24.9368 },
    { id: 10, name: 'Linnanmäki (Park rozrywki)', lat: 60.1882, lng: 24.9403 }
  ]

  const startPoint = ref({ name: 'Dworzec Główny, Helsinki', lat: 60.1718, lng: 24.9414 })
  const startTime = ref('09:00')
  const endTime = ref('18:00')
  const attractions = ref([])

  const isRouteCalculated = ref(false)
  const totalDuration = ref('')
  const mapCenter = ref([60.1699, 24.9384])
  const routePolyline = ref([])

  const addAttraction = (attraction) => {
    attractions.value.push({ ...attraction, id: Date.now() })
    isRouteCalculated.value = false
    routePolyline.value = []
  }

  const removeAttraction = (id) => {
    attractions.value = attractions.value.filter(a => a.id !== id)
    isRouteCalculated.value = false
    routePolyline.value = []
  }

  const calculateRoute = () => {
    isRouteCalculated.value = true
    totalDuration.value = 'Czas obliczony na podstawie punktów'

    const points = [
      [startPoint.value.lat, startPoint.value.lng],
      ...attractions.value.map(a => [a.lat, a.lng])
    ]

    routePolyline.value = points
  }

  return {
    helsinkiPlaces, startPoint, startTime, endTime, attractions,
    isRouteCalculated, totalDuration, mapCenter, routePolyline,
    addAttraction, removeAttraction, calculateRoute
  }
})