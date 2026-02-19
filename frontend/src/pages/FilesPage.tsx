import { useMemo, useState } from 'react'
import { useGetAllExtractedFiles } from '../hooks/extractedFile.hooks'
import { Link } from 'react-router-dom'

export function FilesPage() {
  const { extractedFiles, extractedFilesIsLoading } = useGetAllExtractedFiles()
  const [searchTerm, setSearchTerm] = useState('')

  const filteredFiles = useMemo(() => {
    if (!extractedFiles) return []
    return extractedFiles.filter(file => 
      (file.file_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (file.summary || '').toLowerCase().includes(searchTerm.toLowerCase())
    )
  }, [extractedFiles, searchTerm])

  return (
    <div className="flex flex-col h-full space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-slate-100">Processed Files</h1>
        <div className="w-64">
          <input
            type="text"
            placeholder="Search files..."
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-primary-500 transition-colors"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      <div className="flex-1 bg-slate-800 rounded-xl border border-slate-700 overflow-hidden flex flex-col">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-700">
            <thead className="bg-slate-900">
              <tr>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                  File Name
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Type
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Summary
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Processed At
                </th>
                <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-slate-800 divide-y divide-slate-700">
              {extractedFilesIsLoading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-10 text-center text-slate-500">
                    Loading files...
                  </td>
                </tr>
              ) : filteredFiles.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-10 text-center text-slate-500">
                    No files found.
                  </td>
                </tr>
              ) : (
                filteredFiles.map((file) => (
                  <tr key={file.id} className="hover:bg-slate-750 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-slate-200">{file.file_name || 'Untitled'}</div>
                      <div className="text-xs text-slate-500 font-mono">{file.file_id.slice(0, 8)}...</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                        ${file.file_type === 'RFQ' ? 'bg-blue-900/50 text-blue-200' : 
                          file.file_type === 'PO' ? 'bg-green-900/50 text-green-200' : 
                          file.file_type === 'ProdSpec' ? 'bg-purple-900/50 text-purple-200' :
                          'bg-slate-700 text-slate-300'}`}>
                        {file.file_type || 'Unknown'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-slate-400 line-clamp-2 max-w-md" title={file.summary || ''}>
                        {file.summary || 'No summary available.'}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-400">
                      {file.processed_at ? new Date(file.processed_at).toLocaleString() : 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <Link 
                        to={`/explorer?fileId=${file.file_id}`} // Assuming we might add query param support to explorer later, or just general link
                        className="text-primary-400 hover:text-primary-300"
                      >
                        View Details
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
