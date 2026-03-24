import axios from '../config/axios.config';
import type { SearchResult } from '../types';

export const api = {
  preprocess: async (fileId: string): Promise<void> => {
    await axios.post(`/preprocess/${fileId}`);
  },

  search: async (query: string): Promise<SearchResult[]> => {
    const response = await axios.post<{ results: SearchResult[] }>('/search', { query });
    return response.data.results;
  }
};
