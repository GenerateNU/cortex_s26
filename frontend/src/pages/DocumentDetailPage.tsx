import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import Navbar from '../components/Navbar'
import { getDocument, getDocumentFileUrl, type Document, type ProgressStage } from '../services/api'

const DOC_TYPE_COLORS: Record<string, string> = {
  RFQ: 'bg-blue-500/15 border-blue-500/25 text-blue-300',
  PO: 'bg-green-500/15 border-green-500/25 text-green-300',
  CFG: 'bg-amber-500/15 border-amber-500/25 text-amber-300',
  'Client CSV': 'bg-rose-500/15 border-rose-500/25 text-rose-300',
  'Sales CSV': 'bg-violet-500/15 border-violet-500/25 text-violet-300',
}

const STAGE_LABELS: Record<ProgressStage, string> = {
  uploading: 'Uploading',
  ingesting: 'Ingesting',
  building_graph: 'Building graph',
  analyzing: 'Analyzing',
  extracting_insights: 'Extracting insights',
  completed: 'Complete',
  failed: 'Failed',
}

const STAGE_PERCENT: Record<ProgressStage, number> = {
  uploading: 10,
  ingesting: 25,
  building_graph: 50,
  analyzing: 70,
  extracting_insights: 85,
  completed: 100,
  failed: 100,
}

type Tab = 'document' | 'summary' | 'insights' | 'entities'

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

function parseInsight(insight: string): { parts: string[]; arrows: boolean } {
  const sep = insight.includes(' → ')
    ? ' → '
    : insight.includes('->')
    ? '->'
    : insight.includes(' - ')
    ? ' - '
    : null
  if (sep) {
    return { parts: insight.split(sep), arrows: true }
  }
  return { parts: [insight], arrows: false }
}

