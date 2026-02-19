import React, { useState } from 'react';
import { api } from '../services/api';
import type { SearchResult } from '../types';
import { Link } from 'react-router-dom';

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
        <div className="max-w-4xl mx-auto p-6 min-h-screen">
            <div className="flex justify-between items-center mb-8">
                <Link to="/" className="text-gray-500 hover:text-gray-900">← Back to Dashboard</Link>
                <h1 className="text-2xl font-bold">Semantic Search</h1>
            </div>

            <form onSubmit={handleSearch} className="mb-8">
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Search for 'invoices from Acme' or 'high payload robots'..."
                        className="flex-1 p-4 text-lg border-2 border-gray-200 rounded-lg focus:border-indigo-500 focus:outline-none shadow-sm"
                    />
                    <button
                        type="submit"
                        disabled={loading}
                        className="px-8 py-4 bg-indigo-600 text-white rounded-lg font-semibold hover:bg-indigo-700 transition-colors disabled:opacity-50"
                    >
                        {loading ? 'Searching...' : 'Search'}
                    </button>
                </div>
            </form>

            <div className="space-y-6">
                {results.map((result) => (
                    <div key={result.file_id} className="p-6 bg-white rounded-lg shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                        <div className="flex justify-between items-start mb-2">
                            <h3 className="text-xl font-semibold text-gray-900">{result.file_name}</h3>
                            <span className="text-sm font-medium text-green-600 bg-green-50 px-2 py-1 rounded">
                                {Math.round(result.similarity * 100)}% Match
                            </span>
                        </div>
                        
                        <div className="text-sm text-gray-500 mb-3 flex gap-3">
                            <span className="bg-gray-100 px-2 py-0.5 rounded text-gray-700">{result.file_type}</span>
                        </div>

                        <p className="text-gray-700 leading-relaxed mb-4">
                            {result.summary}
                        </p>

                         {/* Preview of JSON data if useful, typically just showing summary is enough for basic search */}
                    </div>
                ))}

                {searched && results.length === 0 && !loading && (
                    <div className="text-center text-gray-500 py-12">
                        No documents found matching your query.
                    </div>
                )}
            </div>
        </div>
    );
};
