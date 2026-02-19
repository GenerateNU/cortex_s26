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
  const filteredFiles = useMemo(() => {
    if (!files) return []
    return files.filter(f => 
      f.name.toLowerCase().includes(searchTerm.toLowerCase())
    )
  }, [files, searchTerm])

  const selectedFile = useMemo(() => {
    return files?.find(f => f.id === selectedFileId)
  }, [files, selectedFileId])

  const selectedExtraction = useMemo(() => {
    return extractedFiles?.find(ef => ef.file_id === selectedFileId)
  }, [extractedFiles, selectedFileId])

  // interface ExtractedContent removed

  // const extractedContent = (selectedExtraction?.extracted_data || {}) as ExtractedContent

  return (
    <div className="flex h-full min-h-0 gap-4">
      {/* Left Sidebar: File List */}
      <div className="w-1/3 bg-slate-800 rounded-xl border border-slate-700 flex flex-col min-h-0">
        <div className="p-4 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-slate-100 mb-2">Explorer</h2>
          <input 
            type="text" 
            placeholder="Search files..." 
            className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-primary-500"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {filteredFiles.map(file => (
            <div 
              key={file.id}
              onClick={() => setSelectedFileId(file.id)}
              className={`p-3 rounded cursor-pointer transition-colors ${
                selectedFileId === file.id 
                  ? 'bg-primary-600 text-white' 
                  : 'hover:bg-slate-700 text-slate-300'
              }`}
            >
              <div className="font-medium truncate">{file.name}</div>
              <div className="text-xs opacity-70 truncate">
                {file.created_at ? new Date(file.created_at).toLocaleDateString() : 'N/A'}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Right Content: Inspector */}
      <div className="flex-1 bg-slate-800 rounded-xl border border-slate-700 flex flex-col min-h-0 overflow-hidden">
        {selectedFile ? (
          <div className="flex flex-col h-full">
            {/* Header */}
            <div className="p-4 border-b border-slate-700 bg-slate-800">
               <h1 className="text-xl font-bold text-slate-100 truncate">{selectedFile.name}</h1>
               <div className="flex gap-4 mt-2 text-sm text-slate-400">
                  <span>ID: {selectedFile.id}</span>
                  <span>Type: {selectedExtraction?.file_type || 'N/A'}</span>
               </div>
               {selectedExtraction?.summary && (
                 <p className="mt-2 text-slate-300 italic bg-slate-900 p-2 rounded border border-slate-700">
                   "{selectedExtraction.summary}"
                 </p>
               )}
            </div>

            {/* Tabs / Content */}
            <div className="flex-1 overflow-y-auto p-4">
              <div className="mb-6">
                <h3 className="text-md font-semibold text-primary-400 mb-2 uppercase tracking-wider">Extracted Data (JSON)</h3>
                {selectedExtraction?.extracted_json ? (
                  <pre className="bg-slate-950 text-slate-300 p-4 rounded-lg overflow-x-auto text-xs font-mono border border-slate-700">
                    {JSON.stringify(selectedExtraction.extracted_json, null, 2)}
                  </pre>
                ) : (
                  <div className="text-slate-500 italic">No extracted data available.</div>
                )}
              </div>

              {/* Placeholder for Relationships */}
              {/* Relationship Graph */}
              <div className="flex-1 min-h-[400px] border border-slate-700 rounded-lg overflow-hidden bg-slate-900">
                 <h3 className="text-md font-semibold text-primary-400 mb-2 uppercase tracking-wider p-4 pb-0">Relationship Graph</h3>
                 <RelationshipGraph data={graphData} isLoading={graphIsLoading} />
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-slate-500 flex-col">
            <svg className="w-16 h-16 mb-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <p>Select a file to inspect details</p>
          </div>
        )}
      </div>
    </div>
  )
}
