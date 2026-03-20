export interface Tunnel {
  id: string;
  slug: string;
  status: 'pending' | 'active' | 'idle' | 'expired' | 'deleted';
  url: string;
  dashboard_url: string;
  created_at: string;
  expires_at?: string;
  last_active?: string;
  local_port?: number;
  local_url?: string;
}

export interface TunnelStats {
  total_requests: number;
  unique_ips: number;
  bytes_transferred: number;
}

export interface TunnelStatus extends Tunnel {
  stats?: TunnelStats;
}

export interface TunnelCreate {
  local_port: number;
  local_url?: string;
  name?: string;
  ttl_seconds?: number;
  auth_domain?: string;
  password?: string;
}

export interface TunnelResponse {
  id: string;
  slug: string;
  assigned_port: number;
  url: string;
  dashboard_url: string;
  status: string;
  expires_at?: string;
  ssh_command: string;
  local_port: number;
  local_url?: string;
}

export interface RequestLog {
  id: string;
  method: string;
  path: string;
  query_params: Record<string, string>;
  status_code?: number;
  latency_ms?: number;
  visitor_ip?: string;
  country_code?: string;
  created_at: string;
}

export interface RequestLogDetail extends RequestLog {
  req_headers: Record<string, string>;
  req_body?: string;
  res_headers: Record<string, string>;
  res_body?: string;
}

export interface RequestLogPage {
  total: number;
  page: number;
  limit: number;
  requests: RequestLog[];
}

export interface WSEvent {
  type: 'connected' | 'request' | 'status_change' | 'expired' | 'idle_warning' | 'visitor_count';
  timestamp?: string;
  data: Record<string, unknown>;
}

export interface User {
  id: string;
  email: string;
  ssh_key_registered: boolean;
  active_tunnels: number;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}
