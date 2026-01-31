import api from './api';
import type { Resource, ResourceListResponse, ResourceFilters, ActionResponse } from '@/types';

export const resourcesApi = {
  list: async (filters: ResourceFilters = {}, page = 1, pageSize = 50): Promise<ResourceListResponse> => {
    const params = new URLSearchParams();

    if (filters.resource_type) params.append('resource_type', filters.resource_type);
    if (filters.region) params.append('region', filters.region);
    if (filters.state) params.append('state', filters.state);
    if (filters.tag_key) params.append('tag_key', filters.tag_key);
    if (filters.tag_value) params.append('tag_value', filters.tag_value);
    if (filters.search) params.append('search', filters.search);
    params.append('page', String(page));
    params.append('page_size', String(pageSize));

    const response = await api.get<ResourceListResponse>(`/resources?${params}`);
    return response.data;
  },

  get: async (resourceId: string): Promise<Resource> => {
    const response = await api.get<Resource>(`/resources/${resourceId}`);
    return response.data;
  },

  exportCsv: async (filters: ResourceFilters = {}): Promise<Blob> => {
    const params = new URLSearchParams();
    if (filters.resource_type) params.append('resource_type', filters.resource_type);
    if (filters.region) params.append('region', filters.region);

    const response = await api.get(`/resources/export/csv?${params}`, {
      responseType: 'blob',
    });
    return response.data;
  },

  exportJson: async (filters: ResourceFilters = {}): Promise<Blob> => {
    const params = new URLSearchParams();
    if (filters.resource_type) params.append('resource_type', filters.resource_type);
    if (filters.region) params.append('region', filters.region);

    const response = await api.get(`/resources/export/json?${params}`, {
      responseType: 'blob',
    });
    return response.data;
  },
};

export const actionsApi = {
  ec2Start: async (instanceIds: string[], dryRun = true): Promise<ActionResponse> => {
    const response = await api.post<ActionResponse>('/actions/ec2/start', {
      resource_ids: instanceIds,
      dry_run: dryRun,
    });
    return response.data;
  },

  ec2Stop: async (instanceIds: string[], dryRun = true, overrideCode?: string): Promise<ActionResponse> => {
    const response = await api.post<ActionResponse>('/actions/ec2/stop', {
      resource_ids: instanceIds,
      dry_run: dryRun,
      override_code: overrideCode,
    });
    return response.data;
  },

  ec2Terminate: async (instanceIds: string[], dryRun = true, overrideCode?: string): Promise<ActionResponse> => {
    const response = await api.post<ActionResponse>('/actions/ec2/terminate', {
      resource_ids: instanceIds,
      dry_run: dryRun,
      override_code: overrideCode,
    });
    return response.data;
  },

  rdsStart: async (dbIdentifier: string, dryRun = true): Promise<ActionResponse> => {
    const response = await api.post<ActionResponse>('/actions/rds/start', {
      resource_ids: [dbIdentifier],
      db_instance_identifier: dbIdentifier,
      dry_run: dryRun,
    });
    return response.data;
  },

  rdsStop: async (dbIdentifier: string, dryRun = true, overrideCode?: string): Promise<ActionResponse> => {
    const response = await api.post<ActionResponse>('/actions/rds/stop', {
      resource_ids: [dbIdentifier],
      db_instance_identifier: dbIdentifier,
      dry_run: dryRun,
      override_code: overrideCode,
    });
    return response.data;
  },

  ecsScale: async (
    cluster: string,
    service: string,
    desiredCount: number,
    dryRun = true
  ): Promise<ActionResponse> => {
    const response = await api.put<ActionResponse>('/actions/ecs/scale', {
      resource_ids: [`${cluster}/${service}`],
      cluster,
      service,
      desired_count: desiredCount,
      dry_run: dryRun,
    });
    return response.data;
  },
};
