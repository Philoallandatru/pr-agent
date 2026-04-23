import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import {
  TrendingUp,
  Code,
  CheckCircle,
  Warning,
  Speed,
  People,
} from '@mui/icons-material';
import { Line, Bar, Pie, Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { apiClient } from '../api/client';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface DashboardStats {
  total_reviews: number;
  completed_reviews: number;
  pending_reviews: number;
  average_review_time: number;
  average_comments: number;
  quality_score: number;
}

interface TrendData {
  labels: string[];
  datasets: {
    label: string;
    data: number[];
    borderColor?: string;
    backgroundColor?: string;
    fill?: boolean;
  }[];
}

interface ReviewDistribution {
  status: string;
  count: number;
}

const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [timeRange, setTimeRange] = useState('7d');
  const [reviewTrends, setReviewTrends] = useState<TrendData | null>(null);
  const [qualityTrends, setQualityTrends] = useState<TrendData | null>(null);
  const [reviewDistribution, setReviewDistribution] = useState<ReviewDistribution[]>([]);
  const [topReviewers, setTopReviewers] = useState<any[]>([]);

  useEffect(() => {
    fetchDashboardData();
  }, [timeRange]);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);

    try {
      // Fetch dashboard statistics
      const statsResponse = await apiClient.get('/api/dashboards/main/stats', {
        params: { time_range: timeRange },
      });
      setStats(statsResponse.data);

      // Fetch review trends
      const trendsResponse = await apiClient.get('/api/dashboards/main/trends', {
        params: { metric: 'reviews', time_range: timeRange },
      });
      setReviewTrends(formatTrendData(trendsResponse.data, 'Reviews'));

      // Fetch quality trends
      const qualityResponse = await apiClient.get('/api/dashboards/main/trends', {
        params: { metric: 'quality', time_range: timeRange },
      });
      setQualityTrends(formatTrendData(qualityResponse.data, 'Quality Score'));

      // Fetch review distribution
      const distributionResponse = await apiClient.get('/api/dashboards/main/distribution');
      setReviewDistribution(distributionResponse.data.distribution || []);

      // Fetch top reviewers
      const reviewersResponse = await apiClient.get('/api/dashboards/main/top-reviewers', {
        params: { limit: 5 },
      });
      setTopReviewers(reviewersResponse.data.reviewers || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const formatTrendData = (data: any[], label: string): TrendData => {
    return {
      labels: data.map((item) => item.date || item.label),
      datasets: [
        {
          label,
          data: data.map((item) => item.value || item.count),
          borderColor: 'rgb(75, 192, 192)',
          backgroundColor: 'rgba(75, 192, 192, 0.2)',
          fill: true,
        },
      ],
    };
  };

  const getDistributionChartData = () => {
    return {
      labels: reviewDistribution.map((item) => item.status),
      datasets: [
        {
          data: reviewDistribution.map((item) => item.count),
          backgroundColor: [
            'rgba(75, 192, 192, 0.8)',
            'rgba(255, 206, 86, 0.8)',
            'rgba(255, 99, 132, 0.8)',
            'rgba(54, 162, 235, 0.8)',
          ],
        },
      ],
    };
  };

  const getTopReviewersChartData = () => {
    return {
      labels: topReviewers.map((r) => r.reviewer),
      datasets: [
        {
          label: 'Reviews',
          data: topReviewers.map((r) => r.count),
          backgroundColor: 'rgba(54, 162, 235, 0.8)',
        },
      ],
    };
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={3}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  return (
    <Box p={3}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" fontWeight="bold">
          Code Review Dashboard
        </Typography>
        <FormControl sx={{ minWidth: 120 }}>
          <InputLabel>Time Range</InputLabel>
          <Select
            value={timeRange}
            label="Time Range"
            onChange={(e) => setTimeRange(e.target.value)}
          >
            <MenuItem value="24h">Last 24 Hours</MenuItem>
            <MenuItem value="7d">Last 7 Days</MenuItem>
            <MenuItem value="30d">Last 30 Days</MenuItem>
            <MenuItem value="90d">Last 90 Days</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Total Reviews
                  </Typography>
                  <Typography variant="h4">{stats?.total_reviews || 0}</Typography>
                </Box>
                <Code fontSize="large" color="primary" />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Completed
                  </Typography>
                  <Typography variant="h4">{stats?.completed_reviews || 0}</Typography>
                </Box>
                <CheckCircle fontSize="large" color="success" />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Pending
                  </Typography>
                  <Typography variant="h4">{stats?.pending_reviews || 0}</Typography>
                </Box>
                <Warning fontSize="large" color="warning" />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Avg Review Time
                  </Typography>
                  <Typography variant="h4">
                    {stats?.average_review_time?.toFixed(1) || 0}h
                  </Typography>
                </Box>
                <Speed fontSize="large" color="info" />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Avg Comments
                  </Typography>
                  <Typography variant="h4">
                    {stats?.average_comments?.toFixed(1) || 0}
                  </Typography>
                </Box>
                <People fontSize="large" color="secondary" />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Quality Score
                  </Typography>
                  <Typography variant="h4">
                    {stats?.quality_score?.toFixed(1) || 0}%
                  </Typography>
                </Box>
                <TrendingUp fontSize="large" color="success" />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Charts */}
      <Grid container spacing={3}>
        {/* Review Trends */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Review Trends
            </Typography>
            {reviewTrends && (
              <Line
                data={reviewTrends}
                options={{
                  responsive: true,
                  maintainAspectRatio: true,
                  plugins: {
                    legend: {
                      display: true,
                      position: 'top',
                    },
                  },
                  scales: {
                    y: {
                      beginAtZero: true,
                    },
                  },
                }}
              />
            )}
          </Paper>
        </Grid>

        {/* Review Distribution */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Review Status
            </Typography>
            {reviewDistribution.length > 0 && (
              <Doughnut
                data={getDistributionChartData()}
                options={{
                  responsive: true,
                  maintainAspectRatio: true,
                  plugins: {
                    legend: {
                      display: true,
                      position: 'bottom',
                    },
                  },
                }}
              />
            )}
          </Paper>
        </Grid>

        {/* Quality Trends */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Quality Score Trends
            </Typography>
            {qualityTrends && (
              <Line
                data={qualityTrends}
                options={{
                  responsive: true,
                  maintainAspectRatio: true,
                  plugins: {
                    legend: {
                      display: true,
                      position: 'top',
                    },
                  },
                  scales: {
                    y: {
                      beginAtZero: true,
                      max: 100,
                    },
                  },
                }}
              />
            )}
          </Paper>
        </Grid>

        {/* Top Reviewers */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Top Reviewers
            </Typography>
            {topReviewers.length > 0 && (
              <Bar
                data={getTopReviewersChartData()}
                options={{
                  responsive: true,
                  maintainAspectRatio: true,
                  plugins: {
                    legend: {
                      display: false,
                    },
                  },
                  scales: {
                    y: {
                      beginAtZero: true,
                    },
                  },
                }}
              />
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;
