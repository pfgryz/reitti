import { createApp, h } from 'vue'
import L from 'leaflet'

export function leafletIcon(component, props, size, anchor) {
  const el = document.createElement('div')
  createApp({ render: () => h(component, props) }).mount(el)
  return L.divIcon({
    className: 'leaflet-map-marker',
    html: el.innerHTML,
    iconSize: size,
    iconAnchor: anchor
  })
}
