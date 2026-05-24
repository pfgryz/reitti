import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  formatDurationMinutes,
  hoursToMinutes,
  minutesToTimeString,
  parseOpeningHoursForDay,
  narrowOpeningHours,
  timeStringToMinutes
} from '../src/utils/time.js'
import { formatDistanceMeters } from '../src/utils/distance.js'

function segmentsFromLeg(leg) {
  if (leg.mode !== 'public_transport') {
    return leg.points?.length >= 2 ? [{ mode: 'foot', points: leg.points }] : []
  }
  const segments = []
  if (leg.walk_to?.length >= 2) segments.push({ mode: 'foot', points: leg.walk_to })
  if (leg.from_stop && leg.to_stop) {
    const from = [leg.from_stop.lat, leg.from_stop.lon]
    const to = [leg.to_stop.lat, leg.to_stop.lon]
    segments.push({
      mode: 'public_transport',
      points: [from, to],
      bus: { from, to, fromName: leg.from_stop.name, toName: leg.to_stop.name }
    })
  }
  if (leg.walk_from?.length >= 2) segments.push({ mode: 'foot', points: leg.walk_from })
  return segments
}

const START_OPENING_HOURS = { open: 0, close: 1440 }
const START_STAY = { min: 0, max: 0 }

function attractionToApi(place, { isStart = false, stayMin = 0, stayMax = 0, visitDay } = {}) {
  const opening_hours = isStart
    ? START_OPENING_HOURS
    : (() => {
        const oh = parseOpeningHoursForDay(place.hours, visitDay)
        if (!oh || oh.closed) return null
        return narrowOpeningHours(oh, place.visitFrom, place.visitTo)
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

function findInvalidVisitWindow(places, visitDay) {
  return places.filter(p => {
    if (!p.visitFrom || !p.visitTo) return false
    const oh = parseOpeningHoursForDay(p.hours, visitDay)
    return !oh || oh.closed || !narrowOpeningHours(oh, p.visitFrom, p.visitTo)
  })
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

function legPointLists(leg) {
  if (leg.mode === 'public_transport') {
    return [leg.walk_to, leg.walk_from].filter(points => points?.length)
  }
  return leg.points?.length ? [leg.points] : []
}

function polylineFromOptimizeResponse(data) {
  if (data.legs?.length) {
    return stitchPointSegments(data.legs.flatMap(legPointLists))
  }
  if (data.geometry?.length) return stitchPointSegments([data.geometry])
  if (data.points?.length) return stitchPointSegments([data.points])
  return null
}

function routeSegmentsFromResponse(data) {
  if (!data.legs?.length) {
    const points = polylineFromOptimizeResponse(data)
    return points ? [{ mode: 'foot', points }] : []
  }
  return data.legs.flatMap(leg => segmentsFromLeg(leg))
}

function nameForAttractionIndex(index, startPoint, attractions) {
  if (index === 0) return startPoint.name
  return attractions[index - 1]?.name ?? `Miejsce ${index}`
}

function coordsForIndex(index, startPoint, attractions) {
  if (index === 0) return { lat: startPoint.lat, lng: startPoint.lng }
  const a = attractions[index - 1]
  return a ? { lat: a.lat, lng: a.lng } : null
}

function totalWaitMinutes(visits, legs, startTimeMinutes) {
  let total = 0
  let prevDep = startTimeMinutes
  for (let i = 0; i < visits.length; i++) {
    const travel = legs?.[i]?.travel_time ?? 0
    total += Math.max(0, visits[i].arrival_time - prevDep - travel)
    prevDep = visits[i].departure_time
  }
  return Math.round(total)
}

function mapVisitsToOrder(visits, legs, startTimeMinutes, startPoint, attractions) {
  let prevDep = startTimeMinutes
  return (visits ?? []).map((v, i) => {
    const travel = Math.round(legs?.[i]?.travel_time ?? 0)
    const rawArrivalMinutes = prevDep + travel
    const wait = Math.max(0, Math.round(v.arrival_time - rawArrivalMinutes))
    const stay = Math.round(v.stay_minutes ?? v.departure_time - v.arrival_time)
    prevDep = v.departure_time

    const coords = coordsForIndex(v.attraction_index, startPoint, attractions)
    return {
      order: i + 1,
      name: nameForAttractionIndex(v.attraction_index, startPoint, attractions),
      lat: coords?.lat,
      lng: coords?.lng,
      travel,
      wait,
      rawArrival: minutesToTimeString(rawArrivalMinutes),
      arrival: minutesToTimeString(v.arrival_time),
      departure: minutesToTimeString(v.departure_time),
      stay
    }
  })
}

function defaultStart(places) {
  return places.find(p => /central station/i.test(p.name)) ?? places[0]
}

export const useRouteStore = defineStore('route', () => {
  const helsinkiPlaces = ref([])
  const placesError = ref(null)

  const startPoint = ref({ name: '', lat: 60.1699, lng: 24.9384, hours: [] })
  const startTime = ref('09:00')
  const endTime = ref('18:00')
  const visitDay = ref(new Date().getDay())
  const attractions = ref([])

  const isRouteCalculated = ref(false)
  const isLoading = ref(false)
  const error = ref(null)
  const totalDuration = ref('')
  const totalTravelTime = ref('')
  const totalWaitTime = ref('')
  const totalWalkDistance = ref('')
  const visitOrder = ref([])
  const mapCenter = ref([60.1699, 24.9384])
  const routePolyline = ref([])
  const routeSegments = ref([])

  const clearRouteResult = () => {
    isRouteCalculated.value = false
    routePolyline.value = []
    routeSegments.value = []
    visitOrder.value = []
    totalDuration.value = ''
    totalTravelTime.value = ''
    totalWaitTime.value = ''
    totalWalkDistance.value = ''
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

  const updateAttraction = (id, patch) => {
    const item = attractions.value.find(a => a.id === id)
    if (!item) return
    Object.assign(item, patch)
    clearRouteResult()
  }

  const loadPlaces = async () => {
    placesError.value = null
    try {
      const res = await fetch('/places')
      const data = await res.json().catch(() => [])
      if (!res.ok) {
        placesError.value = typeof data.detail === 'string' ? data.detail : 'Nie udało się wczytać miejsc.'
        return
      }
      helsinkiPlaces.value = data
      const start = defaultStart(data)
      if (start) {
        startPoint.value = { name: start.name, lat: start.lat, lng: start.lng, hours: start.hours }
      }
    } catch {
      placesError.value = 'Nie udało się wczytać miejsc.'
    }
  }

  loadPlaces()

  const calculateRoute = async () => {
    isLoading.value = true
    error.value = null

    const closed = findClosedOnDay(attractions.value, visitDay.value)
    if (closed.length) {
      error.value = `Zamknięte w wybrany dzień: ${closed.map(p => p.name).join(', ')}`
      isLoading.value = false
      return
    }

    const invalidWindow = findInvalidVisitWindow(attractions.value, visitDay.value)
    if (invalidWindow.length) {
      error.value = `Nieprawidłowy przedział wizyty: ${invalidWindow.map(p => p.name).join(', ')}`
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
        data.legs,
        timeStringToMinutes(startTime.value),
        startPoint.value,
        attractions.value
      )
      totalDuration.value = formatDurationMinutes(
        data.end_time - timeStringToMinutes(startTime.value)
      )
      totalTravelTime.value = formatDurationMinutes(data.travel_time ?? 0)
      totalWaitTime.value = formatDurationMinutes(
        totalWaitMinutes(data.visits ?? [], data.legs, timeStringToMinutes(startTime.value))
      )
      totalWalkDistance.value = formatDistanceMeters(data.walk_distance ?? 0)

      routeSegments.value = routeSegmentsFromResponse(data)
      routePolyline.value = polylineFromOptimizeResponse(data) ?? []
    } catch {
      error.value = 'Nie udało się połączyć z serwerem.'
    } finally {
      isLoading.value = false
    }
  }

  return {
    helsinkiPlaces, placesError, startPoint, startTime, endTime, visitDay, attractions,
    isRouteCalculated, isLoading, error, totalDuration, totalTravelTime, totalWaitTime, totalWalkDistance, visitOrder, mapCenter, routePolyline, routeSegments,
    loadPlaces, addAttraction, removeAttraction, updateAttraction, clearRouteResult, setVisitDay, calculateRoute
  }
})