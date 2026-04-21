import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '../contexts/AuthContext';
import { ReactNode } from 'react';

// Mock API client
vi.mock('../api/client', () => ({
  login: vi.fn(),
  getCurrentUser: vi.fn(),
}));

describe('AuthContext', () => {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <AuthProvider>{children}</AuthProvider>
  );

  it('provides authentication state', () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    expect(result.current).toHaveProperty('user');
    expect(result.current).toHaveProperty('token');
    expect(result.current).toHaveProperty('login');
    expect(result.current).toHaveProperty('logout');
    expect(result.current).toHaveProperty('isAuthenticated');
    expect(result.current).toHaveProperty('isLoading');
  });

  it('starts with no user', () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('logs in user successfully', async () => {
    const { login, getCurrentUser } = require('../api/client');

    login.mockResolvedValue({ access_token: 'test-token', expires_in: 3600 });
    getCurrentUser.mockResolvedValue({
      username: 'testuser',
      email: 'test@example.com',
      role: 'admin',
    });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await result.current.login('testuser', 'password');

    await waitFor(() => {
      expect(result.current.user).not.toBeNull();
      expect(result.current.user?.username).toBe('testuser');
      expect(result.current.isAuthenticated).toBe(true);
    });
  });

  it('logs out user', async () => {
    const { login, getCurrentUser } = require('../api/client');

    login.mockResolvedValue({ access_token: 'test-token', expires_in: 3600 });
    getCurrentUser.mockResolvedValue({
      username: 'testuser',
      email: 'test@example.com',
      role: 'admin',
    });

    const { result } = renderHook(() => useAuth(), { wrapper });

    // Login first
    await result.current.login('testuser', 'password');

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true);
    });

    // Then logout
    result.current.logout();

    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('handles login failure', async () => {
    const { login } = require('../api/client');

    login.mockRejectedValue(new Error('Invalid credentials'));

    const { result } = renderHook(() => useAuth(), { wrapper });

    await expect(result.current.login('wrong', 'wrong')).rejects.toThrow();

    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('loads user from stored token on mount', async () => {
    const { getCurrentUser } = require('../api/client');

    // Set token in localStorage
    localStorage.setItem('token', 'stored-token');

    getCurrentUser.mockResolvedValue({
      username: 'storeduser',
      email: 'stored@example.com',
      role: 'viewer',
    });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.user).not.toBeNull();
      expect(result.current.user?.username).toBe('storeduser');
    });

    // Cleanup
    localStorage.removeItem('token');
  });
});
