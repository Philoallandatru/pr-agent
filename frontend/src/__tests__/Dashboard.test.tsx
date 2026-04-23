import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Dashboard from '../pages/Dashboard';
import { apiClient } from '../api/client';

// Mock the API client
jest.mock('../api/client');

const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;

const mockStats = {
  total_reviews: 150,
  completed_reviews: 120,
  pending_reviews: 30,
  average_review_time: 2.5,
  average_comments: 8.3,
  quality_score: 87.5,
};

const mockTrends = [
  { date: '2024-01-01', value: 10 },
  { date: '2024-01-02', value: 15 },
  { date: '2024-01-03', value: 12 },
];

const mockDistribution = [
  { status: 'completed', count: 120 },
  { status: 'pending', count: 30 },
];

const mockReviewers = [
  { reviewer: 'Alice', count: 45 },
  { reviewer: 'Bob', count: 38 },
  { reviewer: 'Charlie', count: 37 },
];

describe('Dashboard Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state initially', () => {
    mockApiClient.get.mockImplementation(() => new Promise(() => {}));

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('renders dashboard with data', async () => {
    mockApiClient.get.mockImplementation((url) => {
      if (url.includes('/stats')) {
        return Promise.resolve({ data: mockStats });
      } else if (url.includes('/trends')) {
        return Promise.resolve({ data: mockTrends });
      } else if (url.includes('/distribution')) {
        return Promise.resolve({ data: { distribution: mockDistribution } });
      } else if (url.includes('/top-reviewers')) {
        return Promise.resolve({ data: { reviewers: mockReviewers } });
      }
      return Promise.reject(new Error('Unknown endpoint'));
    });

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Code Review Dashboard')).toBeInTheDocument();
    });

    // Check stats cards
    expect(screen.getByText('Total Reviews')).toBeInTheDocument();
    expect(screen.getByText('150')).toBeInTheDocument();
    expect(screen.getByText('Completed')).toBeInTheDocument();
    expect(screen.getByText('120')).toBeInTheDocument();
    expect(screen.getByText('Pending')).toBeInTheDocument();
    expect(screen.getByText('30')).toBeInTheDocument();
  });

  it('handles API errors gracefully', async () => {
    mockApiClient.get.mockRejectedValue({
      response: { data: { detail: 'API Error' } },
    });

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/API Error/i)).toBeInTheDocument();
    });
  });

  it('allows time range selection', async () => {
    mockApiClient.get.mockResolvedValue({ data: mockStats });

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByLabelText('Time Range')).toBeInTheDocument();
    });
  });
});
