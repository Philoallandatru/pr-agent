import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import Dashboard from '../pages/Dashboard';
import { AuthProvider } from '../contexts/AuthContext';

// Mock API client
vi.mock('../api/client', () => ({
  getStatistics: vi.fn(),
  getSystemStatus: vi.fn(),
  getReviews: vi.fn(),
}));

describe('Dashboard Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders dashboard title', () => {
    const { getStatistics, getSystemStatus, getReviews } = require('../api/client');

    getStatistics.mockResolvedValue({
      repositories: { total: 5, active: 3 },
      reviews: { total: 100, success: 90, failed: 10 },
    });
    getSystemStatus.mockResolvedValue({ polling_active: true });
    getReviews.mockResolvedValue([]);

    render(
      <BrowserRouter>
        <AuthProvider>
          <Dashboard />
        </AuthProvider>
      </BrowserRouter>
    );

    expect(screen.getByText(/dashboard/i)).toBeInTheDocument();
  });

  it('displays statistics cards', async () => {
    const { getStatistics, getSystemStatus, getReviews } = require('../api/client');

    getStatistics.mockResolvedValue({
      repositories: { total: 5, active: 3 },
      reviews: { total: 100, success: 90, failed: 10 },
    });
    getSystemStatus.mockResolvedValue({ polling_active: true });
    getReviews.mockResolvedValue([]);

    render(
      <BrowserRouter>
        <AuthProvider>
          <Dashboard />
        </AuthProvider>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/repositories/i)).toBeInTheDocument();
      expect(screen.getByText(/reviews/i)).toBeInTheDocument();
    });
  });

  it('shows loading state initially', () => {
    const { getStatistics, getSystemStatus, getReviews } = require('../api/client');

    // Mock slow API calls
    getStatistics.mockImplementation(() => new Promise(() => {}));
    getSystemStatus.mockImplementation(() => new Promise(() => {}));
    getReviews.mockImplementation(() => new Promise(() => {}));

    render(
      <BrowserRouter>
        <AuthProvider>
          <Dashboard />
        </AuthProvider>
      </BrowserRouter>
    );

    // Should show loading indicators
    expect(screen.getByRole('progressbar') || screen.getByText(/loading/i)).toBeTruthy();
  });

  it('handles API errors gracefully', async () => {
    const { getStatistics, getSystemStatus, getReviews } = require('../api/client');

    getStatistics.mockRejectedValue(new Error('API Error'));
    getSystemStatus.mockRejectedValue(new Error('API Error'));
    getReviews.mockRejectedValue(new Error('API Error'));

    render(
      <BrowserRouter>
        <AuthProvider>
          <Dashboard />
        </AuthProvider>
      </BrowserRouter>
    );

    // Should handle errors without crashing
    await waitFor(() => {
      expect(screen.queryByText(/error/i) || screen.queryByText(/failed/i)).toBeTruthy();
    });
  });
});
