import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  searchChunks,
  listDocuments,
  type GraphNode,
  type GraphLink,
} from '../services/api'

interface ConnectedEntity {
  id: string
  name: string
  relationship: string
  direction: 'outgoing' | 'incoming'
}

interface Props {
  node: GraphNode
  links: GraphLink[]
  nodes: GraphNode[]
  onClose: () => void
  onSelectNode: (node: GraphNode) => void
}

export default function NodeDetailPanel({
  node,
  links,
  nodes,
  onClose,
  onSelectNode,
}: Props) {
  const panelRef = useRef<HTMLDivElement>(null)

  // Close on click outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose()
      }
    }
    const timer = setTimeout(
      () => document.addEventListener('mousedown', handler),
      100
    )
    return () => {
      clearTimeout(timer)
      document.removeEventListener('mousedown', handler)
    }
  }, [onClose])

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  // Find connected entities from graph data
  const connected: ConnectedEntity[] = []
  const nodeMap = new Map(nodes.map(n => [n.id, n]))

  for (const link of links) {
    const src =
      typeof link.source === 'object'
        ? (link.source as GraphNode).id
        : link.source
    const tgt =
      typeof link.target === 'object'
        ? (link.target as GraphNode).id
        : link.target

    if (src === node.id) {
      const target = nodeMap.get(tgt)
      if (target) {
        connected.push({
          id: target.id,
          name: target.name,
          relationship: link.label,
          direction: 'outgoing',
        })
      }
    } else if (tgt === node.id) {
      const source = nodeMap.get(src)
      if (source) {
        connected.push({
          id: source.id,
          name: source.name,
          relationship: link.label,
          direction: 'incoming',
        })
      }
    }
  }

  // Search for related content
  const isUUID = /^[0-9a-f]{8}-[0-9a-f]{4}-/i.test(node.name)
  const { data: searchData, isLoading: searchLoading } = useQuery({
    queryKey: ['node-chunks', node.name],
    queryFn: () => searchChunks(node.name, 5),
    enabled: !isUUID,
    staleTime: 60_000,
  })

  // Find documents that might relate to this node
  const { data: docs = [] } = useQuery({
    queryKey: ['documents'],
    queryFn: listDocuments,
    staleTime: 30_000,
  })

  // Match documents that mention this entity in their entities array
  const relatedDocs = docs.filter(
    d =>
      d.status === 'completed' &&
      d.entities?.some(e => e.toLowerCase().includes(node.name.toLowerCase()))
  )

  return (
    <div
      ref={panelRef}
      className="absolute top-0 right-0 z-30 h-full w-[380px] max-w-[90%] overflow-y-auto"
      style={{
        background:
          'linear-gradient(180deg, rgba(10,10,12,0.97) 0%, rgba(6,6,8,0.99) 100%)',
        borderLeft: '1px solid rgba(255,255,255,0.06)',
        boxShadow: '-8px 0 40px -10px rgba(0,0,0,0.6)',
        animation: 'slideIn 0.2s ease-out',
      }}
    >
      <style>{`
        @keyframes slideIn {
          from { transform: translateX(100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      `}</style>

      {/* Header */}
      <div
        className="sticky top-0 z-10 px-5 pt-5 pb-4"
        style={{ background: 'inherit' }}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <h2 className="text-lg font-semibold text-white truncate leading-tight">
              {isUUID ? node.id.slice(0, 12) + '...' : node.name}
            </h2>
            <div className="flex items-center gap-2 mt-1.5">
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider bg-violet-500/15 border border-violet-500/20 text-violet-300">
                Entity
              </span>
              <span className="text-[11px] text-white/30">
                {node.val - 1} connection{node.val - 1 !== 1 ? 's' : ''}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="shrink-0 w-7 h-7 flex items-center justify-center rounded-lg bg-white/5 border border-white/[0.06] text-white/40 hover:text-white/70 hover:bg-white/10 transition-colors"
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 12 12"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            >
              <line x1="2" y1="2" x2="10" y2="10" />
              <line x1="10" y1="2" x2="2" y2="10" />
            </svg>
          </button>
        </div>
        <div className="mt-3 h-px bg-white/[0.06]" />
      </div>

      <div className="px-5 pb-6 space-y-5">
        {/* Connected Entities */}
        {connected.length > 0 && (
          <section>
            <h3 className="text-[11px] font-medium uppercase tracking-wider text-white/30 mb-2.5">
              Connected Entities
            </h3>
            <div className="space-y-1.5">
              {connected.map((c, i) => (
                <button
                  key={`${c.id}-${i}`}
                  onClick={() => {
                    const target = nodeMap.get(c.id)
                    if (target) onSelectNode(target)
                  }}
                  className="w-full group flex items-center gap-2.5 px-3 py-2 rounded-lg bg-white/[0.03] border border-white/[0.04] hover:bg-white/[0.06] hover:border-white/[0.08] transition-all text-left"
                >
                  <span
                    className="shrink-0 w-2 h-2 rounded-full"
                    style={{
                      background: '#7c3aed',
                      boxShadow: '0 0 6px 1px rgba(124,58,237,0.3)',
                    }}
                  />
                  <div className="min-w-0 flex-1">
                    <span className="block text-sm text-white/80 group-hover:text-white truncate">
                      {/^[0-9a-f]{8}-/i.test(c.name)
                        ? c.id.slice(0, 12) + '...'
                        : c.name}
                    </span>
                    <span className="block text-[10px] text-white/25 truncate">
                      {c.direction === 'outgoing' ? '\u2192' : '\u2190'}{' '}
                      {c.relationship}
                    </span>
                  </div>
                  <svg
                    className="shrink-0 w-3.5 h-3.5 text-white/15 group-hover:text-white/30 transition-colors"
                    viewBox="0 0 14 14"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  >
                    <polyline points="5,3 9,7 5,11" />
                  </svg>
                </button>
              ))}
            </div>
          </section>
        )}

        {/* Related Content */}
        {!isUUID && (
          <section>
            <h3 className="text-[11px] font-medium uppercase tracking-wider text-white/30 mb-2.5">
              Related Content
            </h3>
            {searchLoading ? (
              <div className="space-y-2">
                {[1, 2, 3].map(i => (
                  <div key={i} className="skeleton h-16 rounded-lg" />
                ))}
              </div>
            ) : searchData && searchData.results.length > 0 ? (
              <div className="space-y-2">
                {searchData.results.map((r, i) => (
                  <div
                    key={i}
                    className="px-3 py-2.5 rounded-lg bg-white/[0.03] border border-white/[0.04]"
                  >
                    <p className="text-xs text-white/60 leading-relaxed line-clamp-4">
                      {r.text}
                    </p>
                    {r.dataset_name && (
                      <span className="inline-block mt-1.5 text-[10px] text-violet-400/50">
                        {r.dataset_name}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-white/20 italic">
                No related content found
              </p>
            )}
          </section>
        )}

        {/* Source Documents */}
        {relatedDocs.length > 0 && (
          <section>
            <h3 className="text-[11px] font-medium uppercase tracking-wider text-white/30 mb-2.5">
              Source Documents
            </h3>
            <div className="space-y-1.5">
              {relatedDocs.map(doc => (
                <Link
                  key={doc.id}
                  to={`/documents/${doc.id}`}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-white/[0.03] border border-white/[0.04] hover:bg-white/[0.06] hover:border-white/[0.08] transition-all group"
                >
                  <svg
                    className="shrink-0 w-4 h-4 text-white/20"
                    viewBox="0 0 16 16"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.2"
                  >
                    <path d="M4 1h6l4 4v10H4V1z" />
                    <polyline points="10,1 10,5 14,5" />
                  </svg>
                  <div className="min-w-0 flex-1">
                    <span className="block text-sm text-white/70 group-hover:text-white truncate">
                      {doc.original_filename}
                    </span>
                    {doc.dataset_name && (
                      <span className="block text-[10px] text-white/25 truncate">
                        {doc.dataset_name}
                      </span>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}
