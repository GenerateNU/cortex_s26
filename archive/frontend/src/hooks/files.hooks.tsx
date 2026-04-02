import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
// import { useAuth } from '../contexts/AuthContext'
import { QUERY_KEYS } from '../utils/constants'
import { supabase } from '../config/supabase.config'
import type { FileUpload } from '../types/file.types'
import { sanitizeFilename } from '../utils/file-helpers'

export const useGetAllFiles = () => {
  // Tenant check removed as multi-tenancy is deprecated in DB
  // const { currentTenant } = useAuth() 

  const query = useQuery({
    queryKey: QUERY_KEYS.files.list('default'), 
    queryFn: async (): Promise<FileUpload[]> => {
      // Allow fetching without tenant for now, or just ignore tenant
      
      const { data, error } = await supabase
        .from('raw_files')
        .select(`
          file_id,
          file_name,
          uploaded_at,
          extracted_files (
            file_type
          )
        `)
        .order('uploaded_at', { ascending: false })

      if (error) throw error

      return data
        ? data.map((file: any) => ({
            id: file.file_id,
            name: file.file_name,
            type: file.extracted_files?.[0]?.file_type || 'unknown',
            created_at: file.uploaded_at,
          }))
        : []
    },
    // Always enabled
    enabled: true,
  })

  return {
    files: query.data,
    filesIsLoading: query.isPending,
    filesError: query.error,
    filesRefetch: query.refetch,
  }
}

export const useGetFile = (fileUploadId: string | undefined) => {
  // const { currentTenant } = useAuth()

  const query = useQuery({
    queryKey: QUERY_KEYS.files.detail('default', fileUploadId),
    queryFn: async (): Promise<FileUpload> => {
      if (!fileUploadId) {
        throw new Error('File ID is required')
      }
      
      const { data, error } = await supabase
        .from('raw_files')
        .select(`
          file_id,
          file_name,
          uploaded_at,
          extracted_files (
             file_type
          )
        `)
        .eq('file_id', fileUploadId)
        .single()

      if (error) throw error
      
      return {
        id: data.file_id,
        name: data.file_name,
        type: (data.extracted_files as any)?.[0]?.file_type || 'unknown',
        created_at: data.uploaded_at,
      }
    },
    enabled: !!fileUploadId,
  })

  return {
    file: query.data,
    fileIsLoading: query.isPending,
    fileError: query.error,
    fileRefetch: query.refetch,
  }
}

export const useFilesMutations = () => {
  // const { currentTenant } = useAuth()
  const queryClient = useQueryClient()

  const uploadFile = useMutation({
    mutationFn: async (file: File): Promise<{ path: string }> => {
      // We still use currentTenant.id for folder structure if available, 
      // otherwise use 'default' or similar if we want to organize files.
      // But since tenants are gone from DB, we might just use 'documents' bucket root or a default folder.
      
      const tenantId = 'default'
      const sanitizedName = sanitizeFilename(file.name)
      const filePath = `${tenantId}/${sanitizedName}`

      console.log('Starting upload:', { filePath })

      const { data: uploadData, error: uploadError } = await supabase.storage
        .from('documents')
        .upload(filePath, file)

      if (uploadError) {
        console.error('Storage upload failed:', uploadError)
        throw uploadError
      }

      console.log('Storage upload succeeded:', uploadData.path)

      // We need to insert into raw_files manually now? 
      // Or does a trigger handle it?
      // Usually storage triggers don't automatically populate raw_files unless configured.
      // Let's assume we need to insert into raw_files.
      
      const { error: dbError } = await supabase
        .from('raw_files')
        .insert({
            file_name: file.name,
            file_link: uploadData.path,
            // uploaded_at defaults to NOW()
            // file_id defaults to uuid
        })
      
      if (dbError) {
          console.error('Database insert failed:', dbError)
          throw dbError
      }

      return { path: uploadData.path }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.files.list('default'),
      })
    },
  })

  const deleteFile = useMutation({
    mutationFn: async (fileId: string): Promise<void> => {
      
      // Get file path first
      const { data: fileData, error: fetchError } = await supabase
        .from('raw_files')
        .select('file_name, file_link')
        .eq('file_id', fileId)
        .single()

      if (fetchError) throw fetchError
      if (!fileData) throw new Error('File not found')

      // Delete from DB
      const { error: dbError } = await supabase
        .from('raw_files')
        .delete()
        .eq('file_id', fileId)

      if (dbError) throw dbError

      // Delete from Storage
      // file_link usually stores the path
      if (fileData.file_link) {
          const { error: storageError } = await supabase.storage
            .from('documents')
            .remove([fileData.file_link])
          
          if (storageError) {
              console.warn('Storage delete failed (non-fatal):', storageError)
          }
      }
    },

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.files.list('default'),
      })
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.extractedFiles.list('default'),
      })
    },
  })

  return {
    uploadFile: uploadFile.mutateAsync,
    deleteFile: deleteFile.mutateAsync,
    isUploadingFile: uploadFile.isPending,
    isDeletingFile: deleteFile.isPending,
    uploadFileError: uploadFile.error,
    deleteFileError: deleteFile.error,
  }
}

export const useGetSignedUrl = (file: FileUpload | null) => {
  // const { currentTenant } = useAuth()

  const query = useQuery({
    // queryKey: QUERY_KEYS.files.signedUrl(currentTenant?.id, file?.id),
    queryKey: ['files', 'signedUrl', file?.id],
    queryFn: async (): Promise<string> => {
      if (!file) {
        throw new Error('Missing file')
      }
      
      // We need the file path. 'name' in FileUpload is just the display name.
      // We previously stored 'file_link' in raw_files. 
      // But FileUpload type doesn't have it.
      // We might need to fetch it or store it in FileUpload.
      // For now, let's try to guess it or fetch it.
      // Better: Add file_link to FileUpload.
      
      // Let's fetch the path from DB to be safe
       const { data, error } = await supabase
        .from('raw_files')
        .select('file_link')
        .eq('file_id', file.id)
        .single()
        
       if (error || !data) throw error || new Error('File not found')
       
       const path = data.file_link

      const { data: signedData, error: signedError } = await supabase.storage
        .from('documents')
        .createSignedUrl(path, 3600)

      if (signedError) {
        console.error('Signed URL error:', signedError)
        throw signedError
      }

      return signedData.signedUrl
    },
    enabled: !!file,
    staleTime: 3000 * 1000, 
  })

  return {
    signedUrl: query.data,
    signedUrlIsLoading: query.isLoading,
    signedUrlError: query.error,
    signedUrlRefetch: query.refetch,
  }
}
