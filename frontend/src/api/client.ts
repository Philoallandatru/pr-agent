import axios from 'axios';
import type { Repository, PRReview, PromptTemplate, Statistics, SystemStatus, SystemLog } from '../types';

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
});

// Repositories
export const getRepositories = () =>
  api.get<Repository[]>('/repositories').then(res => res.data);

export const getRepository = (id: number) =>
  api.get<Repository>(`/repositories/${id}`).then(res => res.data);

export const createRepository = (data: Omit<Repository, 'id' | 'created_at' | 'updated_at'>) =>
  api.post<Repository>('/repositories', data).then(res => res.data);

export const updateRepository = (id: number, data: Partial<Repository>) =>
  api.put<Repository>(`/repositories/${id}`, data).then(res => res.data);

export const deleteRepository = (id: number) =>
  api.delete(`/repositories/${id}`);

// PR Reviews
export const getReviews = (params?: { repo_id?: number; status?: string; limit?: number }) =>
  api.get<PRReview[]>('/reviews', { params }).then(res => res.data);

export const getReview = (id: number) =>
  api.get<PRReview>(`/reviews/${id}`).then(res => res.data);

export const retryReview = (id: number) =>
  api.post<PRReview>(`/reviews/${id}/retry`).then(res => res.data);

// Prompt Templates
export const getPromptTemplates = () =>
  api.get<PromptTemplate[]>('/prompts').then(res => res.data);

export const getPromptTemplate = (id: number) =>
  api.get<PromptTemplate>(`/prompts/${id}`).then(res => res.data);

export const createPromptTemplate = (data: Omit<PromptTemplate, 'id' | 'created_at' | 'updated_at'>) =>
  api.post<PromptTemplate>('/prompts', data).then(res => res.data);

export const updatePromptTemplate = (id: number, data: Partial<PromptTemplate>) =>
  api.put<PromptTemplate>(`/prompts/${id}`, data).then(res => res.data);

export const deletePromptTemplate = (id: number) =>
  api.delete(`/prompts/${id}`);

// System
export const getStatistics = () =>
  api.get<Statistics>('/statistics').then(res => res.data);

export const getSystemStatus = () =>
  api.get<SystemStatus>('/status').then(res => res.data);

export const getLogs = (params?: { level?: string; limit?: number }) =>
  api.get<SystemLog[]>('/logs', { params }).then(res => res.data);

export const getHealth = () =>
  api.get('/health').then(res => res.data);
