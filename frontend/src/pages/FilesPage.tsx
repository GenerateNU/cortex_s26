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
        <h1 className="text-2xl font-bold text-zinc-100">Processed Files</h1>
        <div className="w-64">
          <input
            type="text"
            placeholder="Search files..."
            className="w-full bg-black border border-zinc-700 rounded-lg px-4 py-2 text-sm text-zinc-200 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-shadow shadow-inner"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      <div className="flex-1 bg-zinc-900 rounded-xl border border-zinc-800 overflow-hidden flex flex-col shadow-lg">
        <div className="overflow-auto flex-1">
          <table className="min-w-full divide-y divide-zinc-800">
            <thead className="bg-[#09090b]">
              <tr>
                <th scope="col" className="px-6 py-4 text-left text-xs font-bold text-purple-400 uppercase tracking-widest">
                  File Name
                </th>
                <th scope="col" className="px-6 py-4 text-left text-xs font-bold text-purple-400 uppercase tracking-widest">
                  Type
                </th>
                <th scope="col" className="px-6 py-4 text-left text-xs font-bold text-purple-400 uppercase tracking-widest">
                  Summary
                </th>
                <th scope="col" className="px-6 py-4 text-left text-xs font-bold text-purple-400 uppercase tracking-widest">
                  Processed At
                </th>
                <th scope="col" className="px-6 py-4 text-right text-xs font-bold text-purple-400 uppercase tracking-widest">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-zinc-900 divide-y divide-zinc-800">
              {extractedFilesIsLoading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-10 text-center text-zinc-500">
                    <div className="flex justify-center flex-col items-center">
                      <svg className="animate-spin h-6 w-6 text-purple-400 mb-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Loading files...
                    </div>
                  </td>
                </tr>
              ) : filteredFiles.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-10 text-center text-zinc-500">
                    No files found.
                  </td>
                </tr>
              ) : (
                filteredFiles.map((file) => (
                  <tr key={file.id} className="hover:bg-zinc-800/80 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-zinc-200">{file.file_name || 'Untitled'}</div>
                      <div className="text-xs text-zinc-500 font-mono mt-1">{file.file_id.slice(0, 8)}...</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-md border
                        ${file.file_type === 'RFQ' ? 'bg-blue-900/30 text-blue-300 border-blue-900/50' :
                          file.file_type === 'PO' ? 'bg-emerald-900/30 text-emerald-300 border-emerald-900/50' :
                            file.file_type === 'ProdSpec' ? 'bg-purple-900/30 text-purple-300 border-purple-900/50' :
                              file.file_type === 'Sales' ? 'bg-amber-900/30 text-amber-300 border-amber-900/50' :
                                file.file_type === 'Customers' ? 'bg-pink-900/30 text-pink-300 border-pink-900/50' :
                                  'bg-zinc-800 text-zinc-300 border-zinc-700'}`}>
                        {file.file_type || 'Unknown'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-zinc-400 line-clamp-2 max-w-md leading-relaxed" title={file.summary || ''}>
                        {file.summary || 'No summary available.'}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-zinc-400 font-medium">
                      <span className="bg-zinc-800 px-2 py-1 rounded">
                        {file.processed_at ? new Date(file.processed_at).toLocaleString() : 'N/A'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <Link
                        to={`/explorer?fileId=${file.file_id}`}
                        className="text-purple-400 hover:text-purple-300 hover:underline underline-offset-4 transition-all"
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
