// Leaflet plugins such as Geoman expect `L` as a browser global. Import this module before them:
//   import L from './leaflet'
//   import '@geoman-io/leaflet-geoman-free'
import L from 'leaflet'

;(globalThis as typeof globalThis & { L: typeof L }).L = L

export default L
