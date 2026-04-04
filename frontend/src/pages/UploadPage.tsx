import { useState, useCallback, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import Navbar from '../components/Navbar'
import { uploadDocuments, getDocument, type UploadedFile, type Document, type ProgressStage } from '../services/api'

const MAX_FILES = 5
const ACCEPTED_EXTENSIONS = '.pdf,.csv,.txt'

type FileProgress = {
  uploadedFile: UploadedFile
  doc: Document | null
  error: string | null
}

const STAGE_LABELS: Record<ProgressStage, string> = {
  uploading: 'Uploading…',
  ingesting: 'Ingesting document…',
  building_graph: 'Building knowledge graph…',
  analyzing: 'Analyzing content…',
  extracting_insights: 'Extracting insights…',
  completed: 'Complete',
  failed: 'Failed',
}

const STAGE_PERCENT: Record<ProgressStage, number> = {
  uploading: 10,
  ingesting: 25,
  building_graph: 50,
  analyzing: 70,
  extracting_insights: 85,
  completed: 100,
  failed: 100,
}

const DOC_TYPE_COLORS: Record<string, string> = {
  RFQ: 'bg-blue-500/15 border-blue-500/25 text-blue-300',
  PO: 'bg-green-500/15 border-green-500/25 text-green-300',
  CFG: 'bg-amber-500/15 border-amber-500/25 text-amber-300',
  'Client CSV': 'bg-rose-500/15 border-rose-500/25 text-rose-300',
  'Sales CSV': 'bg-violet-500/15 border-violet-500/25 text-violet-300',
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function UploadPage() {
  const [files, setFiles] = useState<File[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([])
  const [progresses, setProgresses] = useState<FileProgress[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  const mutation = useMutation({
    mutationFn: uploadDocuments,
    onSuccess: (data) => {
      setUploadedFiles(data.uploaded)
      setProgresses(
        data.uploaded.map((f) => ({ uploadedFile: f, doc: null, error: null }))
      )
    },
  })

  const isUploading = mutation.isPending
  const hasUploadStarted = uploadedFiles.length > 0
  const allDone =
    hasUploadStarted &&
    progresses.every((p) => p.doc?.status === 'completed' || p.doc?.status === 'failed')

  function addFiles(incoming: FileList | File[]) {
    const arr = Array.from(incoming)
    setFiles((prev) => {
      const combined = [...prev, ...arr]
      return combined.slice(0, MAX_FILES)
    })
  }

  function removeFile(idx: number) {
    setFiles((prev) => prev.filter((_, i) => i !== idx))
  }

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    if (!(e.currentTarget as HTMLElement).contains(e.relatedTarget as Node)) {
      setIsDragging(false)
    }
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      if (e.dataTransfer.files.length > 0) {
        addFiles(e.dataTransfer.files)
      }
    },
    [],
  )

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      addFiles(e.target.files)
    }
  }, [])

  function handleUpload() {
    if (files.length === 0) return
    mutation.mutate(files)
  }

  function handleReset() {
    setFiles([])
    setUploadedFiles([])
    setProgresses([])
    mutation.reset()
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  return (
    <div className="relative min-h-screen bg-black overflow-x-hidden">
      <Navbar />

      <div
        className="pointer-events-none fixed inset-0 z-0"
        style={{
          background:
            'radial-gradient(ellipse at 60% 30%, rgba(124,58,237,0.2) 0%, transparent 65%)',
        }}
      />

      {/* Decorative dotted circle */}
      <div className="pointer-events-none fixed bottom-16 left-8 opacity-10 z-0 hidden lg:block">
        <svg width="240" height="240" viewBox="0 0 240 240" fill="none">
          <circle cx="120" cy="120" r="110" stroke="#7c3aed" strokeWidth="1.5" strokeDasharray="4 8" />
          <circle cx="120" cy="120" r="75" stroke="#8b5cf6" strokeWidth="1" strokeDasharray="3 6" />
        </svg>
      </div>

      <main className="relative z-10 flex flex-col items-center px-4 pt-20 pb-24">
        <div className="w-full max-w-xl pt-10">
          {/* Header */}
          <div className="mb-10 text-center">
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-white mb-3">
              Upload Documents
            </h1>
            <p className="text-sm text-[#a1a1aa] max-w-sm mx-auto leading-relaxed">
              Upload up to {MAX_FILES} documents. Client and type are detected automatically.
            </p>
          </div>

          {!hasUploadStarted ? (
            <div className="space-y-4">
              {/* Drop zone */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`
                  relative rounded-2xl border-2 border-dashed p-12 flex flex-col items-center justify-center gap-4
                  cursor-pointer transition-all duration-200
                  ${isDragging
                    ? 'border-violet-500/60 bg-violet-600/10'
                    : 'border-white/15 bg-white/[0.02] hover:border-white/25 hover:bg-white/[0.04]'
                  }
                `}
              >
                {isDragging && (
                  <div
                    className="pointer-events-none absolute inset-0 rounded-2xl"
                    style={{ boxShadow: '0 0 40px rgba(124,58,237,0.2) inset' }}
                  />
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={ACCEPTED_EXTENSIONS}
                  multiple
                  onChange={handleInputChange}
                  className="hidden"
                />

                <div className={`w-14 h-14 rounded-xl flex items-center justify-center transition-all duration-200 ${isDragging ? 'bg-violet-600/30 border border-violet-500/50' : 'bg-white/5 border border-white/10'}`}>
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={isDragging ? 'text-violet-400' : 'text-white/30'}>
                    <path d="M12 15V4M12 4l-4 4M12 4l4 4" />
                    <path d="M3 15v4a2 2 0 002 2h14a2 2 0 002-2v-4" />
                  </svg>
                </div>

                <div className="text-center">
                  <p className={`text-sm font-medium mb-1 transition-colors ${isDragging ? 'text-violet-300' : 'text-white/60'}`}>
                    {isDragging ? 'Drop files here' : 'Drag & drop files here'}
                  </p>
                  <p className="text-xs text-[#a1a1aa]">
                    or <span className="text-violet-400">click to browse</span>
                  </p>
                  <p className="text-xs text-white/25 mt-2">PDF, CSV, TXT supported · up to {MAX_FILES} files</p>
                </div>
              </div>

              {/* File list */}
              {files.length > 0 && (
                <div className="space-y-2">
                  {files.map((file, idx) => (
                    <div key={idx} className="flex items-center gap-3 bg-white/5 border border-white/10 rounded-xl px-4 py-3">
                      <FileTypeIcon filename={file.name} />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-white truncate">{file.name}</p>
                        <p className="text-xs text-[#a1a1aa]">{formatBytes(file.size)}</p>
                      </div>
                      <button
                        onClick={(e) => { e.stopPropagation(); removeFile(idx) }}
                        className="text-white/30 hover:text-white/70 transition-colors p-1"
                      >
                        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round">
                          <line x1="3" y1="3" x2="11" y2="11" />
                          <line x1="11" y1="3" x2="3" y2="11" />
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Upload error */}
              {mutation.isError && (
                <div className="flex items-start gap-3 bg-red-500/5 border border-red-500/20 rounded-xl p-4">
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" className="text-red-400 flex-shrink-0 mt-0.5">
                    <circle cx="8" cy="8" r="6" />
                    <line x1="8" y1="5" x2="8" y2="8.5" />
                    <circle cx="8" cy="10.5" r="0.5" fill="currentColor" />
                  </svg>
                  <div>
                    <p className="text-sm font-medium text-red-300">Upload failed</p>
                    <p className="text-xs text-[#a1a1aa] mt-0.5">
                      {mutation.error instanceof Error ? mutation.error.message : 'Something went wrong.'}
                    </p>
                  </div>
                </div>
              )}

              {/* Upload button */}
              <button
                onClick={handleUpload}
                disabled={files.length === 0 || isUploading}
                className="btn-primary w-full py-3.5 text-base"
              >
                {isUploading ? (
                  <>
                    <Spinner />
                    Uploading…
                  </>
                ) : (
                  <>
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M8 10V3M8 3L5 6M8 3l3 3" />
                      <path d="M2 11v1.5A1.5 1.5 0 003.5 14h9A1.5 1.5 0 0014 12.5V11" />
                    </svg>
                    Upload {files.length > 0 ? `${files.length} file${files.length > 1 ? 's' : ''}` : 'Documents'}
                  </>
                )}
              </button>
            </div>
          ) : (
            /* Progress section */
            <div className="space-y-4">
              <h2 className="text-sm font-medium text-[#a1a1aa] mb-4">Processing files…</h2>

              {progresses.map((p, idx) => (
                <FileProgressCard key={p.uploadedFile.id} progress={p} index={idx} onUpdate={(doc) => {
                  setProgresses((prev) => prev.map((x, i) => i === idx ? { ...x, doc } : x))
                }} />
              ))}

              {allDone && (
                <div className="flex gap-3 pt-2">
                  <button
                    onClick={() => navigate('/documents')}
                    className="btn-primary flex-1 py-3"
                  >
                    View Documents
                  </button>
                  <button
                    onClick={handleReset}
                    className="flex-1 py-3 rounded-xl border border-white/10 text-sm text-white/50 hover:text-white/80 hover:border-white/20 hover:bg-white/5 transition-all duration-200"
                  >
                    Upload More
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

// ── FileProgressCard ──────────────────────────────────────────────────────────

function FileProgressCard({
  progress,
  onUpdate,
}: {
  progress: FileProgress
  index: number
  onUpdate: (doc: Document) => void
}) {
  const { uploadedFile, doc } = progress
  const status = doc?.status ?? 'processing'
  const stage = doc?.progress_stage ?? 'uploading'
  const percent = STAGE_PERCENT[stage] ?? 0
  const isDone = status === 'completed'
  const isFailed = status === 'failed'

  const { data } = useQuery({
    queryKey: ['document', uploadedFile.id],
    queryFn: () => getDocument(uploadedFile.id),
    enabled: status !== 'completed' && status !== 'failed',
    refetchInterval: (query) => {
      const d = query.state.data
      if (!d) return 2000
      return d.status === 'processing' ? 2000 : false
    },
    staleTime: 0,
  })

  useEffect(() => {
    if (data) onUpdate(data)
  }, [data]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className={`bg-white/5 border rounded-2xl p-5 transition-all duration-300 ${
      isDone ? 'border-green-500/25' : isFailed ? 'border-red-500/25' : 'border-white/10'
    }`}>
      <div className="flex items-start gap-3">
        {/* Status icon */}
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
          isDone
            ? 'bg-green-500/15 border border-green-500/25'
            : isFailed
            ? 'bg-red-500/15 border border-red-500/25'
            : 'bg-white/5 border border-white/10'
        }`}>
          {isDone ? (
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-green-400">
              <polyline points="2.5,7 5.5,10.5 11.5,3.5" />
            </svg>
          ) : isFailed ? (
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="text-red-400">
              <line x1="3" y1="3" x2="11" y2="11" />
              <line x1="11" y1="3" x2="3" y2="11" />
            </svg>
          ) : (
            <Spinner />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-medium text-white truncate max-w-xs">
              {uploadedFile.filename}
            </p>
            {isDone && doc?.document_type && (
              <span className={`px-2 py-0.5 rounded-full text-xs border font-medium ${DOC_TYPE_COLORS[doc.document_type] ?? 'bg-white/5 border-white/15 text-zinc-300'}`}>
                {doc.document_type}
              </span>
            )}
            {isDone && doc?.dataset_name && (
              <span className="px-2 py-0.5 rounded-full text-xs border border-violet-500/20 bg-violet-500/10 text-violet-300">
                {doc.dataset_name}
              </span>
            )}
          </div>

          <p className="text-xs text-[#a1a1aa] mt-1">
            {isFailed ? 'Processing failed. Please try re-uploading this file.' : STAGE_LABELS[stage]}
          </p>

          {/* Progress bar */}
          <div className="mt-3 h-1.5 rounded-full bg-white/5 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ${
                isDone
                  ? 'bg-green-500'
                  : isFailed
                  ? 'bg-red-500'
                  : 'bg-violet-500'
              }`}
              style={{ width: `${percent}%` }}
            />
          </div>
          {!isDone && !isFailed && (
            <p className="text-[10px] text-white/25 mt-1 text-right">{percent}%</p>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function FileTypeIcon({ filename }: { filename: string }) {
  const ext = filename.split('.').pop()?.toLowerCase()
  const color =
    ext === 'pdf' ? 'text-red-400' :
    ext === 'csv' ? 'text-green-400' :
    'text-blue-400'

  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={`flex-shrink-0 ${color}`}>
      <path d="M11 2H5a1 1 0 00-1 1v12a1 1 0 001 1h8a1 1 0 001-1V6L11 2z" />
      <polyline points="11,2 11,6 15,6" />
    </svg>
  )
}

function Spinner() {
  return (
    <svg className="w-4 h-4 animate-spin text-violet-400" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
  )
}
