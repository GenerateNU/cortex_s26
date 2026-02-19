import { useState } from 'react'
import { useGetAllRelationships, useGetFileRelationships } from '../hooks/relationships.hooks'
import { Link } from 'react-router-dom'

export function RelationshipsPage() {
  const { relationships, relationshipsIsLoading } = useGetAllRelationships()
  const [selectedRelationshipId, setSelectedRelationshipId] = useState<string | null>(null)

  return (
    <div className="flex h-full min-h-0 gap-4">
      {/* Left Sidebar: Relationship Types */}
      <div className="w-1/3 bg-slate-800 rounded-xl border border-slate-700 flex flex-col min-h-0">
        <div className="p-4 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-slate-100 mb-1">Relationships</h2>
          <p className="text-xs text-slate-400">Select a relationship type to view associated files.</p>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {relationshipsIsLoading ? (
            <div className="p-4 text-center text-slate-500 text-sm">Loading types...</div>
          ) : relationships.length === 0 ? (
            <div className="p-4 text-center text-slate-500 text-sm">No relationship types defined.</div>
          ) : (
            relationships.map(rel => (
              <div 
                key={rel.relationship_id} 
                onClick={() => setSelectedRelationshipId(rel.relationship_id)}
                className={`p-3 rounded-lg cursor-pointer transition-all border ${
                  selectedRelationshipId === rel.relationship_id 
                    ? 'bg-primary-900/30 border-primary-500/50 ring-1 ring-primary-500/30' 
                    : 'bg-slate-800 border-transparent hover:bg-slate-700'
                }`}
              >
                <div className={`font-medium ${selectedRelationshipId === rel.relationship_id ? 'text-primary-300' : 'text-slate-200'}`}>
                  {rel.relationship_name}
                </div>
                <div className="text-xs text-slate-500 mt-1 line-clamp-2">
                  {rel.relationship_description}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Right Content: Associated Files */}
      <div className="flex-1 bg-slate-800 rounded-xl border border-slate-700 flex flex-col min-h-0 overflow-hidden">
        {selectedRelationshipId ? (
          <RelationshipDetailView relationshipId={selectedRelationshipId} />
        ) : (
          <div className="flex-1 flex items-center justify-center text-slate-500 flex-col opacity-50">
            <svg className="w-16 h-16 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
            <p>Select a relationship to view connections</p>
          </div>
        )}
      </div>
    </div>
  )
}

function RelationshipDetailView({ relationshipId }: { relationshipId: string }) {
  const { fileRelationships, fileRelationshipsIsLoading } = useGetFileRelationships(relationshipId)

  if (fileRelationshipsIsLoading) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-500">
        Loading connections...
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-slate-700 bg-slate-800">
        <h2 className="text-xl font-bold text-slate-100">Associated Files</h2>
        <p className="text-sm text-slate-400 mt-1">
          {fileRelationships.length} file{fileRelationships.length !== 1 ? 's' : ''} found with this relationship.
        </p>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4">
        {fileRelationships.length === 0 ? (
          <div className="text-center py-10 text-slate-500 italic border-2 border-dashed border-slate-700 rounded-lg">
            No files have been tagged with this relationship yet.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {fileRelationships.map((item) => (
              <div key={`${item.file_id}-${item.relationship_id}`} className="bg-slate-900 border border-slate-700 rounded-lg p-4 hover:border-slate-600 transition-colors">
                 <div className="flex justify-between items-start mb-2">
                    <span className={`inline-block px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider
                      ${item.source === 'ai_inference' ? 'bg-purple-900/30 text-purple-300 border border-purple-800' : 
                        item.source === 'filename-rule' ? 'bg-blue-900/30 text-blue-300 border border-blue-800' :
                        'bg-slate-800 text-slate-400 border border-slate-700'
                      }
                    `}>
                      {item.source || 'MANUAL'}
                    </span>
                    {item.confidence_score && (
                      <span className="text-xs text-slate-500" title="Confidence Score">
                        {Math.round(item.confidence_score * 100)}%
                      </span>
                    )}
                 </div>
                 
                 <h3 className="text-slate-200 font-medium truncate mb-1" title={item.file?.name}>
                    {item.file?.name || 'Unknown File'}
                 </h3>
                 
                 <div className="flex items-center justify-between mt-3 text-xs text-slate-500">
                    <span>
                       {item.file?.type || 'Unknown Type'}
                    </span>
                    <Link to={`/explorer?fileId=${item.file_id}`} className="text-primary-400 hover:text-primary-300 hover:underline">
                      View File
                    </Link>
                 </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
