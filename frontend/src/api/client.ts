import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

// API base URL - can be configured via environment variable
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

// Create axios instance with default config
const axiosInstance: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - add auth token if available
axiosInstance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - handle common errors
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Unauthorized - clear token and redirect to login
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// API client wrapper
export const apiClient = {
  get: <T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> => {
    return axiosInstance.get<T>(url, config);
  },

  post: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> => {
    return axiosInstance.post<T>(url, data, config);
  },

  put: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> => {
    return axiosInstance.put<T>(url, data, config);
  },

  patch: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> => {
    return axiosInstance.patch<T>(url, data, config);
  },

  delete: <T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> => {
    return axiosInstance.delete<T>(url, config);
  },
};

// Dashboard API
export const dashboardApi = {
  getStats: (dashboardId: string, timeRange?: string) => {
    return apiClient.get(`/api/dashboards/${dashboardId}/stats`, {
      params: { time_range: timeRange },
    });
  },

  getTrends: (dashboardId: string, metric: string, timeRange?: string) => {
    return apiClient.get(`/api/dashboards/${dashboardId}/trends`, {
      params: { metric, time_range: timeRange },
    });
  },

  getDistribution: (dashboardId: string) => {
    return apiClient.get(`/api/dashboards/${dashboardId}/distribution`);
  },

  getTopReviewers: (dashboardId: string, limit?: number) => {
    return apiClient.get(`/api/dashboards/${dashboardId}/top-reviewers`, {
      params: { limit },
    });
  },

  refreshData: (dashboardId: string) => {
    return apiClient.post(`/api/dashboards/${dashboardId}/refresh`);
  },
};

// Metrics API
export const metricsApi = {
  recordReview: (data: any) => {
    return apiClient.post('/api/metrics/record', data);
  },

  getMetrics: (timeRange?: string, repository?: string) => {
    return apiClient.get('/api/metrics', {
      params: { time_range: timeRange, repository },
    });
  },

  getReviewStats: (reviewId: string) => {
    return apiClient.get(`/api/metrics/reviews/${reviewId}`);
  },
};

// Reports API
export const reportsApi = {
  generateReport: (data: any) => {
    return apiClient.post('/api/reports/generate', data);
  },

  getReport: (reportId: string) => {
    return apiClient.get(`/api/reports/${reportId}`);
  },

  listReports: (params?: any) => {
    return apiClient.get('/api/reports', { params });
  },

  exportReport: (reportId: string, format: string) => {
    return apiClient.get(`/api/reports/${reportId}/export`, {
      params: { format },
      responseType: 'blob',
    });
  },

  deleteReport: (reportId: string) => {
    return apiClient.delete(`/api/reports/${reportId}`);
  },
};

// Quality Scoring API
export const qualityScoringApi = {
  scoreReview: (data: any) => {
    return apiClient.post('/api/quality-scoring/score', data);
  },

  getReviewerRankings: (timeRange?: string, limit?: number) => {
    return apiClient.get('/api/quality-scoring/rankings', {
      params: { time_range: timeRange, limit },
    });
  },

  getTrends: (reviewerId: string, period: string) => {
    return apiClient.get(`/api/quality-scoring/trends/${reviewerId}`, {
      params: { period },
    });
  },

  getImprovementSuggestions: (reviewerId: string) => {
    return apiClient.get(`/api/quality-scoring/suggestions/${reviewerId}`);
  },
};

// AI Assistant API
export const aiAssistantApi = {
  chat: (message: string, conversationId?: string) => {
    return apiClient.post('/api/ai-assistant/chat', {
      message,
      conversation_id: conversationId,
    });
  },

  explainCode: (code: string, language: string, context?: string) => {
    return apiClient.post('/api/ai-assistant/explain-code', {
      code,
      language,
      context,
    });
  },

  suggestReview: (code: string, filePath: string, context?: any) => {
    return apiClient.post('/api/ai-assistant/suggest-review', {
      code,
      file_path: filePath,
      context,
    });
  },

  optimizeComment: (comment: string, context?: any) => {
    return apiClient.post('/api/ai-assistant/optimize-comment', {
      comment,
      context,
    });
  },

  getConversationHistory: (conversationId: string) => {
    return apiClient.get(`/api/ai-assistant/conversations/${conversationId}`);
  },

  clearConversation: (conversationId: string) => {
    return apiClient.delete(`/api/ai-assistant/conversations/${conversationId}`);
  },
};

// Scheduler API
export const schedulerApi = {
  scheduleJob: (data: any) => {
    return apiClient.post('/api/scheduler/jobs', data);
  },

  listJobs: (status?: string, repository?: string) => {
    return apiClient.get('/api/scheduler/jobs', {
      params: { status, repository },
    });
  },

  getJob: (jobId: string) => {
    return apiClient.get(`/api/scheduler/jobs/${jobId}`);
  },

  cancelJob: (jobId: string) => {
    return apiClient.post(`/api/scheduler/jobs/${jobId}/cancel`);
  },

  addSchedule: (data: any) => {
    return apiClient.post('/api/scheduler/schedules', data);
  },

  listSchedules: () => {
    return apiClient.get('/api/scheduler/schedules');
  },

  addTrigger: (data: any) => {
    return apiClient.post('/api/scheduler/triggers', data);
  },

  listTriggers: () => {
    return apiClient.get('/api/scheduler/triggers');
  },
};

// Knowledge Base API
export const knowledgeBaseApi = {
  addEntry: (data: any) => {
    return apiClient.post('/api/knowledge/entries', data);
  },

  getEntry: (entryId: string) => {
    return apiClient.get(`/api/knowledge/entries/${entryId}`);
  },

  updateEntry: (entryId: string, data: any) => {
    return apiClient.put(`/api/knowledge/entries/${entryId}`, data);
  },

  deleteEntry: (entryId: string) => {
    return apiClient.delete(`/api/knowledge/entries/${entryId}`);
  },

  search: (query: string, category?: string, tags?: string[]) => {
    return apiClient.get('/api/knowledge/search', {
      params: { query, category, tags: tags?.join(',') },
    });
  },

  getRelated: (entryId: string, limit?: number) => {
    return apiClient.get(`/api/knowledge/entries/${entryId}/related`, {
      params: { limit },
    });
  },

  getPopular: (limit?: number, days?: number) => {
    return apiClient.get('/api/knowledge/popular', {
      params: { limit, days },
    });
  },
};

export default apiClient;
