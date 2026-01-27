import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../contexts/AuthContext'
import { QUERY_KEYS } from '../utils/constants'
import type {
  Classification,
  VisualizationResponse,
} from '../types/classification.types'
import type { Tables } from '../types/database.types'
import api from '../config/axios.config'
import { supabase } from '../config/supabase.config'

export const useGetClusterVisualization = () => {
  const { currentTenant } = useAuth()

  const query = useQuery({
    queryKey: QUERY_KEYS.classifications.visualization(currentTenant?.id),
    queryFn: async (): Promise<VisualizationResponse> => {
      const { data } = await api.get(
        `/classification/visualize_clustering/${currentTenant?.id}`
      )

      return data
    },
    enabled: !!currentTenant?.id,
  })

  return {
    visualizationResponse: query.data,
    visualizationResponseIsLoading: query.isPending,
    visualizationResponseError: query.error,
    visualizationResponseRefetch: query.refetch,
  }
}

export const useGetClassifications = () => {
  const { currentTenant } = useAuth()

  const query = useQuery({
    queryKey: QUERY_KEYS.classifications.list(currentTenant?.id),
    queryFn: async (): Promise<Classification[]> => {
      if (!currentTenant) return []

      const { data, error } = await supabase
        .from('classifications')
        .select('*')
        .eq('tenant_id', currentTenant.id)

      if (error) throw error

      return data
        ? (data as Tables<'classifications'>[]).map(classification => ({
            classification_id: classification.id,
            tenant_id: classification.tenant_id,
            name: classification.name,
          }))
        : []
    },
    enabled: !!currentTenant?.id,
  })

  return {
    classifications: query.data,
    classificationsIsLoading: query.isPending,
    classificationsError: query.error,
    classificationsRefetch: query.refetch,
  }
}

export const useClassifications = () => {
  const { currentTenant } = useAuth()
  const queryClient = useQueryClient()

  const createClassificationsMutation = useMutation({
    mutationKey: ['create-classifications'],
    mutationFn: async (): Promise<Classification[]> => {
      if (!currentTenant) {
        throw new Error('No tenant selected')
      }

      const { data } = await api.post(
        `/classification/create_classifications/${currentTenant?.id}`
      )

      return data
    },
    onSuccess: () => {
      // Invalidate everything related to classifications
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.classifications.all(),
      })
      // Creating classifications doesn't directly change files,
      // but the backend might have unlinked files from deleted labels
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.files.list(currentTenant?.id),
      })
    },
  })

  const classifyFilesMutation = useMutation({
    mutationKey: ['classify-files'],
    mutationFn: async () => {
      if (!currentTenant) {
        throw new Error('No tenant selected')
      }

      await api.post(`/classification/classify_files/${currentTenant?.id}`)
    },
    onSuccess: () => {
      // Invalidate files since their classification status changed
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.files.list(currentTenant?.id),
      })
      // Also invalidate extracted files as they contain classification info
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.extractedFiles.list(currentTenant?.id),
      })
      // Refresh classifications list just in case
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.classifications.list(currentTenant?.id),
      })
    },
  })

  return {
    createClassifications: createClassificationsMutation.mutateAsync,
    isCreatingClassifications: createClassificationsMutation.isPending,
    createClassificationsError: createClassificationsMutation.error,
    classifyFiles: classifyFilesMutation.mutateAsync,
    isClassifyingFiles: classifyFilesMutation.isPending,
    classifyingFilesError: classifyFilesMutation.error,
  }
}
