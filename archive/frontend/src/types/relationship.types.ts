export interface Relationship {
  relationship_id: string
  relationship_name: string
  relationship_description: string
}

export type RelationshipSource = 'manual' | 'ai_inference' | 'filename-rule'

export interface FileRelationship {
  file_id: string
  relationship_id: string
  created_at: string | null
  confidence_score: number | null
  source: RelationshipSource | null
}

// Extended type for UI joined with file details
export interface FileRelationshipDetail extends FileRelationship {
  file: {
    name: string
    type: string | null // file_type_enum
  } | null
}
