import 'leaflet/dist/leaflet.css'
import '@geoman-io/leaflet-geoman-free/dist/leaflet-geoman.css'
import './boundary.css'

// Order matters: ./leaflet exposes the global `L` that Geoman needs when it loads.
import L from './leaflet'
import '@geoman-io/leaflet-geoman-free'

import { useEffect, useRef, useState } from 'react'

import { Icon } from '@/components/ui'
import { cn } from '@/lib/cn'

import { mergePolygons } from './format'
import type { BoundaryFeature, Geometry, Overlap } from './types'

type Props = {
  /** Other projects' registered boundaries, drawn for context. */
  context: BoundaryFeature[]
  /** The boundary being viewed or edited. */
  geometry: Geometry | null
  /** Overlaps to highlight (shared areas hatched, conflicting projects in warn colour). */
  overlaps: Overlap[]
  editable: boolean
  onChange: (geometry: Geometry | null) => void
  /** Increment to start drawing a new shape (e.g. from a "Re-draw" button). */
  drawSignal: number
  /** Changes when another project is selected, so the map re-centres on it. */
  focusKey: string
  /** Label shown on the project's own shape. */
  label?: string
}

const START: L.LatLngTuple = [18.78, 100.78] // Nan, Thailand
const EMPTY_GEOMETRY_JSON = 'null'

