import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../config/axios.config'
import { useAuth } from '../contexts/AuthContext'
import { QUERY_KEYS } from '../utils/constants'
import type {
  Relationship,
  RelationshipCreate,
} from '../types/relationship.types'

export const useAnalyzeRelationships = () => {
  const { currentTenant, user } = useAuth()
  const queryClient = useQueryClient()

  const analyzeMutation = useMutation({
    mutationFn: async (): Promise<RelationshipCreate[]> => {
      if (!currentTenant) {
        throw new Error('No tenant selected')
      }
      if (user?.role !== 'admin') {
        throw new Error('Only admins can analyze relationships')
      }

      const { data } = await api.post(
        `/pattern-recognition/analyze/${currentTenant.id}`
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.relationships.list(currentTenant?.id),
      })
    },
  })

  return {
    analyzeRelationships: analyzeMutation.mutateAsync,
    isAnalyzingRelationships: analyzeMutation.isPending,
    analyzeRelationshipsError: analyzeMutation.error,
  }
}

export const useGetRelationships = () => {
  const { currentTenant } = useAuth()

  const query = useQuery({
    queryKey: QUERY_KEYS.relationships.list(currentTenant?.id),
    enabled: !!currentTenant?.id,
    queryFn: async (): Promise<Relationship[]> => {
      // Legacy hook - broken by schema change (v013).
      // Returning empty array to satisfy types until removed/refactored.
      return [] 
      
      /* 
      if (!currentTenant) return []

      const { data, error } = await supabase
        .from('relationships')
        .select(...)
      */
    },
  })

  return {
    relationships: query.data ?? [],
    relationshipsIsLoading: query.isPending,
    relationshipsError: query.error,
    relationshipsRefetch: query.refetch,
  }
}

export const useGetGraphData = () => {
  const query = useQuery({
    queryKey: ['graph-data'],
    queryFn: async () => {
      const { data } = await api.get('/pattern-recognition/graph')
      return data
    },
    // Refresh every 30 seconds or on window focus
    staleTime: 30 * 1000, 
  })

  return {
    graphData: query.data,
    graphIsLoading: query.isPending,
    graphError: query.error,
  }
}
