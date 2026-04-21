export interface Repository {
  id: number;
  name: string;
  url: string;
  enabled: boolean;
  config: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface PRReview {
  id: number;
  repository_id: number;
  pr_number: number;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  result: Record<string, any> | null;
  error?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  repository?: Repository;
}

export interface PromptTemplate {
  id: number;
  name: string;
  description?: string;
  content: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface SystemLog {
  id: number;
  timestamp: string;
  level: 'info' | 'warning' | 'error';
  message: string;
  context: Record<string, any>;
}

export interface Statistics {
  total_repositories: number;
  active_repositories: number;
  total_reviews: number;
  reviews_by_status: Record<string, number>;
  recent_reviews: PRReview[];
}

export interface SystemStatus {
  status: 'healthy' | 'degraded' | 'down';
  uptime: number;
  version: string;
  database_connected: boolean;
}
