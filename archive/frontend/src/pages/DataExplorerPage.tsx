import { useState, useMemo } from 'react'
import { useGetAllFiles } from '../hooks/files.hooks'
import { useGetAllExtractedFiles } from '../hooks/extractedFile.hooks'
import { useGetGraphData } from '../hooks/patternRecognition.hooks'
import { RelationshipGraph } from '../components/visualizer/RelationshipGraph'

export function DataExplorerPage() {
  const { files } = useGetAllFiles()
  const { extractedFiles } = useGetAllExtractedFiles()
  const { graphData, graphIsLoading } = useGetGraphData()
  
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')

  // Derived state


  const selectedExtraction = useMemo(() => {
    return extractedFiles?.find(ef => ef.id === selectedFileId)
  }, [extractedFiles, selectedFileId])

  const selectedFile = useMemo(() => {
    if (!selectedExtraction) return null
    return files?.find(f => f.id === selectedExtraction.file_id)
  }, [files, selectedExtraction])

  // interface ExtractedContent removed

  // const extractedContent = (selectedExtraction?.extracted_data || {}) as ExtractedContent

  return (
    <div className="flex h-full min-h-0 gap-4">
      {/* Left Sidebar: Extracted File List */}
      <div className="w-1/3 bg-zinc-900 rounded-xl border border-zinc-800 flex flex-col min-h-0 shadow-lg">
        <div className="p-4 border-b border-zinc-800">
          <h2 className="text-lg font-semibold text-zinc-100 mb-2">Explorer</h2>
          <input 
            type="text" 
            placeholder="Search documents..." 
            className="w-full bg-black border border-zinc-700 rounded-lg px-4 py-2 text-sm text-zinc-200 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 shadow-inner transition-shadow"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-2 max-h-[700px]">
          {extractedFiles?.filter(f => (f.file_name || '').toLowerCase().includes(searchTerm.toLowerCase())).map(file => (
            <div 
              key={file.id}
              onClick={() => setSelectedFileId(file.id)}
              className={`p-3 rounded-lg cursor-pointer transition-all border ${
                selectedFileId === file.id 
                  ? 'bg-purple-600 border-purple-500 text-white shadow-md' 
                  : 'bg-zinc-800/50 border-zinc-800 hover:bg-zinc-800 hover:border-zinc-700 text-zinc-300'
              }`}
            >
              <div className="font-medium truncate">{file.file_name || 'Untitled'}</div>
              <div className={`text-xs mt-1 truncate ${selectedFileId === file.id ? 'text-purple-200' : 'text-zinc-500'}`}>
                {file.processed_at ? new Date(file.processed_at).toLocaleDateString() : 'N/A'}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Right Content: Inspector */}
      <div className="flex-1 bg-zinc-900 rounded-xl border border-zinc-800 flex flex-col min-h-0 overflow-hidden shadow-lg">
        {selectedFile ? (
          <div className="flex flex-col h-full bg-zinc-900/50">
            {/* Header */}
            <div className="p-6 border-b border-zinc-800 bg-zinc-900">
               <h1 className="text-2xl font-bold text-zinc-100 truncate tracking-tight">{selectedFile.name}</h1>
               <div className="flex gap-4 mt-3 text-sm text-zinc-500 font-mono">
                  <span className="bg-zinc-800 px-2 py-1 rounded">ID: {selectedFile.id.split('-')[0]}...</span>
                  <span className="bg-purple-900/30 text-purple-300 border border-purple-900/50 px-2 py-1 rounded">Type: {selectedExtraction?.file_type || 'N/A'}</span>
               </div>
               {selectedExtraction?.summary && (
                 <p className="mt-4 text-zinc-300 italic bg-black/40 p-4 rounded-lg border border-zinc-800 leading-relaxed shadow-inner">
                   "{selectedExtraction.summary}"
                 </p>
               )}
            </div>

            {/* Tabs / Content */}
            <div className="flex-1 overflow-y-auto p-6 flex flex-col max-h-[800px]">
              <div className="mb-8">
                <h3 className="text-sm font-bold text-purple-400 mb-3 uppercase tracking-widest flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                  </svg>
                  Extracted Data (JSON)
                </h3>
                {selectedExtraction?.extracted_json ? (
                  <pre className="bg-[#09090b] text-zinc-300 p-5 rounded-xl overflow-x-auto text-xs font-mono border border-zinc-800 shadow-inner leading-relaxed">
                    {JSON.stringify(selectedExtraction.extracted_json, null, 2)}
                  </pre>
                ) : (
                  <div className="text-zinc-500 italic p-4 border border-dashed border-zinc-700 rounded-lg text-center bg-zinc-900/50">No extracted data available.</div>
                )}
              </div>

              {/* Placeholder for Relationships */}
              {/* Relationship Graph */}
              <div className="flex-1 min-h-[400px] border border-zinc-800 rounded-xl overflow-hidden bg-[#09090b] shadow-inner flex flex-col">
                 <h3 className="text-sm font-bold text-purple-400 uppercase tracking-widest p-5 pb-4 border-b border-zinc-800 flex items-center gap-2 bg-zinc-900/50">
                   <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                     <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                   </svg>
                   Relationship Graph
                 </h3>
                 <div className="flex-1 relative">
                   <RelationshipGraph data={graphData} isLoading={graphIsLoading} />
                 </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-zinc-500 flex-col bg-zinc-900/30">
            <svg className="w-16 h-16 mb-4 opacity-20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <p className="font-medium text-lg">Select a file to inspect details</p>
          </div>
        )}
      </div>
    </div>
  )
}
