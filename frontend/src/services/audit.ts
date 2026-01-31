import api from './api';
import type { AuditLogListResponse } from '@/types';

export interface AuditFilters {
  action?: string;
  resource_type?: string;
  user_email?: string;
  start_date?: string;
  end_date?: string;
  status?: string;
}

export const auditApi = {
  list: async (
    filters: AuditFilters = {},
    page = 1,
    pageSize = 50
  ): Promise<AuditLogListResponse> => {
    const params = new URLSearchParams();

    if (filters.action) params.append('action', filters.action);
    if (filters.resource_type) params.append('resource_type', filters.resource_type);
    if (filters.user_email) params.append('user_email', filters.user_email);
    if (filters.start_date) params.append('start_date', filters.start_date);
    if (filters.end_date) params.append('end_date', filters.end_date);
    if (filters.status) params.append('status', filters.status);
    params.append('page', String(page));
    params.append('page_size', String(pageSize));

    const response = await api.get<AuditLogListResponse>(`/audit?${params}`);
    return response.data;
  },
};
