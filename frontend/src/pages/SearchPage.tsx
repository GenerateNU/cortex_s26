import { useState, useCallback, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import Navbar from '../components/Navbar'
import {
  searchDocuments,
  type SearchResult,
  type DocumentSource,
} from '../services/api'

const DOC_TYPE_COLORS: Record<string, string> = {
  RFQ: 'bg-blue-500/15 border-blue-500/25 text-blue-300',
  PO: 'bg-green-500/15 border-green-500/25 text-green-300',
  CFG: 'bg-amber-500/15 border-amber-500/25 text-amber-300',
  'Client CSV': 'bg-rose-500/15 border-rose-500/25 text-rose-300',
  'Sales CSV': 'bg-violet-500/15 border-violet-500/25 text-violet-300',
}

const EXAMPLE_QUERIES = [
  'What are the key deliverables in the RFQ?',
  'Summarize the purchase order terms',
  'List all vendor entities mentioned',
  'What are the main product specifications?',
  'Which clients have submitted orders?',
  'What decisions were made last quarter?',
]

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [submittedQuery, setSubmittedQuery] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const { data, isFetching, isError, error, refetch } = useQuery({
    queryKey: ['search', submittedQuery],
    queryFn: () => searchDocuments(submittedQuery),
    enabled: submittedQuery.trim().length > 0,
    staleTime: 5000,
    retry: 1,
  })

  const handleSubmit = useCallback(() => {
    const trimmed = query.trim()
    if (!trimmed) return
    if (trimmed === submittedQuery) refetch()
    else setSubmittedQuery(trimmed)
  }, [query, submittedQuery, refetch])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') handleSubmit()
    },
    [handleSubmit]
  )

  const handleExampleClick = useCallback((q: string) => {
    setQuery(q)
    setSubmittedQuery(q)
  }, [])

  const hasSubmitted = submittedQuery.length > 0

  return (
    <div className="relative min-h-screen bg-black overflow-x-hidden">
      <Navbar />

      <div
        className="pointer-events-none fixed inset-0 z-0"
        style={{
          background:
            'radial-gradient(ellipse at 50% 40%, rgba(124,58,237,0.25) 0%, transparent 65%)',
        }}
      />

      <div className="pointer-events-none fixed top-1/4 right-8 opacity-10 z-0 hidden lg:block">
        <svg width="300" height="300" viewBox="0 0 300 300" fill="none">
          <circle
            cx="150"
            cy="150"
            r="140"
            stroke="#7c3aed"
            strokeWidth="1.5"
            strokeDasharray="4 8"
          />
          <circle
            cx="150"
            cy="150"
            r="100"
            stroke="#8b5cf6"
            strokeWidth="1"
            strokeDasharray="3 6"
          />
          <circle
            cx="150"
            cy="150"
            r="60"
            stroke="#a78bfa"
            strokeWidth="0.75"
            strokeDasharray="2 5"
          />
        </svg>
      </div>

      <main className="relative z-10 flex flex-col items-center px-4 pt-20 pb-24">
        {/* Search bar */}
        <div
          className={`w-full max-w-2xl flex flex-col items-center transition-all duration-500 ${hasSubmitted ? 'pt-10' : 'pt-24'}`}
        >
          {!hasSubmitted && (
            <div className="flex flex-col items-center mb-12 text-center">
              <div className="mb-5 inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-violet-500/30 bg-violet-600/10 text-violet-300 text-xs font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
                Document Intelligence
              </div>
              <h1 className="text-4xl md:text-5xl font-bold tracking-tight leading-tight text-white mb-4">
                Ask Cortex Anything
              </h1>
              <p className="text-base text-[#a1a1aa] max-w-md leading-relaxed">
                Search your knowledge graph with natural language
              </p>
            </div>
          )}

          <div className="w-full">
            <div className="relative flex items-center bg-white/5 border border-white/10 rounded-xl focus-within:border-violet-500/40 focus-within:bg-white/[0.07] transition-all duration-200">
              <div className="pl-4 pr-2 text-white/30 flex-shrink-0">
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 18 18"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.75"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <circle cx="8" cy="8" r="5.5" />
                  <line x1="12.5" y1="12.5" x2="16" y2="16" />
                </svg>
              </div>
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question about your documents…"
                className="flex-1 bg-transparent text-white placeholder-white/25 text-base py-4 px-3 outline-none"
                autoFocus
              />
              {query.length > 0 && (
                <button
                  onClick={() => {
                    setQuery('')
                    inputRef.current?.focus()
                  }}
                  className="px-3 text-white/30 hover:text-white/60 transition-colors"
                  aria-label="Clear"
                >
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 14 14"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.75"
                    strokeLinecap="round"
                  >
                    <line x1="3" y1="3" x2="11" y2="11" />
                    <line x1="11" y1="3" x2="3" y2="11" />
                  </svg>
                </button>
              )}
              <div className="pr-2">
                <button
                  onClick={handleSubmit}
                  disabled={!query.trim() || isFetching}
                  className="btn-primary px-4 py-2 text-sm"
                >
                  {isFetching ? <Spinner /> : 'Search'}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Results */}
        <div className="w-full max-w-2xl mt-8">
          {isFetching && <SearchSkeletons />}

          {!isFetching && isError && (
            <div className="p-6 border border-red-500/20 bg-red-500/5 rounded-2xl">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400 flex-shrink-0 mt-0.5">
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 14 14"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.75"
                    strokeLinecap="round"
                  >
                    <circle cx="7" cy="7" r="5.5" />
                    <line x1="7" y1="4.5" x2="7" y2="7.5" />
                    <circle cx="7" cy="9.5" r="0.5" fill="currentColor" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-medium text-red-300 mb-1">
                    Search failed
                  </p>
                  <p className="text-xs text-[#a1a1aa]">
                    {error instanceof Error
                      ? error.message
                      : 'Something went wrong.'}
                  </p>
                  <button
                    onClick={() => refetch()}
                    className="mt-3 text-xs text-violet-400 hover:text-violet-300 transition-colors"
                  >
                    Try again →
                  </button>
                </div>
              </div>
            </div>
          )}

          {!isFetching && !isError && data && (
            <div className="space-y-3">
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm text-[#a1a1aa]">
                  <span className="text-white font-medium">
                    {data.total ?? data.results?.length ?? 0}
                  </span>{' '}
                  result{data.results?.length !== 1 ? 's' : ''} for{' '}
                  <span className="text-white font-medium">
                    "{submittedQuery}"
                  </span>
                </p>
                <span className="text-[10px] px-2.5 py-1 rounded-full border border-violet-500/20 bg-violet-500/10 text-violet-300">
                  Knowledge Graph
                </span>
              </div>

              {data.results && data.results.length > 0 ? (
                data.results.map((result, idx) => (
                  <ResultCard key={idx} result={result} index={idx} />
                ))
              ) : (
                <EmptyResults query={submittedQuery} />
              )}
            </div>
          )}

          {!isFetching && !isError && !data && !hasSubmitted && (
            <div className="mt-16 flex flex-col items-center gap-6">
              <p className="text-sm text-white/30">Try one of these examples</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
                {EXAMPLE_QUERIES.map(q => (
                  <button
                    key={q}
                    onClick={() => handleExampleClick(q)}
                    className="text-left px-4 py-3 rounded-xl border border-white/10 bg-white/[0.03] text-xs text-[#a1a1aa] hover:text-white hover:border-white/20 hover:bg-white/[0.06] transition-all duration-200 leading-snug"
                  >
                    <span className="text-violet-500 mr-1.5">↗</span>
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

// ── ResultCard ────────────────────────────────────────────────────────────────

function ResultCard({
  result,
  index,
}: {
  result: SearchResult
  index: number
}) {
  const [isExpanded, setIsExpanded] = useState(false)

  const wordCount = result.text.trim().split(/\s+/).length
  const isLong = wordCount > 40

  return (
    <div
      onClick={() => setIsExpanded(v => !v)}
      className={`
        group relative border rounded-2xl cursor-pointer select-none
        transition-all duration-300 overflow-hidden
        ${
          isExpanded
            ? 'bg-white/[0.06] border-violet-500/30 shadow-[0_0_0_1px_rgba(124,58,237,0.15),0_8px_32px_rgba(0,0,0,0.4)]'
            : 'bg-white/[0.03] border-white/10 hover:bg-white/[0.05] hover:border-white/20'
        }
      `}
      style={{ animationDelay: `${index * 50}ms` }}
    >
      {/* Top strip — always visible */}
      <div className="p-5">
        <div className="flex items-start gap-3">
          {/* Index badge */}
          <span
            className={`
            flex-shrink-0 w-6 h-6 rounded-md flex items-center justify-center text-[11px] font-semibold mt-0.5
            transition-colors duration-200
            ${isExpanded ? 'bg-violet-500/20 text-violet-300' : 'bg-white/5 text-white/30'}
          `}
          >
            {index + 1}
          </span>

          {/* Text — clamped when collapsed, full when expanded */}
          <div className="flex-1 min-w-0">
            <p
              className={`text-sm text-white/80 leading-relaxed break-words transition-all duration-300 ${!isExpanded && isLong ? 'line-clamp-2' : ''}`}
            >
              {result.text}
            </p>
            {!isExpanded && isLong && (
              <span className="text-xs text-violet-400 mt-1 inline-block">
                Read more
              </span>
            )}
          </div>

          {/* Chevron */}
          <svg
            className={`flex-shrink-0 w-4 h-4 text-white/20 transition-transform duration-300 mt-0.5 ${isExpanded ? 'rotate-180 text-violet-400' : 'group-hover:text-white/40'}`}
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="4,6 8,10 12,6" />
          </svg>
        </div>

        {/* Collapsed footer — document pill */}
        {!isExpanded &&
          (result.sources?.[0]?.original_filename || result.dataset_name) && (
            <div className="mt-3 ml-9 flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] border border-violet-500/20 bg-violet-500/10 text-violet-300">
                <svg
                  width="9"
                  height="9"
                  viewBox="0 0 9 9"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                >
                  <path d="M1 2.5h7M1 4.5h5M1 6.5h3" />
                </svg>
                {result.sources?.[0]?.original_filename ??
                  result.dataset_name!.replace(/_/g, ' ')}
              </span>
            </div>
          )}
      </div>

      {/* Expanded panel */}
      {isExpanded && (
        <div onClick={e => e.stopPropagation()}>
          {/* Divider */}
          <div className="mx-5 h-px bg-white/[0.06]" />

          <div className="p-5 space-y-4">
            {/* Document + word count metadata row */}
            <div className="flex items-center gap-2 flex-wrap">
              {(result.sources?.[0]?.original_filename ||
                result.dataset_name) && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs border border-violet-500/20 bg-violet-500/10 text-violet-300">
                  <svg
                    width="10"
                    height="10"
                    viewBox="0 0 10 10"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  >
                    <path d="M1 2.5h8M1 5h6M1 7.5h4" />
                  </svg>
                  {result.sources?.[0]?.original_filename ??
                    result.dataset_name!.replace(/_/g, ' ')}
                </span>
              )}
              <span className="text-[11px] text-white/25">
                {wordCount} words
              </span>
            </div>

            {/* Source documents */}
            {result.sources && result.sources.length > 0 && (
              <div>
                <p className="text-[11px] font-medium text-white/30 uppercase tracking-wider mb-2">
                  Source Documents
                </p>
                <div className="space-y-2">
                  {result.sources.map(source => (
                    <SourceCard key={source.id} source={source} />
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ── SourceCard ────────────────────────────────────────────────────────────────

function SourceCard({ source }: { source: DocumentSource }) {
  const ext = source.original_filename.split('.').pop()?.toLowerCase()
  const typeColor = source.document_type
    ? (DOC_TYPE_COLORS[source.document_type] ??
      'bg-white/5 border-white/15 text-zinc-300')
    : null

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    window.open(`/documents/${source.id}`, '_blank', 'noopener,noreferrer')
  }

  return (
    <button
      onClick={handleClick}
      className="w-full text-left flex items-center gap-3 p-3 rounded-xl border border-white/[0.07] bg-white/[0.03] hover:bg-white/[0.07] hover:border-white/15 transition-all duration-150 group/source"
    >
      {/* File icon */}
      <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center flex-shrink-0">
        <svg
          width="14"
          height="14"
          viewBox="0 0 14 14"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={
            ext === 'pdf'
              ? 'text-red-400'
              : ext === 'csv'
                ? 'text-green-400'
                : 'text-blue-400'
          }
        >
          <path d="M9 1.5H4a1 1 0 00-1 1v9a1 1 0 001 1h6a1 1 0 001-1V4L9 1.5z" />
          <polyline points="9,1.5 9,4 11.5,4" />
        </svg>
      </div>

      {/* Name + type */}
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-white/80 truncate group-hover/source:text-white transition-colors">
          {source.original_filename}
        </p>
        {source.dataset_name && (
          <p className="text-[11px] text-white/30 mt-0.5 truncate">
            {source.dataset_name.replace(/_/g, ' ')}
          </p>
        )}
      </div>

      {/* Type badge */}
      <div className="flex items-center gap-2 flex-shrink-0">
        {typeColor && (
          <span
            className={`px-2 py-0.5 rounded-full text-[10px] font-medium border ${typeColor}`}
          >
            {source.document_type}
          </span>
        )}
        {/* View in Graph */}
        {source.dataset_name && (
          <Link
            to={`/graph?dataset=${encodeURIComponent(source.dataset_name)}`}
            onClick={e => e.stopPropagation()}
            className="w-7 h-7 rounded-lg bg-white/[0.04] border border-white/[0.06] flex items-center justify-center text-white/20 hover:text-violet-400 hover:border-violet-500/25 hover:bg-violet-500/10 transition-all"
            title="View in Graph"
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 12 12"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.2"
            >
              <circle cx="6" cy="3" r="1.5" />
              <circle cx="2.5" cy="9" r="1.5" />
              <circle cx="9.5" cy="9" r="1.5" />
              <line x1="5.2" y1="4.3" x2="3.3" y2="7.7" />
              <line x1="6.8" y1="4.3" x2="8.7" y2="7.7" />
            </svg>
          </Link>
        )}
        {/* Arrow */}
        <svg
          width="12"
          height="12"
          viewBox="0 0 12 12"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-white/20 group-hover/source:text-violet-400 transition-colors"
        >
          <line x1="2" y1="10" x2="10" y2="2" />
          <polyline points="4,2 10,2 10,8" />
        </svg>
      </div>
    </button>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function EmptyResults({ query }: { query: string }) {
  return (
    <div className="p-12 flex flex-col items-center text-center gap-3 rounded-2xl border border-white/10 bg-white/[0.02]">
      <div className="w-12 h-12 rounded-full bg-white/5 border border-white/10 flex items-center justify-center mb-1">
        <svg
          width="20"
          height="20"
          viewBox="0 0 20 20"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          className="text-white/25"
        >
          <circle cx="9" cy="9" r="6" />
          <line x1="14" y1="14" x2="18" y2="18" />
        </svg>
      </div>
      <p className="text-sm font-medium text-white/50">No results found</p>
      <p className="text-xs text-[#a1a1aa] max-w-xs">
        No documents matched <span className="text-white/60">"{query}"</span>.
        Try rephrasing your query.
      </p>
    </div>
  )
}

function SearchSkeletons() {
  return (
    <div className="space-y-3">
      {[0, 1, 2].map(i => (
        <div
          key={i}
          className="bg-white/[0.03] border border-white/10 rounded-2xl p-5"
        >
          <div className="flex gap-3">
            <div className="skeleton w-6 h-6 rounded-md flex-shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="skeleton h-3 rounded w-full" />
              <div className="skeleton h-3 rounded w-5/6" />
              <div className="skeleton h-3 rounded w-4/6" />
            </div>
          </div>
          <div className="skeleton h-4 rounded-full w-24 mt-4 ml-9" />
        </div>
      ))}
    </div>
  )
}

function Spinner() {
  return (
    <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
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
  )
}
