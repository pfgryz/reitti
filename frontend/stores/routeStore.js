import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  formatDurationMinutes,
  hoursToMinutes,
  minutesToTimeString,
  parseOpeningHoursForDay,
  timeStringToMinutes
} from '../src/utils/time.js'

const START_OPENING_HOURS = { open: 0, close: 1440 }
const START_STAY = { min: 0, max: 0 }

function attractionToApi(place, { isStart = false, stayMin = 0, stayMax = 0, visitDay } = {}) {
  const opening_hours = isStart
    ? START_OPENING_HOURS
    : (() => {
        const oh = parseOpeningHoursForDay(place.hours, visitDay)
        if (!oh || oh.closed) return null
        return { open: oh.open, close: oh.close }
      })()

  if (!opening_hours) return null

  return {
    lat: place.lat,
    lon: place.lng,
    opening_hours,
    stay: isStart ? START_STAY : { min: hoursToMinutes(stayMin), max: hoursToMinutes(stayMax) },
    type: /muzeum|museum/i.test(place.name) ? 'museum' : 'other'
  }
}

function findClosedOnDay(places, visitDay) {
  return places.filter(p => parseOpeningHoursForDay(p.hours, visitDay)?.closed)
}

function buildOptimizeBody(startTime, endTime, startPoint, attractions, visitDay) {
  const start = attractionToApi(startPoint, { isStart: true, visitDay })
  const stops = attractions.map(a =>
    attractionToApi(a, { stayMin: a.stayMin, stayMax: a.stayMax, visitDay })
  )
  if (!start || stops.some(s => !s)) return null

  return {
    start_time: timeStringToMinutes(startTime),
    end_time: timeStringToMinutes(endTime),
    include_legs: true,
    attractions: [start, ...stops]
  }
}

function stitchPointSegments(segments) {
  const points = []
  for (const segment of segments) {
    if (!segment?.length) continue
    for (const [lat, lon] of segment) {
      const last = points[points.length - 1]
      if (!last || last[0] !== lat || last[1] !== lon) {
        points.push([lat, lon])
      }
    }
  }
  return points
}

function polylineFromOptimizeResponse(data) {
  if (data.legs?.length) {
    return stitchPointSegments(data.legs.map(leg => leg.points))
  }
  if (data.geometry?.length) return stitchPointSegments([data.geometry])
  if (data.points?.length) return stitchPointSegments([data.points])
  return null
}

function nameForAttractionIndex(index, startPoint, attractions) {
  if (index === 0) return startPoint.name
  return attractions[index - 1]?.name ?? `Miejsce ${index}`
}

function mapVisitsToOrder(visits, startPoint, attractions) {
  return (visits ?? []).map(v => ({
    name: nameForAttractionIndex(v.attraction_index, startPoint, attractions),
    arrival: minutesToTimeString(v.arrival_time),
    departure: minutesToTimeString(v.departure_time),
    stay: Math.round(v.stay_minutes ?? v.departure_time - v.arrival_time)
  }))
}

