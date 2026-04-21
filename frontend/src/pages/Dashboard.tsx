import { useEffect, useState } from 'react';
import {
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Chip,
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Pending as PendingIcon,
  Folder as FolderIcon,
} from '@mui/icons-material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { getStatistics, getSystemStatus } from '../api/client';
import type { Statistics, SystemStatus } from '../types';

export default function Dashboard() {
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const [stats, status] = await Promise.all([
        getStatistics(),
        getSystemStatus(),
      ]);
      setStatistics(stats);
      setSystemStatus(status);
      setError(null);
    } catch (err) {
      setError('Failed to load dashboard data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  const statusColor = systemStatus?.status === 'healthy' ? 'success' :
                      systemStatus?.status === 'degraded' ? 'warning' : 'error';

  const chartData = statistics?.reviews_by_status
    ? Object.entries(statistics.reviews_by_status).map(([status, count]) => ({
        status,
        count,
      }))
    : [];

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>

      {/* System Status */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box display="flex" alignItems="center" gap={2}>
          <Typography variant="h6">System Status:</Typography>
          <Chip
            label={systemStatus?.status.toUpperCase()}
            color={statusColor}
            size="small"
          />
          <Typography variant="body2" color="text.secondary">
            Version: {systemStatus?.version}
          </Typography>
        </Box>
      </Paper>

      {/* Statistics Cards */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <FolderIcon color="primary" />
                <Typography color="text.secondary" variant="body2">
                  Total Repositories
                </Typography>
              </Box>
              <Typography variant="h4">
                {statistics?.total_repositories || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {statistics?.active_repositories || 0} active
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <CheckCircleIcon color="success" />
                <Typography color="text.secondary" variant="body2">
                  Completed Reviews
                </Typography>
              </Box>
              <Typography variant="h4">
                {statistics?.reviews_by_status?.completed || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <PendingIcon color="warning" />
                <Typography color="text.secondary" variant="body2">
                  Pending Reviews
                </Typography>
              </Box>
              <Typography variant="h4">
                {(statistics?.reviews_by_status?.pending || 0) +
                  (statistics?.reviews_by_status?.in_progress || 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <ErrorIcon color="error" />
                <Typography color="text.secondary" variant="body2">
                  Failed Reviews
                </Typography>
              </Box>
              <Typography variant="h4">
                {statistics?.reviews_by_status?.failed || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Reviews Chart */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Reviews by Status
        </Typography>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="status" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="count" fill="#1976d2" />
          </BarChart>
        </ResponsiveContainer>
      </Paper>

      {/* Recent Reviews */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Recent Reviews
        </Typography>
        {statistics?.recent_reviews && statistics.recent_reviews.length > 0 ? (
          <Box>
            {statistics.recent_reviews.map((review) => (
              <Box
                key={review.id}
                sx={{
                  p: 2,
                  mb: 1,
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                }}
              >
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Box>
                    <Typography variant="body1">
                      PR #{review.pr_number}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {new Date(review.created_at).toLocaleString()}
                    </Typography>
                  </Box>
                  <Chip
                    label={review.status}
                    color={
                      review.status === 'completed' ? 'success' :
                      review.status === 'failed' ? 'error' :
                      'default'
                    }
                    size="small"
                  />
                </Box>
              </Box>
            ))}
          </Box>
        ) : (
          <Typography color="text.secondary">No recent reviews</Typography>
        )}
      </Paper>
    </Box>
  );
}
