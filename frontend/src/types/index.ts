export type FileType = 'RFQ' | 'PO' | 'ProdSpec' | 'Sales' | 'Customers';

export interface RawFile {
  file_id: string;
  file_name: string;
  file_link: string;
  uploaded_at: string;
}

export interface ExtractedFile {
  file_id: string;
  file_name: string; // denormalized
  file_type?: FileType;
  summary?: string;
  extracted_json?: Record<string, unknown> | null;
  processed_at?: string;
}

// Join type for UI
export interface Document extends RawFile, ExtractedFile {}

export interface Relationship {
  relationship_id: string;
  relationship_name: string;
  relationship_description: string;
}

export interface FileRelationship {
  file_id: string;
  relationship_id: string;
  confidence_score: number;
  source: 'manual' | 'ai_inference' | 'filename-rule';
  created_at: string;
}

export interface SearchResult {
  file_id: string;
  file_name: string;
  file_type: FileType;
  summary: string;
  similarity: number;
}
