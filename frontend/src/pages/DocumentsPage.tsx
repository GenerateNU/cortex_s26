import { useState, useMemo } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import Navbar from '../components/Navbar'
import { listDocuments, type Document } from '../services/api'

const DOC_TYPE_COLORS: Record<string, string> = {
  RFQ: 'bg-blue-500/15 border-blue-500/25 text-blue-300',
  PO: 'bg-green-500/15 border-green-500/25 text-green-300',
  Invoice: 'bg-amber-500/15 border-amber-500/25 text-amber-300',
  Sales: 'bg-violet-500/15 border-violet-500/25 text-violet-300',
  'Client Data': 'bg-rose-500/15 border-rose-500/25 text-rose-300',
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  } catch {
    return iso
  }
}

export default function DocumentsPage() {
  const [searchParams] = useSearchParams()
  const [nameFilter, setNameFilter] = useState('')
  const [datasetFilter, setDatasetFilter] = useState(searchParams.get('dataset') ?? '')

  const hasProcessing = (docs: Document[]) => docs.some((d) => d.status === 'processing')

  const { data: docs = [], isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: listDocuments,
    staleTime: 5000,
    refetchInterval: (query) => {
      const docs = query.state.data
      return docs && hasProcessing(docs) ? 5000 : false
    },
  })

  const datasets = useMemo(() => {
    const set = new Set(docs.map((d) => d.dataset_name).filter(Boolean))
    return Array.from(set).sort()
  }, [docs])

  const filtered = useMemo(() => {
    return docs.filter((doc) => {
      const matchName = nameFilter
        ? doc.original_filename.toLowerCase().includes(nameFilter.toLowerCase())
        : true
      const matchDataset = datasetFilter
        ? doc.dataset_name === datasetFilter
        : true
      return matchName && matchDataset
    })
  }, [docs, nameFilter, datasetFilter])

  return (
    <div className="relative min-h-screen bg-black">
      <Navbar />

      <div
        className="pointer-events-none fixed inset-0 z-0"
        style={{
          background:
            'radial-gradient(ellipse at 30% 20%, rgba(124,58,237,0.15) 0%, transparent 55%)',
        }}
      />

      <main className="relative z-10 px-4 pt-20 pb-24 max-w-7xl mx-auto">
        <div className="pt-10 mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Documents</h1>
          <p className="text-[#a1a1aa] text-sm">
            {docs.length} document{docs.length !== 1 ? 's' : ''} in your knowledge base
          </p>
        </div>

        {/* Filter bar */}
        <div className="flex flex-col sm:flex-row gap-3 mb-8">
          <div className="relative flex-1">
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="7" cy="7" r="4.5" />
                <line x1="10.5" y1="10.5" x2="14" y2="14" />
              </svg>
            </div>
            <input
              type="text"
              value={nameFilter}
              onChange={(e) => setNameFilter(e.target.value)}
              placeholder="Filter by filename…"
              className="input-dark pl-9"
            />
          </div>

          <select
            value={datasetFilter}
            onChange={(e) => setDatasetFilter(e.target.value)}
            className="input-dark sm:w-56 bg-black cursor-pointer"
          >
            <option value="">All clients</option>
            {datasets.map((ds) => (
              <option key={ds} value={ds}>{ds}</option>
            ))}
          </select>
        </div>

        {/* Loading */}
        {isLoading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="bg-white/5 border border-white/10 rounded-2xl p-5">
                <div className="skeleton h-4 rounded w-3/4 mb-3" />
                <div className="skeleton h-3 rounded w-1/2 mb-4" />
                <div className="flex gap-2">
                  <div className="skeleton h-5 rounded-full w-16" />
                  <div className="skeleton h-5 rounded-full w-20" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Document grid */}
        {!isLoading && filtered.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map((doc) => (
              <DocumentCard key={doc.id} doc={doc} />
            ))}
          </div>
        )}

        {/* Empty state */}
        {!isLoading && filtered.length === 0 && (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mb-4">
              <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-white/20">
                <path d="M18 3H9a1.5 1.5 0 00-1.5 1.5v19A1.5 1.5 0 009 25h10a1.5 1.5 0 001.5-1.5V8L18 3z" />
                <polyline points="18,3 18,8 23.5,8" />
                <line x1="11" y1="13" x2="17" y2="13" />
                <line x1="11" y1="17" x2="17" y2="17" />
              </svg>
            </div>
            <p className="text-white/50 font-medium mb-2">No documents found</p>
            <p className="text-[#a1a1aa] text-sm max-w-xs mb-6">
              {docs.length === 0
                ? 'Upload your first document to get started.'
                : 'No documents match your current filters.'}
            </p>
            {docs.length === 0 && (
              <Link to="/upload" className="btn-primary">
                Upload Documents
              </Link>
            )}
          </div>
        )}
      </main>
    </div>
  )
}

function DocumentCard({ doc }: { doc: Document }) {
  const statusDot = {
    completed: 'bg-green-500',
    processing: 'bg-yellow-500 animate-pulse',
    failed: 'bg-red-500',
  }[doc.status]

  return (
    <Link
      to={`/documents/${doc.id}`}
      className="bg-white/5 border border-white/10 rounded-2xl p-5 hover:border-white/20 hover:bg-white/[0.07] transition-all duration-200 flex flex-col gap-3 group"
    >
      {/* Filename + status */}
      <div className="flex items-start gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-white truncate group-hover:text-white/90" title={doc.original_filename}>
            {doc.original_filename}
          </p>
        </div>
        <span className={`w-2 h-2 rounded-full flex-shrink-0 mt-1.5 ${statusDot}`} title={doc.status} />
      </div>

      {/* Badges */}
      <div className="flex flex-wrap gap-1.5">
        {doc.dataset_name && (
          <span className="px-2.5 py-0.5 rounded-full text-xs border border-violet-500/25 bg-violet-500/10 text-violet-300">
            {doc.dataset_name}
          </span>
        )}
        {doc.document_type && (
          <span className={`px-2.5 py-0.5 rounded-full text-xs border font-medium ${DOC_TYPE_COLORS[doc.document_type] ?? 'bg-white/5 border-white/15 text-zinc-300'}`}>
            {doc.document_type}
          </span>
        )}
      </div>

      {/* Stats */}
      <p className="text-xs text-[#a1a1aa]">
        {doc.insights?.length ?? 0} insight{(doc.insights?.length ?? 0) !== 1 ? 's' : ''} · {doc.entities?.length ?? 0} entit{(doc.entities?.length ?? 0) !== 1 ? 'ies' : 'y'}
      </p>

      {/* Date */}
      <p className="text-xs text-white/25 mt-auto">
        {formatDate(doc.uploaded_at)}
      </p>
    </Link>
  )
}
