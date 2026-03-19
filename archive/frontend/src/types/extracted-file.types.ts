import type { Json } from './database.types'

export interface ExtractedFile {
  id: string // New PK
  file_id: string // FK to raw_files
  file_name: string | null
  file_type: string | null // Using string to be compatible with enum generally, or we can use specific union type
  summary: string | null
  extracted_json: Json
  embedding: number[] | null
  row_index: number | null
  processed_at: string | null
}
