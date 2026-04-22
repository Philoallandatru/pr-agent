import { useEffect, useState } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Chip,
  TextField,
  MenuItem,
  CircularProgress,
  Alert,
  Pagination,
} from '@mui/material';
import {
  Visibility as VisibilityIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { getReviews, getReview } from '../api/client';
import type { PRReview } from '../types';

export default function Reviews() {
  const [reviews, setReviews] = useState<PRReview[]>([]);
  const [selectedReview, setSelectedReview] = useState<PRReview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({
    status: '',
    repository_id: '',
  });

  const itemsPerPage = 20;

  useEffect(() => {
    loadReviews();
  }, [filters]);

  const loadReviews = async () => {
    try {
      setLoading(true);
      const params: Record<string, string> = {};
      if (filters.status) params.status = filters.status;
      if (filters.repository_id) params.repository_id = filters.repository_id;

      const data = await getReviews(params);
      setReviews(data);
      setError(null);
    } catch (err) {
      setError('Failed to load reviews');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetails = async (id: number) => {
    try {
      const review = await getReview(id);
      setSelectedReview(review);
      setDialogOpen(true);
    } catch (err) {
      setError('Failed to load review details');
      console.error(err);
    }
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setSelectedReview(null);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'in_progress':
        return 'info';
      default:
        return 'default';
    }
  };

  const paginatedReviews = reviews.slice(
    (page - 1) * itemsPerPage,
    page * itemsPerPage
  );

  if (loading && reviews.length === 0) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Review History</Typography>
        <IconButton onClick={loadReviews} disabled={loading}>
          <RefreshIcon />
        </IconButton>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box display="flex" gap={2}>
          <TextField
            select
            label="Status"
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            sx={{ minWidth: 150 }}
            size="small"
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="pending">Pending</MenuItem>
            <MenuItem value="in_progress">In Progress</MenuItem>
            <MenuItem value="completed">Completed</MenuItem>
            <MenuItem value="failed">Failed</MenuItem>
          </TextField>
          <TextField
            label="Repository ID"
            value={filters.repository_id}
            onChange={(e) => setFilters({ ...filters, repository_id: e.target.value })}
            size="small"
            placeholder="Filter by repo ID"
          />
        </Box>
      </Paper>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>PR Number</TableCell>
              <TableCell>Repository</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Created</TableCell>
              <TableCell>Completed</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {paginatedReviews.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <Typography color="text.secondary">No reviews found</Typography>
                </TableCell>
              </TableRow>
            ) : (
              paginatedReviews.map((review) => (
                <TableRow key={review.id}>
                  <TableCell>#{review.pr_number}</TableCell>
                  <TableCell>{review.repository_id}</TableCell>
                  <TableCell>
                    <Chip
                      label={review.status}
                      color={getStatusColor(review.status)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    {new Date(review.created_at).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    {review.completed_at
                      ? new Date(review.completed_at).toLocaleString()
                      : '-'}
                  </TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      onClick={() => handleViewDetails(review.id)}
                    >
                      <VisibilityIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Pagination */}
      {reviews.length > itemsPerPage && (
        <Box display="flex" justifyContent="center" mt={3}>
          <Pagination
            count={Math.ceil(reviews.length / itemsPerPage)}
            page={page}
            onChange={(_, value) => setPage(value)}
            color="primary"
          />
        </Box>
      )}

      {/* Details Dialog */}
      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          Review Details - PR #{selectedReview?.pr_number}
        </DialogTitle>
        <DialogContent>
          {selectedReview && (
            <Box sx={{ pt: 2 }}>
              <Box mb={2}>
                <Typography variant="subtitle2" color="text.secondary">
                  Status
                </Typography>
                <Chip
                  label={selectedReview.status}
                  color={getStatusColor(selectedReview.status)}
                  size="small"
                />
              </Box>

              <Box mb={2}>
                <Typography variant="subtitle2" color="text.secondary">
                  Repository ID
                </Typography>
                <Typography>{selectedReview.repository_id}</Typography>
              </Box>

              <Box mb={2}>
                <Typography variant="subtitle2" color="text.secondary">
                  Created At
                </Typography>
                <Typography>
                  {new Date(selectedReview.created_at).toLocaleString()}
                </Typography>
              </Box>

              {selectedReview.completed_at && (
                <Box mb={2}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Completed At
                  </Typography>
                  <Typography>
                    {new Date(selectedReview.completed_at).toLocaleString()}
                  </Typography>
                </Box>
              )}

              {selectedReview.result && (
                <Box mb={2}>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Review Result
                  </Typography>
                  <Paper
                    sx={{
                      p: 2,
                      bgcolor: 'grey.50',
                      maxHeight: 400,
                      overflow: 'auto',
                    }}
                  >
                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                      {JSON.stringify(selectedReview.result, null, 2)}
                    </pre>
                  </Paper>
                </Box>
              )}

              {selectedReview.error && (
                <Box mb={2}>
                  <Typography variant="subtitle2" color="error" gutterBottom>
                    Error
                  </Typography>
                  <Alert severity="error">{selectedReview.error}</Alert>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
