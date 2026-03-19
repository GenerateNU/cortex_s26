import { useQuery } from '@tanstack/react-query'

import { QUERY_KEYS } from '../utils/constants'
import { supabase } from '../config/supabase.config'
import type { ExtractedFile } from '../types/extracted-file.types'

export const useGetAllExtractedFiles = () => {
  // const { currentTenant } = useAuth()

  const query = useQuery({
    queryKey: QUERY_KEYS.extractedFiles.list('all'),
    queryFn: async (): Promise<ExtractedFile[]> => {
      // if (!currentTenant) return []

      const { data, error } = await supabase
        .from('extracted_files')
        .select('*')
        // .eq('file_uploads.tenant_id', currentTenant.id) // Tenant ID removed from schema

      if (error) throw error
      return data
        ? data.map((extractedFile) => ({
            ...extractedFile,
            embedding: extractedFile.embedding as unknown as number[] | null,
          }))
        : []
    },
    // enabled: !!currentTenant?.id,
    enabled: true,
  })

  return {
    extractedFiles: query.data,
    extractedFilesIsLoading: query.isPending,
    extractedFilesError: query.error,
    extractedFilesRefetch: query.refetch,
  }
}

export const useGetExtractedFile = (sourceFileId: string | undefined) => {
  const query = useQuery({
    queryKey: QUERY_KEYS.extractedFiles.detail(sourceFileId),
    queryFn: async (): Promise<ExtractedFile | null> => {
      if (!sourceFileId) {
        return null
      }

      const { data, error } = await supabase
        .from('extracted_files')
        .select('*')
        .eq('file_id', sourceFileId)
        .single()

      if (error) {
        if (error.code === 'PGRST116') {
          // No rows returned - file not yet processed
          return null
        }
        throw error
      }

      return data
        ? {
            ...data,
            embedding: data.embedding as unknown as number[] | null,
          }
        : null
    },
    enabled: !!sourceFileId,
  })

  return {
    extractedFile: query.data,
    extractedFileIsLoading: query.isPending,
    extractedFileError: query.error,
    extractedFileRefetch: query.refetch,
  }
}
