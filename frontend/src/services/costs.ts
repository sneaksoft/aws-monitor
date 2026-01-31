import api from './api';
import type {
  CostSummary,
  CostBreakdown,
  CostForecast,
  CostRecommendationsResponse,
  DailyCost,
} from '@/types';

export const costsApi = {
  getSummary: async (): Promise<CostSummary> => {
    const response = await api.get<CostSummary>('/cost/summary');
    return response.data;
  },

  getBreakdown: async (
    startDate?: string,
    endDate?: string,
    granularity = 'MONTHLY'
  ): Promise<CostBreakdown> => {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    params.append('granularity', granularity);

    const response = await api.get<CostBreakdown>(`/cost/breakdown?${params}`);
    return response.data;
  },

  getForecast: async (): Promise<CostForecast> => {
    const response = await api.get<CostForecast>('/cost/forecast');
    return response.data;
  },

  getRecommendations: async (): Promise<CostRecommendationsResponse> => {
    const response = await api.get<CostRecommendationsResponse>('/cost/recommendations');
    return response.data;
  },

  getDailyCosts: async (days = 30): Promise<DailyCost[]> => {
    const response = await api.get<DailyCost[]>(`/cost/daily?days=${days}`);
    return response.data;
  },

  getCostsByTag: async (
    tagKey: string,
    startDate?: string,
    endDate?: string
  ): Promise<{ tag_value: string; cost: number }[]> => {
    const params = new URLSearchParams();
    params.append('tag_key', tagKey);
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    const response = await api.get(`/cost/by-tag?${params}`);
    return response.data;
  },
};
