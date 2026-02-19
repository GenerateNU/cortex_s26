import React, { useEffect, useState } from 'react';
import { supabase } from '../../config/supabase.config';
import type { Document } from '../../types';

interface FileWithRelations extends Document {
    relationships: { name: string; description: string; score: number }[];
}

export const FileList: React.FC = () => {
    const [files, setFiles] = useState<FileWithRelations[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchFiles = async () => {
        setLoading(true);
        // 1. Fetch raw_files + extracted_files
        // Supabase join syntax: raw_files -> extracted_files
        const { data: rawData, error } = await supabase
            .from('raw_files')
            .select(`
                *,
                extracted_files (
                    file_type,
                    summary,
                    processed_at,
                    extracted_json
                )
            `)
            .order('uploaded_at', { ascending: false });

        if (error) {
            console.error(error);
            return;
        }

        // 2. Fetch relationships for these files
        const { data: relData } = await supabase
            .from('file_relationships')
            .select(`
                file_id,
                confidence_score,
                relationships (
                    relationship_name,
                    relationship_description
                )
            `);

        // Map relationships by file_id
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const relMap: Record<string, any[]> = {};
        if (relData) {
            relData.forEach((r) => {
                if (!relMap[r.file_id]) relMap[r.file_id] = [];
                if (r.relationships) {
                    const rel = r.relationships as { relationship_name: string; relationship_description: string };
                    relMap[r.file_id].push({
                        name: rel.relationship_name,
                        description: rel.relationship_description,
                        score: r.confidence_score
                    });
                }
            });
        }


        // Transform data
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const processedFiles = (rawData || []).map((raw: any) => {
            const extracted = raw.extracted_files?.[0] || {};
            return {
                ...raw, // file_id, file_name, etc.
                ...extracted, // summary, file_type
                relationships: relMap[raw.file_id] || []
            };
        });

        setFiles(processedFiles);
        setLoading(false);
    };

    useEffect(() => {
        fetchFiles();
        // Poll for updates (poor man's realtime)
        const interval = setInterval(fetchFiles, 5000);
        return () => clearInterval(interval);
    }, []);

    if (loading && files.length === 0) return <div>Loading documents...</div>;

    return (
        <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2">
            {files.map((file) => (
                <div key={file.file_id} className="p-4 bg-zinc-900 shadow-lg rounded-xl border border-zinc-800 hover:border-zinc-700 transition-colors">
                    <div className="flex justify-between items-start">
                        <div>
                            <h3 className="text-lg font-bold text-zinc-100">{file.file_name}</h3>
                            <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold mt-1 border ${
                                getFileTypeColor(file.file_type)
                            }`}>
                                {file.file_type || 'Processing...'}
                            </span>
                        </div>
                        <div className="text-xs text-zinc-500 font-medium bg-zinc-800 px-2 py-1 rounded">
                            {new Date(file.uploaded_at).toLocaleDateString()}
                        </div>
                    </div>
                    
                    <p className="mt-3 text-sm text-zinc-400 leading-relaxed">
                        {file.summary || 'Generating summary...'}
                    </p>

                    {/* Relationships Section */}
                    {file.relationships.length > 0 && (
                        <div className="mt-4 pt-4 border-t border-zinc-800">
                            <h4 className="text-xs font-semibold tracking-wider uppercase text-zinc-500 mb-2 flex items-center gap-1">
                                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                                </svg>
                                Detected Relationships
                            </h4>
                            <div className="flex flex-wrap gap-2">
                                {file.relationships.map((rel, idx) => (
                                    <div key={idx} className="flex items-center px-2 py-1 bg-purple-900/40 text-purple-200 rounded-md text-xs border border-purple-500/30 backdrop-blur-sm" title={rel.description}>
                                        <span className="font-medium mr-1.5">{rel.name}</span>
                                        <span className="text-purple-400 font-mono text-[10px] bg-purple-950/50 px-1 rounded">
                                            {(rel.score * 100).toFixed(0)}%
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
};

const getFileTypeColor = (type?: string) => {
    switch (type) {
        case 'PO': return 'bg-blue-900/30 text-blue-300 border-blue-900/50';
        case 'RFQ': return 'bg-purple-900/30 text-purple-300 border-purple-900/50';
        case 'ProdSpec': return 'bg-emerald-900/30 text-emerald-300 border-emerald-900/50';
        case 'Sales': return 'bg-amber-900/30 text-amber-300 border-amber-900/50';
        case 'Customers': return 'bg-pink-900/30 text-pink-300 border-pink-900/50';
        default: return 'bg-zinc-800 text-zinc-300 border-zinc-700';
    }
};
