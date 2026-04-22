import { useEffect, useState } from 'react';
import {
  Box,
  Button,
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
  TextField,
  Switch,
  CircularProgress,
  Alert,
  Chip,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import {
  getRepositories,
  createRepository,
  updateRepository,
  deleteRepository,
} from '../api/client';
import type { Repository } from '../types';

export default function Repositories() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRepo, setEditingRepo] = useState<Repository | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    url: '',
    enabled: true,
    config: '{}',
  });

  useEffect(() => {
    loadRepositories();
  }, []);

  const loadRepositories = async () => {
    try {
      const data = await getRepositories();
      setRepositories(data);
      setError(null);
    } catch (err) {
      setError('Failed to load repositories');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (repo?: Repository) => {
    if (repo) {
      setEditingRepo(repo);
      setFormData({
        name: repo.name,
        url: repo.url,
        enabled: repo.enabled,
        config: JSON.stringify(repo.config, null, 2),
      });
    } else {
      setEditingRepo(null);
      setFormData({ name: '', url: '', enabled: true, config: '{}' });
    }
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingRepo(null);
  };

  const handleSave = async () => {
    try {
      const config = JSON.parse(formData.config);
      const data = {
        name: formData.name,
        url: formData.url,
        enabled: formData.enabled,
        config,
      };

      if (editingRepo) {
        await updateRepository(editingRepo.id, data);
      } else {
        await createRepository(data);
      }

      handleCloseDialog();
      loadRepositories();
    } catch (err) {
      setError('Failed to save repository');
      console.error(err);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this repository?')) return;

    try {
      await deleteRepository(id);
      loadRepositories();
    } catch (err) {
      setError('Failed to delete repository');
      console.error(err);
    }
  };

  const handleToggleEnabled = async (repo: Repository) => {
    try {
      await updateRepository(repo.id, { enabled: !repo.enabled });
      loadRepositories();
    } catch (err) {
      setError('Failed to update repository');
      console.error(err);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Repositories</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpenDialog()}
        >
          Add Repository
        </Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>URL</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Created</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {repositories.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  <Typography color="text.secondary">No repositories configured</Typography>
                </TableCell>
              </TableRow>
            ) : (
              repositories.map((repo) => (
                <TableRow key={repo.id}>
                  <TableCell>{repo.name}</TableCell>
                  <TableCell>
                    <Typography variant="body2" noWrap sx={{ maxWidth: 300 }}>
                      {repo.url}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Box display="flex" alignItems="center" gap={1}>
                      <Switch
                        checked={repo.enabled}
                        onChange={() => handleToggleEnabled(repo)}
                        size="small"
                      />
                      <Chip
                        label={repo.enabled ? 'Active' : 'Disabled'}
                        color={repo.enabled ? 'success' : 'default'}
                        size="small"
                      />
                    </Box>
                  </TableCell>
                  <TableCell>
                    {new Date(repo.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      onClick={() => handleOpenDialog(repo)}
                    >
                      <EditIcon />
                    </IconButton>
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => handleDelete(repo.id)}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Add/Edit Dialog */}
      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingRepo ? 'Edit Repository' : 'Add Repository'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="URL"
              value={formData.url}
              onChange={(e) => setFormData({ ...formData, url: e.target.value })}
              fullWidth
              required
              placeholder="https://bitbucket.example.com/scm/project/repo.git"
            />
            <Box display="flex" alignItems="center" gap={1}>
              <Typography>Enabled:</Typography>
              <Switch
                checked={formData.enabled}
                onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
              />
            </Box>
            <TextField
              label="Configuration (JSON)"
              value={formData.config}
              onChange={(e) => setFormData({ ...formData, config: e.target.value })}
              fullWidth
              multiline
              rows={6}
              placeholder='{"branch": "main", "auto_review": true}'
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSave} variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