export default function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [activeTab, setActiveTab] = useState<Tab>('summary')

  const { data: doc, isLoading, isError } = useQuery({
    queryKey: ['document', id],
    queryFn: () => getDocument(id!),
    enabled: !!id,
    staleTime: 5000,
    refetchInterval: (query) => {
      const d = query.state.data
      return d?.status === 'processing' ? 2000 : false
    },
  })

  const tabs: { key: Tab; label: string; count?: number }[] = [
    { key: 'document', label: 'Document' },
    { key: 'summary', label: 'Summary' },
    { key: 'insights', label: 'Insights', count: doc?.insights?.length },
    { key: 'entities', label: 'Entities', count: doc?.entities?.length },
  ]

  return (
    <div className="relative min-h-screen bg-black">
      <Navbar />

      <div
        className="pointer-events-none fixed inset-0 z-0"
        style={{
          background:
            'radial-gradient(ellipse at 70% 15%, rgba(124,58,237,0.15) 0%, transparent 55%)',
        }}
      />

      <main className="relative z-10 px-4 pt-20 pb-24 max-w-4xl mx-auto">
        <div className="pt-10">
          {/* Back */}
          <Link
            to="/documents"
            className="inline-flex items-center gap-2 text-sm text-[#a1a1aa] hover:text-white transition-colors mb-8"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
              <line x1="13" y1="8" x2="3" y2="8" />
              <polyline points="7,12 3,8 7,4" />
            </svg>
            Documents
          </Link>

          {/* Loading skeleton */}
          {isLoading && (
            <div className="space-y-4">
              <div className="skeleton h-8 rounded w-2/3" />
              <div className="flex gap-2">
                <div className="skeleton h-6 rounded-full w-24" />
                <div className="skeleton h-6 rounded-full w-20" />
              </div>
              <div className="skeleton h-40 rounded-2xl w-full mt-6" />
            </div>
          )}

          {/* Error */}
          {isError && (
            <div className="bg-red-500/5 border border-red-500/20 rounded-2xl p-8 text-center">
              <p className="text-red-300 font-medium mb-2">Failed to load document</p>
              <p className="text-[#a1a1aa] text-sm">
                The document may not exist or there was a server error.
              </p>
              <Link
                to="/documents"
                className="inline-flex items-center gap-1 mt-4 text-violet-400 hover:text-violet-300 text-sm transition-colors"
              >
                ← Back to Documents
              </Link>
            </div>
          )}

          {doc && (
            <>
              {/* Header */}
              <div className="mb-8">
                <h1 className="text-2xl md:text-3xl font-bold text-white mb-3 leading-tight break-all">
                  {doc.original_filename}
                </h1>

                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge doc={doc} />
                  {doc.dataset_name && (
                    <span className="px-3 py-1 rounded-full text-xs border border-violet-500/25 bg-violet-500/10 text-violet-300">
                      {doc.dataset_name}
                    </span>
                  )}
                  {doc.document_type && (
                    <span className={`px-3 py-1 rounded-full text-xs border font-medium ${DOC_TYPE_COLORS[doc.document_type] ?? 'bg-white/5 border-white/15 text-zinc-300'}`}>
                      {doc.document_type}
                    </span>
                  )}
                  <span className="text-xs text-[#a1a1aa] ml-auto">
                    {formatDate(doc.uploaded_at)}
                  </span>
                </div>

                {doc.status === 'processing' && (
                  <div className="mt-4">
                    <div className="flex items-center justify-between text-xs text-[#a1a1aa] mb-1.5">
                      <span>{STAGE_LABELS[doc.progress_stage]}</span>
                      <span>{STAGE_PERCENT[doc.progress_stage]}%</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-violet-500 transition-all duration-700"
                        style={{ width: `${STAGE_PERCENT[doc.progress_stage]}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Tabs */}
              <div className="flex items-center gap-1 border-b border-white/[0.06] mb-6">
                {tabs.map(({ key, label, count }) => (
                  <button
                    key={key}
                    onClick={() => setActiveTab(key)}
                    className={`relative px-4 py-2.5 text-sm font-medium transition-colors duration-200 ${
                      activeTab === key ? 'text-white' : 'text-zinc-400 hover:text-white'
                    }`}
                  >
                    <span className="flex items-center gap-1.5">
                      {label}
                      {count !== undefined && count > 0 && (
                        <span
                          className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                            activeTab === key
                              ? 'bg-violet-500/20 text-violet-300'
                              : 'bg-white/5 text-white/30'
                          }`}
                        >
                          {count}
                        </span>
                      )}
                    </span>
                    {activeTab === key && (
                      <span className="absolute bottom-0 left-2 right-2 h-px bg-violet-500 rounded-full" />
                    )}
                  </button>
                ))}
              </div>

              {/* Content */}
              {activeTab === 'document' && <DocumentTab doc={doc} />}
              {activeTab === 'summary' && <SummaryTab doc={doc} />}
              {activeTab === 'insights' && <InsightsTab insights={doc.insights ?? []} />}
              {activeTab === 'entities' && <EntitiesTab entities={doc.entities ?? []} />}
            </>
          )}
        </div>
      </main>
    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function DocumentTab({ doc }: { doc: Document }) {
  const isPdf = doc.original_filename.toLowerCase().endsWith('.pdf')
  const isCsv = doc.original_filename.toLowerCase().endsWith('.csv')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['document-file-url', doc.id],
    queryFn: () => getDocumentFileUrl(doc.id),
    enabled: !!doc.file_url,
    staleTime: 50 * 60 * 1000, // pre-signed URLs are valid for 1h
    retry: false,
  })

  if (!doc.file_url) {
    return (
      <div className="bg-white/5 border border-white/10 rounded-2xl p-8 text-center">
        <p className="text-[#a1a1aa] text-sm">
          Raw file not stored — configure Cloudflare R2 credentials to enable document storage.
        </p>
      </div>
    )
  }

  if (isLoading) {
    return <div className="skeleton h-[600px] rounded-2xl w-full" />
  }

  if (isError || !data) {
    return (
      <div className="bg-red-500/5 border border-red-500/20 rounded-2xl p-8 text-center">
        <p className="text-red-300 text-sm">Failed to load document preview.</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-[#a1a1aa]">{doc.original_filename}</p>
        <a
          href={data.url}
          download={data.filename}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-xs text-violet-400 hover:text-violet-300 transition-colors"
        >
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
            <path d="M6.5 1v7M6.5 8l-2.5-2.5M6.5 8l2.5-2.5" />
            <path d="M1 10v1.5A1.5 1.5 0 002.5 13h8a1.5 1.5 0 001.5-1.5V10" />
          </svg>
          Download
        </a>
      </div>

      {isPdf && (
        <div className="rounded-2xl overflow-hidden border border-white/10 bg-white/5">
          <embed
            src={data.url}
            type="application/pdf"
            className="w-full"
            style={{ height: '75vh', minHeight: 500 }}
          />
        </div>
      )}

      {isCsv && (
        <div className="bg-white/5 border border-white/10 rounded-2xl p-4 text-center">
          <p className="text-sm text-[#a1a1aa] mb-3">CSV files cannot be previewed inline.</p>
          <a
            href={data.url}
            download={data.filename}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary inline-flex items-center gap-2 px-4 py-2 text-sm"
          >
            Download CSV
          </a>
        </div>
      )}

      {!isPdf && !isCsv && (
        <div className="bg-white/5 border border-white/10 rounded-2xl p-4 text-center">
          <p className="text-sm text-[#a1a1aa] mb-3">Preview not available for this file type.</p>
          <a
            href={data.url}
            download={data.filename}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary inline-flex items-center gap-2 px-4 py-2 text-sm"
          >
            Download File
          </a>
        </div>
      )}
    </div>
  )
}

function StatusBadge({ doc }: { doc: Document }) {
  const isCompleted = doc.status === 'completed'
  const isFailed = doc.status === 'failed'
  const label = doc.status === 'processing'
    ? STAGE_LABELS[doc.progress_stage]
    : doc.status.charAt(0).toUpperCase() + doc.status.slice(1)

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs border font-medium ${
        isCompleted
          ? 'bg-green-500/15 border-green-500/25 text-green-300'
          : isFailed
          ? 'bg-red-500/15 border-red-500/25 text-red-300'
          : 'bg-yellow-500/15 border-yellow-500/25 text-yellow-300'
      }`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          isCompleted ? 'bg-green-400' : isFailed ? 'bg-red-400' : 'bg-yellow-400 animate-pulse'
        }`}
      />
      {label}
    </span>
  )
}

