import { useState, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import Navbar from '../components/Navbar'
import { searchDocuments, type SearchResult } from '../services/api'

const EXAMPLE_QUERIES = [
  'What are the key deliverables in the RFQ?',
  'Summarize the purchase order terms',
  'Which clients have outstanding invoices?',
  'What are the main risk factors identified?',
  'List all vendor entities mentioned',
  'What decisions were made last quarter?',
]

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [submittedQuery, setSubmittedQuery] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

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
    if (trimmed === submittedQuery) {
      refetch()
    } else {
      setSubmittedQuery(trimmed)
    }
  }, [query, submittedQuery, refetch])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') handleSubmit()
    },
    [handleSubmit],
  )

  const handleExampleClick = useCallback((q: string) => {
    setQuery(q)
    setSubmittedQuery(q)
  }, [])

  const hasSubmitted = submittedQuery.length > 0

  return (
    <div className="relative min-h-screen bg-black overflow-x-hidden">
      <Navbar />

      {/* Purple radial glow */}
      <div
        className="pointer-events-none fixed inset-0 z-0"
        style={{
          background:
            'radial-gradient(ellipse at 50% 40%, rgba(124,58,237,0.25) 0%, transparent 65%)',
        }}
      />

      {/* Decorative dotted circle motif */}
      <div className="pointer-events-none fixed top-1/4 right-8 opacity-10 z-0 hidden lg:block">
        <svg width="300" height="300" viewBox="0 0 300 300" fill="none">
          <circle cx="150" cy="150" r="140" stroke="#7c3aed" strokeWidth="1.5" strokeDasharray="4 8" />
          <circle cx="150" cy="150" r="100" stroke="#8b5cf6" strokeWidth="1" strokeDasharray="3 6" />
          <circle cx="150" cy="150" r="60" stroke="#a78bfa" strokeWidth="0.75" strokeDasharray="2 5" />
        </svg>
      </div>

      <main className="relative z-10 flex flex-col items-center px-4 pt-20 pb-24">
        {/* Hero / Search area */}
        <div className={`w-full max-w-2xl flex flex-col items-center transition-all duration-500 ${hasSubmitted ? 'pt-10' : 'pt-24'}`}>
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

          {/* Search input */}
          <div className="w-full">
            <div className="relative flex items-center bg-white/5 border border-white/10 rounded-xl focus-within:border-white/20 transition-all duration-200">
              <div className="pl-4 pr-2 text-white/30 flex-shrink-0">
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="8" cy="8" r="5.5" />
                  <line x1="12.5" y1="12.5" x2="16" y2="16" />
                </svg>
              </div>

              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question about your documents…"
                className="flex-1 bg-transparent text-white placeholder-white/25 text-base py-4 px-3 outline-none"
                autoFocus
              />

              {query.length > 0 && (
                <button
                  onClick={() => { setQuery(''); inputRef.current?.focus() }}
                  className="px-3 text-white/30 hover:text-white/60 transition-colors"
                  aria-label="Clear"
                >
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round">
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

        {/* Results area */}
        <div className="w-full max-w-2xl mt-8">
          {/* Loading skeletons */}
          {isFetching && <SearchSkeletons />}

          {/* Error */}
          {!isFetching && isError && (
            <div className="glass-card p-6 border border-red-500/20 bg-red-500/5 rounded-2xl">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400 flex-shrink-0 mt-0.5">
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round">
                    <circle cx="7" cy="7" r="5.5" />
                    <line x1="7" y1="4.5" x2="7" y2="7.5" />
                    <circle cx="7" cy="9.5" r="0.5" fill="currentColor" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-medium text-red-300 mb-1">Search failed</p>
                  <p className="text-xs text-[#a1a1aa]">
                    {error instanceof Error ? error.message : 'Something went wrong.'}
                  </p>
                  <button onClick={() => refetch()} className="mt-3 text-xs text-violet-400 hover:text-violet-300 transition-colors">
                    Try again →
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Results */}
          {!isFetching && !isError && data && (
            <div className="space-y-4 animate-slide-up">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-[#a1a1aa]">
                  {data.total ?? data.results?.length ?? 0} result{data.results?.length !== 1 ? 's' : ''} for{' '}
                  <span className="text-white font-medium">"{submittedQuery}"</span>
                </p>
                <span className="pill-chip text-xs border-violet-500/20 bg-violet-500/10 text-violet-300">
                  Graph Completion
                </span>
              </div>

              {data.results && data.results.length > 0 ? (
                data.results.map((result, idx) => (
                  <ResultCard key={idx} result={result} index={idx} navigate={navigate} />
                ))
              ) : (
                <EmptyResults query={submittedQuery} />
              )}
            </div>
          )}

          {/* Initial empty state */}
          {!isFetching && !isError && !data && !hasSubmitted && (
            <div className="mt-16 flex flex-col items-center gap-6">
              <p className="text-sm text-white/30">Try one of these examples</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
                {EXAMPLE_QUERIES.map((q) => (
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

// ── Sub-components ────────────────────────────────────────────────────────────

function ResultCard({
  result,
  index,
  navigate,
}: {
  result: SearchResult
  index: number
  navigate: ReturnType<typeof useNavigate>
}) {
  const dataset = result.metadata?.dataset

  return (
    <div
      className="bg-white/5 border border-white/10 rounded-2xl p-5 hover:border-white/20 hover:bg-white/[0.07] transition-all duration-200"
      style={{ animationDelay: `${index * 60}ms` }}
    >
      <div className="flex items-start gap-2 mb-3">
        <span className="flex items-center justify-center w-5 h-5 rounded bg-white/5 border border-white/10 text-[10px] font-mono text-white/30 flex-shrink-0 mt-0.5">
          {index + 1}
        </span>
        <p className="text-sm text-white/80 leading-relaxed flex-1">{result.text}</p>
      </div>

      <div className="flex items-center justify-between mt-3 pt-3 border-t border-white/[0.06]">
        {dataset ? (
          <button
            onClick={() => navigate(`/documents?dataset=${encodeURIComponent(dataset)}`)}
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs border border-violet-500/20 bg-violet-500/10 text-violet-300 hover:border-violet-500/40 hover:bg-violet-500/20 transition-all duration-200"
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
              <path d="M1 3h8M1 5h6M1 7h4" />
            </svg>
            {dataset}
          </button>
        ) : (
          <span />
        )}
        {result.score !== null && result.score !== undefined && (
          <span className="pill-chip text-xs">
            {Math.round(result.score * 100)}% match
          </span>
        )}
      </div>
    </div>
  )
}

function EmptyResults({ query }: { query: string }) {
  return (
    <div className="glass-card p-12 flex flex-col items-center text-center gap-3 rounded-2xl">
      <div className="w-12 h-12 rounded-full bg-white/5 border border-white/10 flex items-center justify-center mb-1">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="text-white/25">
          <circle cx="9" cy="9" r="6" />
          <line x1="14" y1="14" x2="18" y2="18" />
        </svg>
      </div>
      <p className="text-sm font-medium text-white/50">No results found</p>
      <p className="text-xs text-[#a1a1aa] max-w-xs">
        No documents matched <span className="text-white/60">"{query}"</span>. Try rephrasing your query.
      </p>
    </div>
  )
}

function SearchSkeletons() {
  return (
    <div className="space-y-4">
      {[0, 1, 2].map((i) => (
        <div key={i} className="bg-white/5 border border-white/10 rounded-2xl p-5">
          <div className="flex gap-2 mb-3">
            <div className="skeleton w-5 h-5 rounded flex-shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="skeleton h-3 rounded w-full" />
              <div className="skeleton h-3 rounded w-5/6" />
              <div className="skeleton h-3 rounded w-4/6" />
            </div>
          </div>
          <div className="skeleton h-5 rounded-full w-24 mt-3" />
        </div>
      ))}
    </div>
  )
}

function Spinner() {
  return (
    <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
  )
}
