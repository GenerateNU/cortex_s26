import { useQuery } from '@tanstack/react-query'

import { supabase } from '../config/supabase.config'
import type { Relationship, FileRelationshipDetail } from '../types/relationship.types'

export const QUERY_KEYS = {
  relationships: {
    all: ['relationships', 'list'] as const,
    detail: (id: string | undefined) => ['relationships', 'detail', id] as const,
    fileRelationships: (relationshipId: string | undefined) => ['relationships', 'files', relationshipId] as const,
  },
}

export const useGetAllRelationships = () => {
  // const { currentTenant } = useAuth()

  const query = useQuery({
    queryKey: QUERY_KEYS.relationships.all,
    queryFn: async (): Promise<Relationship[]> => {
      const { data, error } = await supabase
        .from('relationships')
        .select('*')
        .order('relationship_name')

      if (error) throw error
      return data || []
    },
    // Enable for everyone, authenticated or not (based on RLS)
    enabled: true, 
  })

  return {
    relationships: query.data || [],
    relationshipsIsLoading: query.isPending,
    relationshipsError: query.error,
    relationshipsRefetch: query.refetch,
  }
}

export const useGetFileRelationships = (relationshipId: string | undefined) => {
  const query = useQuery({
    queryKey: QUERY_KEYS.relationships.fileRelationships(relationshipId),
    queryFn: async (): Promise<FileRelationshipDetail[]> => {
      if (!relationshipId) return []

      // Join file_relationships with raw_files (and optionally extracted_files for type)
      // Note: Supabase types might be tricky with deep joins, using 'raw_files!inner(file_name)'
      // We also want file_type, which is in extracted_files.
      // For MVP, let's just get raw_files(file_name) and maybe we can join extracted_files too if needed.
      // But based on schema, raw_files doesn't have type. extracted_files has type.
      
      const { data, error } = await supabase
        .from('file_relationships')
        .select(`
          *,
          file:raw_files (
            file_name,
            extracted_file:extracted_files (
              file_type
            )
          )
        `)
        .eq('relationship_id', relationshipId)
        .order('created_at', { ascending: false })

      if (error) throw error

      return (data || []).map((item: any) => {
        // Handle potential array from extracted_files join
        const extFiles = item.file?.extracted_file;
        const fileType = Array.isArray(extFiles) && extFiles.length > 0 ? extFiles[0].file_type : extFiles?.file_type || null;
        
        return {
          file_id: item.file_id,
          relationship_id: item.relationship_id,
          created_at: item.created_at,
          confidence_score: item.confidence_score,
          source: item.source,
          file: {
            name: item.file?.file_name || 'Unknown File',
            type: fileType
          }
        }
      })
    },
    enabled: !!relationshipId,
  })

  return {
    fileRelationships: query.data || [],
    fileRelationshipsIsLoading: query.isPending,
    fileRelationshipsError: query.error,
  }
}
