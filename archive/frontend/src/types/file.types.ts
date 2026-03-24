export interface FileUpload {
  id: string            // Mapped from raw_files.file_id
  name: string          // Mapped from raw_files.file_name
  type: string | null   // Mapped from extracted_files.file_type
  created_at: string | null // Mapped from raw_files.uploaded_at
  // classification: string | null // Removed as table is dropped
  // tenant_id: string // Removed as table is dropped
}
