import React, { useState } from 'react';
import { Layout } from '../components/layout/Layout';
import { api } from '../services/api';
import type { SearchResult } from '../types';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/ui/StatusBadge';

export const SearchPage: React.FC = () => {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<SearchResult[]>([]);
    const [loading, setLoading] = useState(false);
    const [searched, setSearched] = useState(false);

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        try {
            const data = await api.search(query);
            setResults(data);
            setSearched(true);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Layout>
            <div className="flex flex-col h-full min-h-0 space-y-6">
                
                {/* Header Section */}
                <div className="flex justify-between items-center">
                    <div>
                        <h1 className="text-3xl font-bold text-zinc-100 mb-2 tracking-tight">Search & Organize</h1>
                        <p className="text-zinc-500 font-medium">Find documents using AI or automatically organize your data.</p>
                    </div>
                </div>

                {/* Search Bar Section */}
                <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-lg">
                    <form onSubmit={handleSearch}>
                        <div className="flex gap-4">
                            <input
                                type="text"
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder="Search for 'invoices from Acme' or 'high payload robots'..."
                                className="flex-1 px-6 py-4 text-lg bg-[#09090b] border border-zinc-700 text-zinc-100 rounded-xl focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 focus:outline-none shadow-inner transition-all placeholder:text-zinc-600"
                            />
                            <Button
                                type="submit"
                                disabled={loading}
                                className="px-8 py-4 text-lg font-bold shadow-md hover:shadow-lg transition-all"
                            >
                                {loading ? 'Searching...' : 'Search'}
                            </Button>
                        </div>
                    </form>
                </div>

                {/* Results Section */}
                <div className="flex-1 overflow-y-auto min-h-0">
                    <div className="space-y-4 pr-2">
                        {results.map((result) => (
                            <div key={result.file_id} className="p-6 bg-zinc-900/80 rounded-2xl border border-zinc-800 hover:border-zinc-700 transition-all hover:shadow-md">
                                <div className="flex justify-between items-start mb-4">
                                    <h3 className="text-xl font-bold text-zinc-100">{result.file_name}</h3>
                                    <StatusBadge 
                                        status="success" 
                                        label={`${Math.round(result.similarity * 100)}% Match`} 
                                    />
                                </div>
                                
                                {result.file_type && (
                                    <div className="mb-4">
                                        <span className="bg-purple-900/30 text-purple-300 px-3 py-1 text-xs uppercase tracking-wider rounded-md font-bold border border-purple-900/50">
                                            {result.file_type}
                                        </span>
                                    </div>
                                )}

                                <p className="text-zinc-400 leading-relaxed text-sm bg-black/20 p-4 rounded-xl border border-zinc-800/50">
                                    {result.summary}
                                </p>
                            </div>
                        ))}

                        {searched && results.length === 0 && !loading && (
                            <div className="text-center bg-zinc-900/50 border-2 border-dashed border-zinc-700/50 rounded-2xl p-16 mt-8">
                                <svg
                                  className="mx-auto h-12 w-12 text-zinc-600 mb-4"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  stroke="currentColor"
                                >
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                </svg>
                                <h3 className="text-lg font-bold text-zinc-300 mb-2">No results found</h3>
                                <p className="text-zinc-500">We couldn't find any documents matching your search.</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </Layout>
    );
};
