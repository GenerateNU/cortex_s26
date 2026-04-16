import { useRef, useEffect, useState, useCallback, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import ForceGraph2D from 'react-force-graph-2d'
import Navbar from '../components/Navbar'
import { getGraphData, listDocuments, type GraphNode, type GraphLink } from '../services/api'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type NodeObj = GraphNode & { x?: number; y?: number; [k: string]: any }
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type LinkObj = GraphLink & { [k: string]: any }

export default function GraphPage() {
  const wrapperRef = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(800)
  const [selectedDataset, setSelectedDataset] = useState('')
  const [hoveredNode, setHoveredNode] = useState<string | null>(null)
  const [hoveredLink, setHoveredLink] = useState<string | null>(null)

  const { data: docs = [] } = useQuery({
    queryKey: ['documents'],
    queryFn: listDocuments,
    staleTime: 5000,
  })

  const datasets = useMemo(() => {
    const set = new Set(docs.map((d) => d.dataset_name).filter(Boolean))
    return Array.from(set).sort()
  }, [docs])

  const { data: rawGraphData, isLoading } = useQuery({
    queryKey: ['graph', selectedDataset],
    queryFn: () => getGraphData(selectedDataset || undefined),
    staleTime: 30_000,
  })

  const graphData = useMemo(() => {
    if (!rawGraphData) return undefined
    return { nodes: [...rawGraphData.nodes], links: [...rawGraphData.links] }
  }, [rawGraphData])

  useEffect(() => {
    const el = wrapperRef.current
    if (!el) return
    const ro = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect
      if (rect) setWidth(rect.width)
    })
    ro.observe(el)
    setWidth(el.clientWidth)
    return () => ro.disconnect()
  }, [])

  const graphHeight = typeof window !== 'undefined' ? Math.max(window.innerHeight - 260, 400) : 600

  const handleNodeHover = useCallback((node: NodeObj | null) => {
    setHoveredNode(node ? (node.name ?? node.id ?? null) : null)
  }, [])

  const handleLinkHover = useCallback((link: LinkObj | null) => {
    setHoveredLink(link ? (link.label as string | undefined) ?? null : null)
  }, [])

  const nodeColor = useCallback(() => '#7c3aed', [])
  const linkColor = useCallback(() => 'rgba(255,255,255,0.2)', [])

  const hasData = graphData && (graphData.nodes.length > 0 || graphData.links.length > 0)

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
        <div className="pt-10 mb-6">
          <div className="flex flex-col sm:flex-row sm:items-end gap-4 justify-between">
            <div>
              <h1 className="text-4xl font-bold text-white mb-2">Knowledge Graph</h1>
              <p className="text-[#a1a1aa] text-sm">
                {graphData
                  ? `${graphData.nodes.length} nodes · ${graphData.links.length} relationships`
                  : 'Explore entity relationships across your documents'}
              </p>
            </div>

            <select
              value={selectedDataset}
              onChange={(e) => setSelectedDataset(e.target.value)}
              className="input-dark sm:w-52 bg-black cursor-pointer"
            >
              <option value="">All datasets</option>
              {datasets.map((ds) => (
                <option key={ds} value={ds}>{ds}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Controls hint */}
        <div className="flex flex-wrap items-center gap-2 mb-4">
          {['Scroll to zoom', 'Drag to pan', 'Click node to highlight connections'].map((hint) => (
            <span key={hint} className="border border-white/15 bg-white/5 rounded-full px-3 py-1 text-sm text-zinc-300">
              {hint}
            </span>
          ))}
        </div>

        {/* Hover label */}
        {(hoveredNode || hoveredLink) && (
          <div className="mb-3 inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-violet-500/25 bg-violet-500/10 text-sm text-violet-300">
            {hoveredNode ? (
              <>
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                  <circle cx="6" cy="6" r="4" fill="#7c3aed" />
                </svg>
                {hoveredNode}
              </>
            ) : (
              <>
                <svg width="12" height="8" viewBox="0 0 12 8" fill="none" stroke="#8b5cf6" strokeWidth="1.5" strokeLinecap="round">
                  <line x1="0" y1="4" x2="10" y2="4" />
                  <polyline points="7,1 10,4 7,7" />
                </svg>
                {hoveredLink}
              </>
            )}
          </div>
        )}

        {/* Graph container */}
        <div
          ref={wrapperRef}
          className="relative w-full bg-white/[0.02] border border-white/10 rounded-2xl overflow-hidden"
          style={{ height: graphHeight }}
        >
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center z-10">
              <div className="flex flex-col items-center gap-3">
                <svg className="w-8 h-8 animate-spin text-violet-500" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                </svg>
                <p className="text-sm text-[#a1a1aa]">Loading graph…</p>
              </div>
            </div>
          )}

          {!isLoading && !hasData && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
              <div className="opacity-15 absolute pointer-events-none">
                <svg width="320" height="320" viewBox="0 0 320 320" fill="none">
                  <circle cx="160" cy="160" r="150" stroke="#7c3aed" strokeWidth="1.5" strokeDasharray="4 8" />
                  <circle cx="160" cy="160" r="110" stroke="#8b5cf6" strokeWidth="1" strokeDasharray="3 6" />
                  <circle cx="160" cy="160" r="70" stroke="#a78bfa" strokeWidth="0.75" strokeDasharray="2 5" />
                </svg>
              </div>
              <div className="relative flex flex-col items-center gap-3 text-center z-10">
                <div className="w-14 h-14 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center">
                  <svg width="26" height="26" viewBox="0 0 26 26" fill="none" className="text-white/20">
                    <circle cx="13" cy="13" r="3.5" stroke="currentColor" strokeWidth="1.5" />
                    <circle cx="4.5" cy="5.5" r="2.5" stroke="currentColor" strokeWidth="1.5" />
                    <circle cx="21.5" cy="5.5" r="2.5" stroke="currentColor" strokeWidth="1.5" />
                    <circle cx="4.5" cy="20.5" r="2.5" stroke="currentColor" strokeWidth="1.5" />
                    <circle cx="21.5" cy="20.5" r="2.5" stroke="currentColor" strokeWidth="1.5" />
                    <line x1="13" y1="9.5" x2="4.5" y2="5.5" stroke="currentColor" strokeWidth="1" opacity="0.5" />
                    <line x1="13" y1="9.5" x2="21.5" y2="5.5" stroke="currentColor" strokeWidth="1" opacity="0.5" />
                    <line x1="13" y1="16.5" x2="4.5" y2="20.5" stroke="currentColor" strokeWidth="1" opacity="0.5" />
                    <line x1="13" y1="16.5" x2="21.5" y2="20.5" stroke="currentColor" strokeWidth="1" opacity="0.5" />
                  </svg>
                </div>
                <p className="text-white/50 font-medium">No graph data available</p>
                <p className="text-[#a1a1aa] text-sm max-w-xs">
                  Upload and process documents to build your knowledge graph.
                </p>
              </div>
            </div>
          )}

          {!isLoading && hasData && width > 0 && (
            <ForceGraph2D
              graphData={graphData as Parameters<typeof ForceGraph2D>[0]['graphData']}
              width={width}
              height={graphHeight}
              backgroundColor="#000000"
              nodeColor={nodeColor}
              nodeRelSize={6}
              linkColor={linkColor}
              linkDirectionalArrowLength={4}
              linkDirectionalArrowRelPos={1}
              nodeLabel="name"
              linkLabel="label"
              onNodeHover={handleNodeHover}
              onLinkHover={handleLinkHover}
              cooldownTicks={200}
              d3AlphaDecay={0.05}
              d3VelocityDecay={0.3}
              warmupTicks={100}
            />
          )}
        </div>
      </main>
    </div>
  )
}
