export function timeStringToMinutes(time) {
  const [h, m] = time.split(':').map(Number)
  return h * 60 + m
}

export function hoursToMinutes(hours) {
  return Math.round(Number(hours) * 60)
}

export function minutesToTimeString(minutes) {
  const h = Math.floor(minutes / 60)
  const min = Math.round(minutes % 60)
  return `${String(h).padStart(2, '0')}:${String(min).padStart(2, '0')}`
}

export function formatDurationMinutes(minutes) {
  const total = Math.round(minutes)
  const h = Math.floor(total / 60)
  const m = total % 60
  if (h > 0 && m > 0) return `${h} h ${m} min`
  if (h > 0) return `${h} h`
  return `${m} min`
}

export function parseOpeningHoursString(timeStr) {
  const t = (timeStr || '').trim()
  if (!t) return null

  if (/open 24|całą dobę|24\s*h/i.test(t)) {
    return { open: 0, close: 1440 }
  }
  if (/closed|zamknięte/i.test(t)) {
    return { open: 0, close: 0, closed: true }
  }

  const match = t.match(/(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})/)
  if (match) {
    return {
      open: timeStringToMinutes(match[1]),
      close: timeStringToMinutes(match[2])
    }
  }
  return null
}

export function parseOpeningHoursForDay(hoursList, day = new Date().getDay()) {
  const entry = hoursList?.find(h => h.day === day)
  if (!entry) return null
  return parseOpeningHoursString(entry.time)
}

export function narrowOpeningHours(openingHours, visitFrom, visitTo) {
  if (!openingHours || openingHours.closed) return null
  if (!visitFrom || !visitTo) return openingHours

  const from = timeStringToMinutes(visitFrom)
  const to = timeStringToMinutes(visitTo)
  if (from >= to) return null

  const open = Math.max(openingHours.open, from)
  const close = Math.min(openingHours.close, to)
  if (open >= close) return null

  return { open, close }
}
