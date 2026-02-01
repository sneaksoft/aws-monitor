export interface User {
  id: string;
  email: string;
  role: 'admin' | 'operator' | 'readonly';
  created_at: string;
  updated_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token?: string;
}

export interface AuditLog {
  id: string;
  user_email: string | null;
  action: string;
  resource_type: string;
  resource_id: string;
  aws_account_id: string | null;
  region: string | null;
  status: string;
  request_data: Record<string, unknown> | null;
  response_data: Record<string, unknown> | null;
  created_at: string;
}

export interface AuditLogListResponse {
  items: AuditLog[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface ApiError {
  detail: string;
}
