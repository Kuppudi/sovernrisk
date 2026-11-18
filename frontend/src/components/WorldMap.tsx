import { useEffect, useMemo, useRef, useState } from 'react'
import type { PointerEvent } from 'react'
import { geoNaturalEarth1, geoPath } from 'd3-geo'
import { formatIndicatorValue } from '../services/indicatorLabels'
import {
  getMapColor,
  getValueRange,
  mapColors,
  riskBands,
  getRiskBand,
  type MapPlace,
  type WorldShapes,
} from '../services/mapData'

interface WorldMapProps {
  shapes: WorldShapes
  countries: { iso3: string; value: number | null }[]
  indicator: string
  unit?: string
  year?: number
  mapLabel?: string
  emptyLabel?: string
  missingLabel?: string
  selectedCountry: string | null
  onSelectCountry: (country: MapPlace) => void
}

interface Viewport {
  scale: number
  x: number
  y: number
}

interface DragStart {
  pointerId: number
  clientX: number
  clientY: number
  x: number
  y: number
  viewport: Viewport
}

function constrain(viewport: Viewport): Viewport {
  return {
    ...viewport,
    x: Math.max(1000 * (1 - viewport.scale), Math.min(0, viewport.x)),
    y: Math.max(500 * (1 - viewport.scale), Math.min(0, viewport.y)),
  }
}

function zoom(viewport: Viewport, factor: number, x = 500, y = 250): Viewport {
  const scale = Math.max(1, Math.min(12, viewport.scale * factor))
  const ratio = scale / viewport.scale
  return constrain({
    scale,
    x: x - (x - viewport.x) * ratio,
    y: y - (y - viewport.y) * ratio,
  })
}

function svgPoint(svg: SVGSVGElement, clientX: number, clientY: number) {
  const matrix = svg.getScreenCTM()
  return matrix ? new DOMPoint(clientX, clientY).matrixTransform(matrix.inverse()) : new DOMPoint(500, 250)
}