export const useRouteStore = defineStore('route', () => {
  const defaultHours = () => [
    { day: 1, label: 'Poniedziałek', time: '09:00 - 18:00' },
    { day: 2, label: 'Wtorek', time: '09:00 - 18:00' },
    { day: 3, label: 'Środa', time: '09:00 - 18:00' },
    { day: 4, label: 'Czwartek', time: '09:00 - 18:00' },
    { day: 5, label: 'Piątek', time: '09:00 - 20:00' },
    { day: 6, label: 'Sobota', time: '10:00 - 18:00' },
    { day: 0, label: 'Niedziela', time: '10:00 - 16:00' }
  ]

  const museumHours = () => [
    { day: 1, label: 'Poniedziałek', time: 'Zamknięte' },
    { day: 2, label: 'Wtorek', time: '10:00 - 18:00' },
    { day: 3, label: 'Środa', time: '10:00 - 20:00' },
    { day: 4, label: 'Czwartek', time: '10:00 - 18:00' },
    { day: 5, label: 'Piątek', time: '10:00 - 18:00' },
    { day: 6, label: 'Sobota', time: '11:00 - 17:00' },
    { day: 0, label: 'Niedziela', time: '11:00 - 17:00' }
  ]

  const open24h = () => [
    { day: 1, label: 'Poniedziałek', time: 'Czynne całą dobę' },
    { day: 2, label: 'Wtorek', time: 'Czynne całą dobę' },
    { day: 3, label: 'Środa', time: 'Czynne całą dobę' },
    { day: 4, label: 'Czwartek', time: 'Czynne całą dobę' },
    { day: 5, label: 'Piątek', time: 'Czynne całą dobę' },
    { day: 6, label: 'Sobota', time: 'Czynne całą dobę' },
    { day: 0, label: 'Niedziela', time: 'Czynne całą dobę' }
  ]

  const helsinkiPlaces = [
    { id: 0, name: 'Dworzec Główny, Helsinki', lat: 60.1718, lng: 24.9414, hours: open24h() },
    { id: 1, name: 'Katedra w Helsinkach', lat: 60.1704, lng: 24.9522, hours: defaultHours() },
    { id: 2, name: 'Plac Targowy (Kauppatori)', lat: 60.1676, lng: 24.9538, hours: defaultHours() },
    { id: 3, name: 'Kaplica Kamppi', lat: 60.1691, lng: 24.9365, hours: defaultHours() },
    { id: 4, name: 'Kościół w Skale (Temppeliaukio)', lat: 60.1730, lng: 24.9252, hours: defaultHours() },
    { id: 5, name: 'Twierdza Suomenlinna', lat: 60.1436, lng: 24.9844, hours: defaultHours() },
    { id: 6, name: 'Muzeum Narodowe Finlandii', lat: 60.1749, lng: 24.9314, hours: museumHours() },
    { id: 7, name: 'Park Sibeliusa', lat: 60.1821, lng: 24.9134, hours: open24h() },
    { id: 8, name: 'Sobór Uspieński', lat: 60.1683, lng: 24.9599, hours: museumHours() },
    { id: 9, name: 'Muzeum Kiasma', lat: 60.1717, lng: 24.9368, hours: museumHours() },
    { id: 10, name: 'Linnanmäki (Park rozrywki)', lat: 60.1882, lng: 24.9403, hours: defaultHours() },
    { id: 11, name: 'Heureka – centrum nauki, Vantaa', lat: 60.2940, lng: 25.0408, hours: museumHours() }
  ]

  const startPoint = ref({
    name: 'Dworzec Główny, Helsinki',
    lat: 60.1718,
    lng: 24.9414,
    hours: open24h()
  })
  const startTime = ref('09:00')
  const endTime = ref('18:00')
  const visitDay = ref(new Date().getDay())
  const attractions = ref([])

  const isRouteCalculated = ref(false)
  const isLoading = ref(false)
  const error = ref(null)
  const totalDuration = ref('')
  const visitOrder = ref([])
  const mapCenter = ref([60.1699, 24.9384])
  const routePolyline = ref([])

  const clearRouteResult = () => {
    isRouteCalculated.value = false
    routePolyline.value = []
    visitOrder.value = []
    totalDuration.value = ''
    error.value = null
  }

  const setVisitDay = (day) => {
    if (visitDay.value === day) return
    visitDay.value = day
    clearRouteResult()
  }

  const addAttraction = (attraction) => {
    attractions.value.push({ ...attraction, id: Date.now() })
    clearRouteResult()
  }

  const removeAttraction = (id) => {
    attractions.value = attractions.value.filter(a => a.id !== id)
    clearRouteResult()
  }

  const calculateRoute = async () => {
    isLoading.value = true
    error.value = null

    const closed = findClosedOnDay(attractions.value, visitDay.value)
    if (closed.length) {
      error.value = `Zamknięte w wybrany dzień: ${closed.map(p => p.name).join(', ')}`
      isLoading.value = false
      return
    }

    const body = buildOptimizeBody(
      startTime.value,
      endTime.value,
      startPoint.value,
      attractions.value,
      visitDay.value
    )
    if (!body) {
      error.value = 'Nie udało się odczytać godzin otwarcia wybranych miejsc.'
      isLoading.value = false
      return
    }

    try {
      const res = await fetch('/trip/optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })

      const data = await res.json().catch(() => ({}))

      if (!res.ok) {
        const detail = data.detail
        error.value = typeof detail === 'object' && detail?.message
          ? detail.message
          : typeof detail === 'string'
            ? detail
            : `Błąd serwera (${res.status})`
        return
      }

      isRouteCalculated.value = true
      visitOrder.value = mapVisitsToOrder(
        data.visits,
        startPoint.value,
        attractions.value
      )
      totalDuration.value = formatDurationMinutes(
        data.end_time - timeStringToMinutes(startTime.value)
      )

      routePolyline.value = polylineFromOptimizeResponse(data) ?? []
    } catch {
      error.value = 'Nie udało się połączyć z serwerem.'
    } finally {
      isLoading.value = false
    }
  }

  return {
    helsinkiPlaces, startPoint, startTime, endTime, visitDay, attractions,
    isRouteCalculated, isLoading, error, totalDuration, visitOrder, mapCenter, routePolyline,
    addAttraction, removeAttraction, clearRouteResult, setVisitDay, calculateRoute
  }
})