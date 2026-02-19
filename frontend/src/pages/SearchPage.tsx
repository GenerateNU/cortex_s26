import { useState } from 'react'
import { Layout } from '../components/layout/Layout'

type Document = {
  id: string
  title: string
  summary?: string
}

export function SearchPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Document[]>([])
  const [isSearching, setIsSearching] = useState(false)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setIsSearching(true)

    try {
      // Mock data for now
      const mockResults: Document[] = [
        {
          id: '1',
          title: `Result for "${query}"`,
          summary: 'This is a document!',
        },
        {
          id: '2',
          title: `Result for "${query}"`,
          summary: 'This is another document!',
        },
        {
          id: '3',
          title: `Result for "${query}"`,
          summary: 'This is a third document!',
        },
      ]

      setResults(mockResults)
    } catch (err) {
      console.error('Search failed', err)
    } finally {
      setIsSearching(false)
    }
  }

  return (
    <Layout>
      <div className="flex h-full min-h-0 flex-col">
        {/* Header */}
        <header className="flex-shrink-0">
          <h1 className="text-2xl font-semibold text-slate-100">
            Document Search
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Search across extracted and processed documents.
          </p>
        </header>
        {/* Search Bar */}
        <section className="mt-6 flex-shrink-0">
          <form onSubmit={handleSearch} className="flex w-full max-w-2xl gap-3">
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search documents, entities, or keywords..."
              className="flex-1 rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />

            <button
              type="submit"
              className="rounded-xl bg-indigo-600 px-5 py-2 font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
              disabled={isSearching}
            >
              {isSearching ? 'Searching…' : 'Search'}
            </button>
          </form>
        </section>
        {/* Results */}
        <section className="mt-6 flex-1 min-h-0 overflow-y-auto">
          <div className="space-y-3 pr-2">
            {results.length === 0 && !isSearching && (
              <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6 text-center text-slate-400">
                No results yet. Try searching for something.
              </div>
            )}

            {results.map(doc => (
              <div
                key={doc.id}
                className="rounded-xl border border-slate-800 bg-slate-900 p-4 transition hover:border-slate-700 hover:bg-slate-900/80"
              >
                <h2 className="text-lg font-medium text-slate-100">
                  {doc.title}
                </h2>

                {doc.summary && (
                  <p className="mt-1 text-sm text-slate-400">{doc.summary}</p>
                )}
              </div>
            ))}
          </div>
        </section>
      </div>
    </Layout>
  )
}
