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
        <div className="space-y-4">
            {files.map((file) => (
                <div key={file.file_id} className="p-4 bg-white shadow rounded-lg border border-gray-200">
                    <div className="flex justify-between items-start">
                        <div>
                            <h3 className="text-lg font-bold text-gray-900">{file.file_name}</h3>
                            <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${
                                getFileTypeColor(file.file_type)
                            }`}>
                                {file.file_type || 'Processing...'}
                            </span>
                        </div>
                        <div className="text-xs text-gray-500">
                            {new Date(file.uploaded_at).toLocaleDateString()}
                        </div>
                    </div>
                    
                    <p className="mt-2 text-sm text-gray-600">
                        {file.summary || 'Generating summary...'}
                    </p>

                    {/* Relationships Section */}
                    {file.relationships.length > 0 && (
                        <div className="mt-3">
                            <h4 className="text-xs font-uppercase text-gray-400 mb-1">Detected Relationships</h4>
                            <div className="flex flex-wrap gap-2">
                                {file.relationships.map((rel, idx) => (
                                    <div key={idx} className="flex items-center px-2 py-1 bg-indigo-50 text-indigo-700 rounded text-xs border border-indigo-100" title={rel.description}>
                                        <span className="font-medium mr-1">{rel.name}</span>
                                        <span className="text-indigo-400">({(rel.score * 100).toFixed(0)}%)</span>
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
        case 'PO': return 'bg-blue-100 text-blue-800';
        case 'RFQ': return 'bg-purple-100 text-purple-800';
        case 'ProdSpec': return 'bg-green-100 text-green-800';
        case 'Sales': return 'bg-yellow-100 text-yellow-800';
        case 'Customers': return 'bg-pink-100 text-pink-800';
        default: return 'bg-gray-100 text-gray-800';
    }
};
