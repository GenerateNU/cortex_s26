import { useRef, useEffect, useState, useCallback, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import ForceGraph2D from 'react-force-graph-2d'
import Navbar from '../components/Navbar'
import {
  getGraphData,
  listDocuments,
  type GraphData,
  type GraphNode,
  type GraphLink,
} from '../services/api'
import NodeDetailPanel from '../components/NodeDetailPanel'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type NodeObj = GraphNode & { x?: number; y?: number; [k: string]: any }
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type LinkObj = GraphLink & { [k: string]: any }

export default function GraphPage() {
  const wrapperRef = useRef<HTMLDivElement>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null)
  const hasZoomed = useRef(false)
  const appliedUrlParams = useRef(false)
  const [searchParams] = useSearchParams()
  const [width, setWidth] = useState(800)
  const [selectedDataset, setSelectedDataset] = useState(
    searchParams.get('dataset') || ''
  )
  const [hoveredNode, setHoveredNode] = useState<string | null>(null)
  const [hoveredLink, setHoveredLink] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [nodeSearch, setNodeSearch] = useState('')
  const [nodeSearchFocused, setNodeSearchFocused] = useState(false)

  const { data: docs = [] } = useQuery({
    queryKey: ['documents'],
    queryFn: listDocuments,
    staleTime: 5000,
  })

  const datasets = useMemo(() => {
    const set = new Set(docs.map(d => d.dataset_name).filter(Boolean))
    return Array.from(set).sort()
  }, [docs])

  const { data: rawGraphData, isLoading } = useQuery({
    queryKey: ['graph', selectedDataset],
    queryFn: () => getGraphData(selectedDataset || undefined),
    staleTime: 30_000,
  })

  const graphData = useMemo<GraphData | undefined>(() => {
    if (!rawGraphData) return undefined
    hasZoomed.current = false
    return { nodes: [...rawGraphData.nodes], links: [...rawGraphData.links] }
  }, [rawGraphData])

  useEffect(() => {
    const el = wrapperRef.current
    if (!el) return
    const ro = new ResizeObserver(entries => {
      const rect = entries[0]?.contentRect
      if (rect) setWidth(rect.width)
    })
    ro.observe(el)
    setWidth(el.clientWidth)
    return () => ro.disconnect()
  }, [])

  const graphHeight =
    typeof window !== 'undefined'
      ? Math.max(window.innerHeight - 260, 400)
      : 600

  const handleNodeHover = useCallback((node: NodeObj | null) => {
    setHoveredNode(node ? (node.name ?? node.id ?? null) : null)
  }, [])

  const handleLinkHover = useCallback((link: LinkObj | null) => {
    setHoveredLink(link ? ((link.label as string | undefined) ?? null) : null)
  }, [])

  const handleNodeClick = useCallback((node: NodeObj) => {
    setSelectedNode({
      id: String(node.id),
      name: node.name,
      val: node.val ?? 1,
    })
    setNodeSearch('')
    setNodeSearchFocused(false)
  }, [])

  // Neighbor IDs for highlight when a node is selected
  const neighborIds = useMemo(() => {
    if (!selectedNode || !graphData) return new Set<string>()
    const ids = new Set<string>()
    for (const link of graphData.links) {
      const src =
        typeof link.source === 'object'
          ? (link.source as GraphNode).id
          : link.source
      const tgt =
        typeof link.target === 'object'
          ? (link.target as GraphNode).id
          : link.target
      if (src === selectedNode.id) ids.add(tgt)
      else if (tgt === selectedNode.id) ids.add(src)
    }
    return ids
  }, [selectedNode, graphData])

  // Dynamic link color based on selection
  const linkColorFn = useCallback(
    (link: LinkObj) => {
      if (!selectedNode) return 'rgba(255,255,255,0.15)'
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const src =
        typeof link.source === 'object' ? (link.source as any).id : link.source
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const tgt =
        typeof link.target === 'object' ? (link.target as any).id : link.target
      if (src === selectedNode.id || tgt === selectedNode.id)
        return 'rgba(167,139,250,0.5)'
      return 'rgba(255,255,255,0.04)'
    },
    [selectedNode]
  )

  // Node search results (client-side filter)
  const nodeSearchResults = useMemo(() => {
    if (!nodeSearch.trim() || !graphData) return []
    const q = nodeSearch.toLowerCase()
    return graphData.nodes
      .filter(
        n => !/^[0-9a-f]{8}-/i.test(n.name) && n.name.toLowerCase().includes(q)
      )
      .slice(0, 8)
  }, [nodeSearch, graphData])

  // Zoom to a specific node
  const zoomToNode = useCallback(
    (node: GraphNode) => {
      if (!fgRef.current || !graphData) return
      // Find the live node object with x/y coordinates
      const liveNode = (graphData.nodes as NodeObj[]).find(
        n => n.id === node.id
      )
      if (liveNode?.x != null && liveNode?.y != null) {
        fgRef.current.centerAt(liveNode.x, liveNode.y, 600)
        fgRef.current.zoom(2.5, 600)
      }
    },
    [graphData]
  )

  // Compute degree per node for sizing
  const degreeMap = useMemo(() => {
    const map = new Map<string, number>()
    if (!graphData) return map
    for (const link of graphData.links) {
      map.set(link.source as string, (map.get(link.source as string) || 0) + 1)
      map.set(link.target as string, (map.get(link.target as string) || 0) + 1)
    }
    return map
  }, [graphData])

  const nodeCanvasObject = useCallback(
    (node: NodeObj, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const rawLabel = node.name || String(node.id || '')
      const isUUID = /^[0-9a-f]{8}-[0-9a-f]{4}-/i.test(rawLabel)
      const label = isUUID ? '' : rawLabel
      const degree = degreeMap.get(String(node.id)) || 1
      const radius = Math.max(3, Math.sqrt(degree) * 3)
      const x = node.x ?? 0
      const y = node.y ?? 0
      const nodeId = String(node.id)
      const isHovered = hoveredNode === (node.name ?? node.id ?? null)
      const isSelected = selectedNode?.id === nodeId
      const isNeighbor = neighborIds.has(nodeId)
      const hasFocus = !!selectedNode // is any node selected?
      const isDimmed = hasFocus && !isSelected && !isNeighbor

      // Node circle
      ctx.beginPath()
      ctx.arc(x, y, radius, 0, 2 * Math.PI)
      if (isSelected) {
        ctx.fillStyle = '#a78bfa'
      } else if (isDimmed) {
        ctx.fillStyle = 'rgba(124,58,237,0.2)'
      } else if (isHovered) {
        ctx.fillStyle = '#a78bfa'
      } else {
        ctx.fillStyle = '#7c3aed'
      }
      ctx.fill()

      // Glow ring on selected or hovered
      if (isSelected) {
        ctx.strokeStyle = '#c4b5fd'
        ctx.lineWidth = 2
        ctx.stroke()
        ctx.beginPath()
        ctx.arc(x, y, radius + 3, 0, 2 * Math.PI)
        ctx.strokeStyle = 'rgba(196,181,253,0.25)'
        ctx.lineWidth = 1
        ctx.stroke()
      } else if (isHovered && !isDimmed) {
        ctx.strokeStyle = '#c4b5fd'
        ctx.lineWidth = 1.5
        ctx.stroke()
      }

      // Label logic
      const showLabel =
        isSelected ||
        isNeighbor ||
        isHovered ||
        (!isDimmed && (globalScale > 1.5 || degree >= 4))
      if (label && showLabel) {
        const fontSize = Math.max(10, 12 / globalScale)
        ctx.font = `${fontSize}px sans-serif`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'top'
        if (isSelected) ctx.fillStyle = '#e9d5ff'
        else if (isDimmed) ctx.fillStyle = 'rgba(255,255,255,0.15)'
        else if (isHovered) ctx.fillStyle = '#e9d5ff'
        else ctx.fillStyle = 'rgba(255,255,255,0.7)'
        ctx.fillText(label, x, y + radius + 2)
      }
    },
    [degreeMap, hoveredNode, selectedNode, neighborIds]
  )

  const nodePointerAreaPaint = useCallback(
    (node: NodeObj, color: string, ctx: CanvasRenderingContext2D) => {
      const degree = degreeMap.get(String(node.id)) || 1
      const radius = Math.max(3, Math.sqrt(degree) * 3) + 2
      ctx.beginPath()
      ctx.arc(node.x ?? 0, node.y ?? 0, radius, 0, 2 * Math.PI)
      ctx.fillStyle = color
      ctx.fill()
    },
    [degreeMap]
  )

  // Apply URL params once graph data loads
  useEffect(() => {
    if (!graphData || appliedUrlParams.current) return
    const nodeParam = searchParams.get('node')
    if (nodeParam) {
      const match = graphData.nodes.find(
        n => n.name.toLowerCase() === nodeParam.toLowerCase()
      )
      if (match) {
        setSelectedNode(match)
        // Zoom to node after a short delay for simulation to settle
        setTimeout(() => zoomToNode(match), 800)
        appliedUrlParams.current = true
      }
    }
  }, [graphData, searchParams, zoomToNode])

  // Configure force simulation for better spread
  useEffect(() => {
    if (!fgRef.current) return
    fgRef.current.d3Force('charge')?.strength(-150)
    fgRef.current.d3Force('link')?.distance(60)
    fgRef.current.d3Force('center')?.strength(0.05)
  })

  // Zoom to fit only on first load
  const handleEngineStop = useCallback(() => {
    if (fgRef.current && !hasZoomed.current) {
      hasZoomed.current = true
      fgRef.current.zoomToFit(400, 60)
    }
  }, [])

  const hasData =
    graphData && (graphData.nodes.length > 0 || graphData.links.length > 0)

  return (
    <div className="relative min-h-screen bg-black">
      <Navbar />

      <div
        className="pointer-events-none fixed inset-0 z-0"
        style={{
          background:
            'radial-gradient(ellipse at 50% 40%, rgba(124,58,237,0.18) 0%, transparent 60%)',
        }}
      />

      <main className="relative z-10 px-4 pt-20 pb-8 max-w-7xl mx-auto">
        <div className="pt-10 mb-5">
          <div className="flex flex-col sm:flex-row sm:items-end gap-4 justify-between">
            <div>
              <h1 className="text-4xl font-bold text-white mb-1 tracking-tight">
                Knowledge Graph
              </h1>
              <div className="flex items-center gap-3 mt-2">
                {graphData ? (
                  <>
                    <span className="inline-flex items-center gap-1.5 text-xs font-medium tracking-wide uppercase text-white/40">
                      <span className="inline-block w-1.5 h-1.5 rounded-full bg-violet-500" />
                      {graphData.nodes.length} nodes
                    </span>
                    <span className="text-white/15">|</span>
                    <span className="inline-flex items-center gap-1.5 text-xs font-medium tracking-wide uppercase text-white/40">
                      <span className="inline-block w-3 h-px bg-violet-500/60" />
                      {graphData.links.length} relationships
                    </span>
                  </>
                ) : (
                  <span className="text-xs text-white/30 tracking-wide">
                    Explore entity relationships across your documents
                  </span>
                )}
              </div>
            </div>

            <select
              value={selectedDataset}
              onChange={e => setSelectedDataset(e.target.value)}
              className="input-dark sm:w-52 bg-black cursor-pointer"
            >
              <option value="">All datasets</option>
              {datasets.map(ds => (
                <option key={ds} value={ds}>
                  {ds}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Graph container */}
        <div
          ref={wrapperRef}
          className="relative w-full rounded-2xl overflow-hidden"
          style={{
            height: graphHeight,
            boxShadow:
              '0 0 80px -20px rgba(124,58,237,0.15), inset 0 0 0 1px rgba(255,255,255,0.06)',
          }}
        >
          {/* Controls — overlaid top-left */}
          <div className="absolute top-3 left-3 z-20 flex items-center gap-1.5">
            {[
              { key: 'Scroll', icon: '\u21C5', label: 'Zoom' },
              { key: 'Drag', icon: '\u2725', label: 'Pan' },
              { key: 'Click', icon: '\u25CB', label: 'Select' },
            ].map(hint => (
              <span
                key={hint.key}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium tracking-wider uppercase text-white/30 bg-white/[0.04] border border-white/[0.06] backdrop-blur-sm"
              >
                <span className="text-white/50">{hint.icon}</span>
                {hint.label}
              </span>
            ))}
          </div>

          {/* Node search — overlaid top-right */}
          <div className="absolute top-3 right-3 z-20 w-56">
            <div className="relative">
              <svg
                className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-white/25 pointer-events-none"
                viewBox="0 0 16 16"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              >
                <circle cx="7" cy="7" r="5" />
                <line x1="11" y1="11" x2="14" y2="14" />
              </svg>
              <input
                type="text"
                value={nodeSearch}
                onChange={e => setNodeSearch(e.target.value)}
                onFocus={() => setNodeSearchFocused(true)}
                onBlur={() =>
                  setTimeout(() => setNodeSearchFocused(false), 150)
                }
                onKeyDown={e => {
                  if (e.key === 'Escape') {
                    setNodeSearch('')
                    setNodeSearchFocused(false)
                    ;(e.target as HTMLInputElement).blur()
                  }
                }}
                placeholder="Find node..."
                className="w-full pl-8 pr-3 py-1.5 rounded-lg text-xs text-white/80 placeholder-white/20 bg-white/[0.04] border border-white/[0.06] backdrop-blur-sm outline-none focus:border-white/15 focus:bg-white/[0.07] transition-all"
              />
            </div>
            {nodeSearchFocused &&
              nodeSearch &&
              nodeSearchResults.length > 0 && (
                <div className="mt-1 rounded-lg border border-white/[0.08] bg-black/90 backdrop-blur-md overflow-hidden">
                  {nodeSearchResults.map(n => (
                    <button
                      key={n.id}
                      onMouseDown={e => {
                        e.preventDefault()
                        setSelectedNode(n)
                        zoomToNode(n)
                        setNodeSearch('')
                        setNodeSearchFocused(false)
                      }}
                      className="w-full flex items-center gap-2 px-3 py-2 text-left text-xs text-white/70 hover:bg-white/[0.06] hover:text-white transition-colors"
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-violet-500 shrink-0" />
                      <span className="truncate">{n.name}</span>
                      <span className="ml-auto text-[10px] text-white/20 shrink-0">
                        {n.val - 1}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            {nodeSearchFocused &&
              nodeSearch &&
              nodeSearchResults.length === 0 && (
                <div className="mt-1 rounded-lg border border-white/[0.08] bg-black/90 backdrop-blur-md px-3 py-2">
                  <span className="text-xs text-white/20 italic">
                    No matching nodes
                  </span>
                </div>
              )}
          </div>

          {/* Hover tooltip — overlaid bottom-left */}
          {(hoveredNode || hoveredLink) && (
            <div
              className="absolute bottom-4 left-4 z-20 inline-flex items-center gap-2.5 px-3.5 py-2 rounded-lg text-sm backdrop-blur-md"
              style={{
                background:
                  'linear-gradient(135deg, rgba(124,58,237,0.15), rgba(139,92,246,0.08))',
                border: '1px solid rgba(139,92,246,0.2)',
                boxShadow: '0 4px 24px -4px rgba(124,58,237,0.25)',
              }}
            >
              {hoveredNode ? (
                <>
                  <span
                    className="inline-block w-2.5 h-2.5 rounded-full"
                    style={{
                      background: '#7c3aed',
                      boxShadow: '0 0 8px 2px rgba(124,58,237,0.5)',
                    }}
                  />
                  <span className="text-white/90 font-medium">
                    {hoveredNode}
                  </span>
                  <span className="text-[10px] uppercase tracking-widest text-violet-400/60 font-medium ml-1">
                    node
                  </span>
                </>
              ) : (
                <>
                  <svg
                    width="14"
                    height="6"
                    viewBox="0 0 14 6"
                    fill="none"
                    className="opacity-70"
                  >
                    <line
                      x1="0"
                      y1="3"
                      x2="11"
                      y2="3"
                      stroke="#8b5cf6"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                    />
                    <polyline
                      points="8.5,0.5 11,3 8.5,5.5"
                      fill="none"
                      stroke="#8b5cf6"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  <span className="text-white/90 font-medium">
                    {hoveredLink}
                  </span>
                  <span className="text-[10px] uppercase tracking-widest text-violet-400/60 font-medium ml-1">
                    edge
                  </span>
                </>
              )}
            </div>
          )}
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center z-10">
              <div className="flex flex-col items-center gap-3">
                <svg
                  className="w-8 h-8 animate-spin text-violet-500"
                  viewBox="0 0 24 24"
                  fill="none"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="3"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
                  />
                </svg>
                <p className="text-sm text-[#a1a1aa]">Loading graph…</p>
              </div>
            </div>
          )}

          {!isLoading && !hasData && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
              <div className="opacity-15 absolute pointer-events-none">
                <svg width="320" height="320" viewBox="0 0 320 320" fill="none">
                  <circle
                    cx="160"
                    cy="160"
                    r="150"
                    stroke="#7c3aed"
                    strokeWidth="1.5"
                    strokeDasharray="4 8"
                  />
                  <circle
                    cx="160"
                    cy="160"
                    r="110"
                    stroke="#8b5cf6"
                    strokeWidth="1"
                    strokeDasharray="3 6"
                  />
                  <circle
                    cx="160"
                    cy="160"
                    r="70"
                    stroke="#a78bfa"
                    strokeWidth="0.75"
                    strokeDasharray="2 5"
                  />
                </svg>
              </div>
              <div className="relative flex flex-col items-center gap-3 text-center z-10">
                <div className="w-14 h-14 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center">
                  <svg
                    width="26"
                    height="26"
                    viewBox="0 0 26 26"
                    fill="none"
                    className="text-white/20"
                  >
                    <circle
                      cx="13"
                      cy="13"
                      r="3.5"
                      stroke="currentColor"
                      strokeWidth="1.5"
                    />
                    <circle
                      cx="4.5"
                      cy="5.5"
                      r="2.5"
                      stroke="currentColor"
                      strokeWidth="1.5"
                    />
                    <circle
                      cx="21.5"
                      cy="5.5"
                      r="2.5"
                      stroke="currentColor"
                      strokeWidth="1.5"
                    />
                    <circle
                      cx="4.5"
                      cy="20.5"
                      r="2.5"
                      stroke="currentColor"
                      strokeWidth="1.5"
                    />
                    <circle
                      cx="21.5"
                      cy="20.5"
                      r="2.5"
                      stroke="currentColor"
                      strokeWidth="1.5"
                    />
                    <line
                      x1="13"
                      y1="9.5"
                      x2="4.5"
                      y2="5.5"
                      stroke="currentColor"
                      strokeWidth="1"
                      opacity="0.5"
                    />
                    <line
                      x1="13"
                      y1="9.5"
                      x2="21.5"
                      y2="5.5"
                      stroke="currentColor"
                      strokeWidth="1"
                      opacity="0.5"
                    />
                    <line
                      x1="13"
                      y1="16.5"
                      x2="4.5"
                      y2="20.5"
                      stroke="currentColor"
                      strokeWidth="1"
                      opacity="0.5"
                    />
                    <line
                      x1="13"
                      y1="16.5"
                      x2="21.5"
                      y2="20.5"
                      stroke="currentColor"
                      strokeWidth="1"
                      opacity="0.5"
                    />
                  </svg>
                </div>
                <p className="text-white/50 font-medium">
                  No graph data available
                </p>
                <p className="text-[#a1a1aa] text-sm max-w-xs">
                  Upload and process documents to build your knowledge graph.
                </p>
              </div>
            </div>
          )}

          {!isLoading && hasData && width > 0 && (
            <ForceGraph2D
              ref={fgRef}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              graphData={graphData as any}
              width={width}
              height={graphHeight}
              backgroundColor="#000000"
              nodeCanvasObject={nodeCanvasObject}
              nodePointerAreaPaint={nodePointerAreaPaint}
              linkColor={linkColorFn}
              linkWidth={1}
              linkDirectionalArrowLength={3}
              linkDirectionalArrowRelPos={1}
              linkDirectionalArrowColor={linkColorFn}
              linkLabel="label"
              onNodeClick={handleNodeClick}
              onNodeHover={handleNodeHover}
              onLinkHover={handleLinkHover}
              onEngineStop={handleEngineStop}
              cooldownTicks={200}
              d3AlphaDecay={0.05}
              d3VelocityDecay={0.3}
              warmupTicks={100}
            />
          )}

          {/* Node detail panel */}
          {selectedNode && graphData && (
            <NodeDetailPanel
              node={selectedNode}
              links={graphData.links}
              nodes={graphData.nodes}
              onClose={() => setSelectedNode(null)}
              onSelectNode={n => setSelectedNode(n)}
            />
          )}
        </div>
      </main>
    </div>
  )
}