/** Read a design token (CSS variable) so the map follows the app's light/dark palette. */
function token(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

const toolButton =
  'grid size-[34px] place-items-center rounded-[9px] border border-line bg-surface text-muted shadow-card hover:bg-surface-2 disabled:opacity-50'

export function BoundaryMap({
  context,
  geometry,
  overlaps,
  editable,
  onChange,
  drawSignal,
  focusKey,
  label,
}: Props) {
  const element = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)
  const draftRef = useRef<L.FeatureGroup | null>(null)
  const contextRef = useRef<L.GeoJSON | null>(null)
  const overlapRef = useRef<L.GeoJSON | null>(null)
  const onChangeRef = useRef(onChange)
  const editableRef = useRef(editable)
  const lastGeometry = useRef(EMPTY_GEOMETRY_JSON)
  const fittedKey = useRef<string | null>(null)
  const [view, setView] = useState({ lat: START[0], lng: START[1], zoom: 13 })
  const [showContext, setShowContext] = useState(true)
  const [drawing, setDrawing] = useState(false)

  useEffect(() => {
    onChangeRef.current = onChange
    editableRef.current = editable
  })

  // Create the map once.
  useEffect(() => {
    const map = L.map(element.current!, { zoomControl: false }).setView(START, 13)
    L.control.zoom({ position: 'bottomright' }).addTo(map)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map)

    contextRef.current = L.geoJSON(undefined, { pmIgnore: true } as L.GeoJSONOptions).addTo(map)
    overlapRef.current = L.geoJSON(undefined, { pmIgnore: true } as L.GeoJSONOptions).addTo(map)
    draftRef.current = L.featureGroup().addTo(map)

    map.pm.setGlobalOptions({ allowSelfIntersection: false, snappable: true })

    map.on('pm:create', (event) => {
      const draft = draftRef.current!
      draft.clearLayers()
      draft.addLayer(event.layer)
      watch(event.layer as L.Polygon)
      setDrawing(false)
      emit()
    })
    map.on('pm:drawend', () => setDrawing(false))
    map.on('moveend', () => {
      const c = map.getCenter()
      setView({ lat: c.lat, lng: c.lng, zoom: map.getZoom() })
    })

    mapRef.current = map
    return () => {
      map.remove()
      mapRef.current = null
      // A new map starts empty (React dev mode mounts twice): redraw and refit on next render.
      lastGeometry.current = EMPTY_GEOMETRY_JSON
      fittedKey.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- create once; helpers read refs only
  }, [])

  function emit() {
    const shapes: Geometry[] = []
    draftRef.current?.eachLayer((layer) => {
      const feature = (layer as L.Polygon).toGeoJSON()
      shapes.push(feature.geometry as Geometry)
    })
    const merged = mergePolygons(shapes)
    lastGeometry.current = JSON.stringify(merged)
    onChangeRef.current(merged)
  }

  function watch(layer: L.Polygon) {
    layer.setStyle(draftStyle())
    if (editableRef.current) layer.pm.enable({ allowSelfIntersection: false })
    layer.on('pm:edit', emit)
  }

  function draftStyle(): L.PathOptions {
    return {
      color: token('--accent'),
      weight: 2.5,
      fillColor: token('--accent'),
      fillOpacity: 0.18,
    }
  }

  // Context layer: everyone else's boundaries; conflicting ones in warn colour.
  useEffect(() => {
    const layer = contextRef.current
    if (!layer) return
    layer.clearLayers()
    if (!showContext) return
    const conflicting = new Set(
      overlaps.filter((o) => o.exceeds_tolerance).map((o) => o.project_id),
    )
    layer.addData({ type: 'FeatureCollection', features: context } as GeoJSON.FeatureCollection)
    layer.eachLayer((l) => {
      const path = l as L.Polygon
      const props = (path.feature as BoundaryFeature).properties
      const conflict = conflicting.has(props.project_id)
      path.setStyle(
        conflict
          ? { color: token('--warn'), weight: 2.5, dashArray: '6 4', fillOpacity: 0.08 }
          : {
              color: token('--muted'),
              weight: 1.5,
              fillColor: token('--muted'),
              fillOpacity: 0.06,
            },
      )
      path.bindTooltip(props.code, {
        permanent: true,
        direction: 'center',
        className: cn('crvr-map-label', conflict ? 'is-conflict' : 'is-context'),
      })
    })
  }, [context, overlaps, showContext])

  // Shared areas, hatched in the warn colour.
  useEffect(() => {
    const layer = overlapRef.current
    if (!layer) return
    layer.clearLayers()
    for (const overlap of overlaps) {
      layer.addData(overlap.intersection as GeoJSON.Geometry)
    }
    layer.setStyle({
      color: token('--warn'),
      weight: 1,
      fillColor: token('--warn'),
      fillOpacity: 0.45,
    })
  }, [overlaps])

  // The boundary itself — only rebuilt when it changes from outside (load, upload, discard).
  useEffect(() => {
    const map = mapRef.current
    const draft = draftRef.current
    if (!map || !draft) return
    const json = JSON.stringify(geometry)
    if (json !== lastGeometry.current) {
      draft.clearLayers()
      if (geometry) {
        L.geoJSON(geometry as GeoJSON.Geometry).eachLayer((l) => {
          draft.addLayer(l)
          watch(l as L.Polygon)
        })
      }
      lastGeometry.current = json
    }

    // Zoom to the project's boundary once per project. Without one, stay on the local view
    // (fitting every registered boundary would zoom out to the whole country).
    if (fittedKey.current !== focusKey && draft.getLayers().length > 0) {
      map.fitBounds(draft.getBounds(), { padding: [40, 40], maxZoom: 16 })
      fittedKey.current = focusKey
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- watch() reads refs only
  }, [geometry, focusKey])

  // Turn vertex editing on/off when permissions change.
  useEffect(() => {
    draftRef.current?.eachLayer((l) => {
      const polygon = l as L.Polygon
      if (editable) polygon.pm.enable({ allowSelfIntersection: false })
      else polygon.pm.disable()
    })
  }, [editable, geometry])

  // Label the project's own shape.
  useEffect(() => {
    draftRef.current?.eachLayer((l) => {
      l.unbindTooltip()
      if (label)
        l.bindTooltip(label, { permanent: true, direction: 'center', className: 'crvr-map-label' })
    })
  }, [label, geometry])

  function startDrawing() {
    const map = mapRef.current
    if (!map || !editable) return
    setDrawing(true)
    map.pm.enableDraw('Polygon', {
      allowSelfIntersection: false,
      templineStyle: { color: token('--accent') },
      hintlineStyle: { color: token('--accent'), dashArray: '5 5' },
      pathOptions: draftStyle(),
    })
  }

  // External "Re-draw" request
  useEffect(() => {
    if (drawSignal > 0) startDrawing()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only react to the signal
  }, [drawSignal])

  function locate() {
    mapRef.current?.locate({ setView: true, maxZoom: 16 })
  }

  function fit() {
    const draft = draftRef.current
    if (draft && draft.getLayers().length > 0) {
      mapRef.current?.fitBounds(draft.getBounds(), { padding: [40, 40], maxZoom: 16 })
    }
  }

  return (
    <div className="relative overflow-hidden rounded-xl border border-line shadow-card">
      <div
        ref={element}
        className="crvr-map h-[58vh] min-h-[320px] w-full desk:h-[460px]"
        role="application"
        aria-label="Boundary map"
      />
      <span className="pointer-events-none absolute top-2.5 left-2.5 z-[400] rounded-lg border border-line bg-surface px-[9px] py-[5px] font-mono text-[11px] tracking-[0.04em] text-muted">
        {view.lat.toFixed(2)}&deg;N &nbsp;{view.lng.toFixed(2)}&deg;E &nbsp;&middot;&nbsp; z
        {view.zoom}
      </span>
      <div className="absolute top-2.5 right-2.5 z-[400] grid gap-1.5">
        {editable && (
          <button
            type="button"
            className={cn(toolButton, drawing && 'border-accent text-accent')}
            title="Draw a new boundary"
            aria-label="Draw a new boundary"
            onClick={startDrawing}
          >
            <Icon name="pen" strokeWidth={2} className="size-4" />
          </button>
        )}
        <button
          type="button"
          className={cn(toolButton, !showContext && 'text-faint')}
          title={showContext ? 'Hide other boundaries' : 'Show other boundaries'}
          aria-label="Toggle other boundaries"
          aria-pressed={showContext}
          onClick={() => setShowContext((v) => !v)}
        >
          <Icon name="layers" strokeWidth={2} className="size-4" />
        </button>
        <button
          type="button"
          className={toolButton}
          title="Zoom to the boundary"
          aria-label="Zoom to the boundary"
          onClick={fit}
        >
          <Icon name="map" strokeWidth={2} className="size-4" />
        </button>
        <button
          type="button"
          className={toolButton}
          title="Go to my location"
          aria-label="Go to my location"
          onClick={locate}
        >
          <Icon name="locate" strokeWidth={2} className="size-4" />
        </button>
      </div>
    </div>
  )
}
