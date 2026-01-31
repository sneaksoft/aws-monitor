export interface Resource {
  resource_id: string;
  resource_type: ResourceType;
  name: string | null;
  region: string;
  aws_account_id: string;
  state: string | null;
  tags: Record<string, string>;
  metadata: Record<string, unknown>;
  created_at?: string;
  monthly_cost?: number;
}

export type ResourceType =
  | 'ec2'
  | 'ebs'
  | 'rds'
  | 'aurora'
  | 's3'
  | 'ecs'
  | 'lambda'
  | 'ebs_snapshot';

export interface ResourceListResponse {
  items: Resource[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface ResourceFilters {
  resource_type?: string;
  region?: string;
  state?: string;
  tag_key?: string;
  tag_value?: string;
  search?: string;
}

export interface ActionRequest {
  resource_ids: string[];
  dry_run: boolean;
  override_code?: string;
}

export interface ActionResponse {
  status: 'success' | 'failed' | 'dry_run';
  action: string;
  resource_ids: string[];
  dry_run: boolean;
  message?: string;
  details?: Record<string, unknown>;
}
