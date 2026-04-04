import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 60_000,
})

// ─── Types ────────────────────────────────────────────────────────────────────

export type DocumentType = 'RFQ' | 'PO' | 'CFG' | 'Client CSV' | 'Sales CSV' | null

export type DocumentStatus = 'processing' | 'completed' | 'failed'

export type ProgressStage =
  | 'uploading'
  | 'ingesting'
  | 'building_graph'
  | 'analyzing'
  | 'extracting_insights'
  | 'completed'
  | 'failed'

export interface Document {
  id: string
  original_filename: string
  dataset_name: string
  document_type: DocumentType
  status: DocumentStatus
  progress_stage: ProgressStage
  summary: string | null
  insights: string[]
  entities: string[]
  raw_chunks_count: number
  uploaded_at: string
  completed_at: string | null
  file_url: string | null
}

export interface SearchResult {
  text: string
  score: number | null
  metadata: {
    dataset?: string
    [key: string]: unknown
  }
}

export interface SearchResponse {
  query: string
  results: SearchResult[]
  total: number
}

export interface UploadedFile {
  id: string
  filename: string
}

export interface UploadResponse {
  uploaded: UploadedFile[]
}

export interface GraphNode {
  id: string
  name: string
  val: number
}

export interface GraphLink {
  source: string
  target: string
  label: string
}

export interface GraphData {
  nodes: GraphNode[]
  links: GraphLink[]
}

// ─── API calls ────────────────────────────────────────────────────────────────

export async function searchDocuments(query: string): Promise<SearchResponse> {
  const { data } = await client.get<SearchResponse>('/api/documents/search', {
    params: { q: query, search_type: 'GRAPH_COMPLETION' },
  })
  return data
}

export async function uploadDocuments(files: File[]): Promise<UploadResponse> {
  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file)
  }
  const { data } = await client.post<UploadResponse>(
    '/api/documents/upload',
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  return data
}

export async function getDocument(id: string): Promise<Document> {
  const { data } = await client.get<Document>(`/api/documents/${id}`)
  return data
}

export async function listDocuments(): Promise<Document[]> {
  const { data } = await client.get<Document[]>('/api/documents/')
  return data
}

export async function getDocumentFileUrl(id: string): Promise<{ url: string; filename: string }> {
  const { data } = await client.get<{ url: string; filename: string }>(`/api/documents/${id}/file-url`)
  return data
}

export async function getGraphData(dataset?: string): Promise<GraphData> {
  const { data } = await client.get<GraphData>('/api/documents/graph', {
    params: dataset ? { dataset } : undefined,
  })
  return data
}