export function WorldMap({
  shapes, countries, indicator, unit, year,
  mapLabel = 'Indicator map', emptyLabel = 'No reported values for this year',
  missingLabel = 'No data', selectedCountry, onSelectCountry,
}: WorldMapProps) {
  const [hoveredCountry, setHoveredCountry] = useState<MapPlace | null>(null)
  const [viewport, setViewport] = useState<Viewport>({ scale: 1, x: 0, y: 0 })
  const svg = useRef<SVGSVGElement>(null)
  const drag = useRef<DragStart | null>(null)
  const suppressClick = useRef(false)
  const countryValues = new Map(countries.map((country) => [country.iso3, country.value]))
  const range = getValueRange(countries.map((country) => country.value))

  function valueLabel(value: number | null) {
    if (value === null) return missingLabel
    const formatted = formatIndicatorValue(value, indicator, unit)
    return indicator === 'default-risk' ? `${formatted} · ${getRiskBand(value).label}` : formatted
  }

  useEffect(() => {
    const element = svg.current
    if (!element) return
    const handleWheel = (event: WheelEvent) => {
      event.preventDefault()
      drag.current = null
      const point = svgPoint(element, event.clientX, event.clientY)
      setViewport((current) => zoom(current, Math.exp(-event.deltaY * 0.0015), point.x, point.y))
    }
    element.addEventListener('wheel', handleWheel, { passive: false })
    return () => element.removeEventListener('wheel', handleWheel)
  }, [])

  // Projection stays fixed while the SVG group handles zooming and panning.
  const countryPaths = useMemo(() => {
    const projection = geoNaturalEarth1().fitExtent([[16, 12], [984, 488]], shapes)
    const drawPath = geoPath(projection)
    return shapes.features.map((feature) => ({ country: feature.properties, path: drawPath(feature) || '' }))
  }, [shapes])

  function startDrag(event: PointerEvent<SVGSVGElement>) {
    suppressClick.current = false
    if (event.button !== 0 || !event.isPrimary || viewport.scale === 1) return
    const point = svgPoint(event.currentTarget, event.clientX, event.clientY)
    drag.current = { pointerId: event.pointerId, clientX: event.clientX, clientY: event.clientY, x: point.x, y: point.y, viewport }
  }

  function moveDrag(event: PointerEvent<SVGSVGElement>) {
    const start = drag.current
    if (!start || start.pointerId !== event.pointerId) return
    if (Math.hypot(event.clientX - start.clientX, event.clientY - start.clientY) < 4) return
    event.currentTarget.setPointerCapture(event.pointerId)
    suppressClick.current = true
    setHoveredCountry(null)
    const point = svgPoint(event.currentTarget, event.clientX, event.clientY)
    setViewport(constrain({ ...start.viewport, x: start.viewport.x + point.x - start.x, y: start.viewport.y + point.y - start.y }))
  }

  function endDrag(event: PointerEvent<SVGSVGElement>) {
    drag.current = null
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
  }

  return (
    <div className="world-map">
      <div className="map-zoom-controls" aria-label="Map zoom controls">
        <button
          type="button" aria-label="Zoom in" disabled={viewport.scale >= 12}
          onClick={() => setViewport((current) => zoom(current, 1.5))}
        >+</button>
        <button
          type="button" aria-label="Zoom out" disabled={viewport.scale <= 1}
          onClick={() => setViewport((current) => zoom(current, 1 / 1.5))}
        >−</button>
        <button
          type="button" aria-label="Reset zoom"
          onClick={() => setViewport({ scale: 1, x: 0, y: 0 })}
        >Reset</button>
      </div>
      {hoveredCountry && (
        <div className="map-tooltip" role="status">
          <strong>{hoveredCountry.name}</strong>
          <span>{valueLabel(countryValues.get(hoveredCountry.iso3) ?? null)}{year ? ` · ${year}` : ''}</span>
        </div>
      )}
      <svg
        ref={svg}
        viewBox="0 0 1000 500"
        role="group"
        aria-label={`${mapLabel}${year ? ` for ${year}` : ''}`}
        className={viewport.scale > 1 ? 'map-viewport zoomed' : 'map-viewport'}
        style={{ touchAction: viewport.scale > 1 ? 'none' : 'pan-y' }}
        onPointerDown={startDrag}
        onPointerMove={moveDrag}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onPointerLeave={(event) => {
          const start = drag.current
          if (start && !event.currentTarget.hasPointerCapture(start.pointerId)) {
            drag.current = null
          }
        }}
        onClickCapture={(event) => {
          if (suppressClick.current) {
            event.stopPropagation()
            suppressClick.current = false
          }
        }}
        onDoubleClick={(event) => {
          const point = svgPoint(event.currentTarget, event.clientX, event.clientY)
          setViewport((current) => zoom(current, 2, point.x, point.y))
        }}
      >
        <g transform={`translate(${viewport.x} ${viewport.y}) scale(${viewport.scale})`}>
          {countryPaths.map(({ country, path }, index) => {
            const value = countryValues.get(country.iso3) ?? null
            const isSelected = selectedCountry === country.iso3
            return (
              <path
                key={`${country.iso3}-${index}`}
                d={path}
                fill={getMapColor(value, range, indicator)}
                className={isSelected ? 'map-country selected' : 'map-country'}
                vectorEffect="non-scaling-stroke"
                role="button"
                tabIndex={countryValues.has(country.iso3) ? 0 : -1}
                aria-label={`${country.name}: ${valueLabel(value)}${year ? ` in ${year}` : ''}`}
                aria-pressed={isSelected}
                onClick={() => onSelectCountry(country)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault()
                    onSelectCountry(country)
                  }
                }}
                onMouseEnter={() => setHoveredCountry(country)}
                onMouseLeave={() => setHoveredCountry(null)}
                onFocus={() => setHoveredCountry(country)}
                onBlur={() => setHoveredCountry(null)}
              >
                <title>{country.name}: {valueLabel(value)}</title>
              </path>
            )
          })}
        </g>
      </svg>
      <div className="map-legend" aria-label="Map color legend">
        {range ? (
          <>
            {indicator === 'default-risk' ? (
              <div className="risk-legend" aria-label="Research estimate bands">
                {riskBands.map((band) => <span key={band.label}><i style={{ background: band.color }} />{band.label} {band.range}</span>)}
              </div>
            ) : <div className="legend-scale">
              <div className="legend-colors">{mapColors.map((color) => <span key={color} style={{ background: color }} />)}</div>
              <div className="legend-values">
                <span>{valueLabel(range.minimum)}</span><span>{valueLabel(range.maximum)}</span>
              </div>
            </div>}
            <div className="legend-missing"><i />{missingLabel}</div>
          </>
        ) : <span>{emptyLabel}</span>}
      </div>
    </div>
  )
}
