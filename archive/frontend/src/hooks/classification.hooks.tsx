import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { QUERY_KEYS } from '../utils/constants'
import type {
  Classification,
  VisualizationResponse,
} from '../types/classification.types'
import type { Tables } from '../types/database.types'
import api from '../config/axios.config'
import { supabase } from '../config/supabase.config'

export const useGetClusterVisualization = () => {
  // const { currentTenant } = useAuth()

  const query = useQuery({
    queryKey: QUERY_KEYS.classifications.visualization('default'),
    queryFn: async (): Promise<VisualizationResponse> => {
      const { data } = await api.get(
        `/classification/visualize_clustering/default`
      )

      return data
    },
    enabled: true,
  })

  return {
    visualizationResponse: query.data,
    visualizationResponseIsLoading: query.isPending,
    visualizationResponseError: query.error,
    visualizationResponseRefetch: query.refetch,
  }
}

export const useGetClassifications = () => {
  // const { currentTenant } = useAuth()

  const query = useQuery({
    queryKey: QUERY_KEYS.classifications.list('default'),
    queryFn: async (): Promise<Classification[]> => {
      // if (!currentTenant) return []

      const { data, error } = await supabase
        .from('classifications')
        .select('*')
        // .eq('tenant_id', currentTenant.id)

      if (error) throw error

      return data
        ? (data as Tables<'classifications'>[]).map(classification => ({
            classification_id: classification.id,
            tenant_id: classification.tenant_id,
            name: classification.name,
          }))
        : []
    },
    enabled: true,
  })

  return {
    classifications: query.data,
    classificationsIsLoading: query.isPending,
    classificationsError: query.error,
    classificationsRefetch: query.refetch,
  }
}

export const useClassifications = () => {
  // const { currentTenant } = useAuth()
  const queryClient = useQueryClient()

  const createClassificationsMutation = useMutation({
    mutationKey: ['create-classifications'],
    mutationFn: async (): Promise<Classification[]> => {
      const { data } = await api.post(
        `/classification/create_classifications/default`
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
        queryKey: QUERY_KEYS.files.list('all'),
      })
    },
  })

  const classifyFilesMutation = useMutation({
    mutationKey: ['classify-files'],
    mutationFn: async () => {
      await api.post(`/classification/classify_files/default`)
    },
    onSuccess: () => {
      // Invalidate files since their classification status changed
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.files.list('all'),
      })
      // Also invalidate extracted files as they contain classification info
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.extractedFiles.list('all'),
      })
      // Refresh classifications list just in case
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.classifications.list('default'),
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