function SummaryTab({ doc }: { doc: Document }) {
  if (doc.status === 'processing') {
    return (
      <div className="space-y-3">
        <div className="skeleton h-4 rounded w-full" />
        <div className="skeleton h-4 rounded w-5/6" />
        <div className="skeleton h-4 rounded w-4/6" />
        <div className="skeleton h-4 rounded w-full mt-2" />
        <div className="skeleton h-4 rounded w-3/4" />
      </div>
    )
  }

  if (!doc.summary) {
    return (
      <div className="bg-white/5 border border-white/10 rounded-2xl p-8 text-center">
        <p className="text-[#a1a1aa] text-sm">No summary available for this document.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
        <p className="text-sm text-white/80 leading-relaxed whitespace-pre-wrap">{doc.summary}</p>
      </div>
      <div className="flex items-center gap-4 text-xs text-[#a1a1aa]">
        <span>{doc.raw_chunks_count} chunks processed</span>
        {doc.completed_at && (
          <span>
            Completed{' '}
            {new Date(doc.completed_at).toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
              year: 'numeric',
            })}
          </span>
        )}
      </div>
    </div>
  )
}

function InsightsTab({ insights }: { insights: string[] }) {
  if (insights.length === 0) {
    return (
      <div className="bg-white/5 border border-white/10 rounded-2xl p-8 text-center">
        <p className="text-[#a1a1aa] text-sm">No insights extracted yet.</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {insights.map((insight, idx) => {
        const { parts, arrows } = parseInsight(insight)
        return (
          <div
            key={idx}
            className="bg-white/5 border border-white/10 rounded-2xl p-4 hover:border-white/20 transition-colors overflow-hidden"
          >
            {arrows && parts.length > 1 ? (
              <div className="flex flex-wrap items-start gap-1.5">
                {parts.map((part, i) => (
                  <span key={i} className="flex items-start gap-1.5 min-w-0">
                    <span className="text-sm text-white/80 break-words min-w-0">{part.trim()}</span>
                    {i < parts.length - 1 && (
                      <span className="text-violet-400 font-semibold text-sm flex-shrink-0">→</span>
                    )}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-white/80 leading-relaxed break-words">{insight}</p>
            )}
          </div>
        )
      })}
    </div>
  )
}

function EntitiesTab({ entities }: { entities: string[] }) {
  if (entities.length === 0) {
    return (
      <div className="bg-white/5 border border-white/10 rounded-2xl p-8 text-center">
        <p className="text-[#a1a1aa] text-sm">No entities extracted yet.</p>
      </div>
    )
  }

  return (
    <div className="flex flex-wrap gap-2">
      {entities.map((entity, idx) => (
        <span
          key={idx}
          className="border border-white/15 bg-white/5 rounded-full px-3 py-1 text-sm text-zinc-300 break-words max-w-full"
        >
          {entity}
        </span>
      ))}
    </div>
  )
}
