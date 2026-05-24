export function formatDistanceMeters(meters) {
  const m = Math.round(meters)
  if (m >= 1000) {
    return `${(m / 1000).toFixed(1).replace('.', ',')} km`
  }
  return `${m} m`
}
