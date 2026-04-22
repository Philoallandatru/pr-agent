import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  FormControlLabel,
  FormGroup,
  IconButton,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Chip,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  Backup as BackupIcon,
  Restore as RestoreIcon,
  Delete as DeleteIcon,
  Download as DownloadIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { apiClient } from '../api/client';

interface Backup {
  timestamp: string;
  created_at: string;
  description?: string;
  includes: {
    database: boolean;
    config: boolean;
    cache: boolean;
    logs: boolean;
  };
  size_bytes: number;
  path: string;
}

const Backups: React.FC = () => {
  const [backups, setBackups] = useState<Backup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Create backup dialog
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [createOptions, setCreateOptions] = useState({
    include_db: true,
    include_config: true,
    include_cache: false,
    include_logs: false,
    description: '',
  });
  const [creating, setCreating] = useState(false);

  // Restore dialog
  const [restoreDialogOpen, setRestoreDialogOpen] = useState(false);
  const [selectedBackup, setSelectedBackup] = useState<Backup | null>(null);
  const [restoreOptions, setRestoreOptions] = useState({
    restore_db: true,
    restore_config: true,
    restore_cache: false,
    restore_logs: false,
    create_backup_before_restore: true,
  });
  const [restoring, setRestoring] = useState(false);

  // Delete dialog
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [backupToDelete, setBackupToDelete] = useState<Backup | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Info dialog
  const [infoDialogOpen, setInfoDialogOpen] = useState(false);
  const [backupInfo, setBackupInfo] = useState<Backup | null>(null);

  useEffect(() => {
    loadBackups();
  }, []);

  const loadBackups = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.get('/api/backups');
      setBackups(response.data.backups);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load backups');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateBackup = async () => {
    try {
      setCreating(true);
      setError(null);
      await apiClient.post('/api/backups', createOptions);
      setSuccess('Backup created successfully');
      setCreateDialogOpen(false);
      setCreateOptions({
        include_db: true,
        include_config: true,
        include_cache: false,
        include_logs: false,
        description: '',
      });
      await loadBackups();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create backup');
    } finally {
      setCreating(false);
    }
  };

  const handleRestoreBackup = async () => {
    if (!selectedBackup) return;

    try {
      setRestoring(true);
      setError(null);
      const backupId = selectedBackup.timestamp;
      await apiClient.post(`/api/backups/${backupId}/restore`, restoreOptions);
      setSuccess('Backup restored successfully. Please restart the application.');
      setRestoreDialogOpen(false);
      setSelectedBackup(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to restore backup');
    } finally {
      setRestoring(false);
    }
  };

  const handleDeleteBackup = async () => {
    if (!backupToDelete) return;

    try {
      setDeleting(true);
      setError(null);
      const backupId = backupToDelete.timestamp;
      await apiClient.delete(`/api/backups/${backupId}`);
      setSuccess('Backup deleted successfully');
      setDeleteDialogOpen(false);
      setBackupToDelete(null);
      await loadBackups();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete backup');
    } finally {
      setDeleting(false);
    }
  };

  const handleShowInfo = async (backup: Backup) => {
    try {
      const response = await apiClient.get(`/api/backups/${backup.timestamp}`);
      setBackupInfo(response.data);
      setInfoDialogOpen(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load backup info');
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Backup & Restore</Typography>
        <Button
          variant="contained"
          startIcon={<BackupIcon />}
          onClick={() => setCreateDialogOpen(true)}
        >
          Create Backup
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Created</TableCell>
                <TableCell>Description</TableCell>
                <TableCell>Includes</TableCell>
                <TableCell>Size</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {backups.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} align="center">
                    No backups found
                  </TableCell>
                </TableRow>
              ) : (
                backups.map((backup) => (
                  <TableRow key={backup.timestamp}>
                    <TableCell>{formatDate(backup.created_at)}</TableCell>
                    <TableCell>{backup.description || '-'}</TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                        {backup.includes.database && <Chip label="DB" size="small" color="primary" />}
                        {backup.includes.config && <Chip label="Config" size="small" color="secondary" />}
                        {backup.includes.cache && <Chip label="Cache" size="small" />}
                        {backup.includes.logs && <Chip label="Logs" size="small" />}
                      </Box>
                    </TableCell>
                    <TableCell>{formatBytes(backup.size_bytes)}</TableCell>
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        onClick={() => handleShowInfo(backup)}
                        title="Info"
                      >
                        <InfoIcon />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => {
                          setSelectedBackup(backup);
                          setRestoreDialogOpen(true);
                        }}
                        title="Restore"
                      >
                        <RestoreIcon />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => {
                          setBackupToDelete(backup);
                          setDeleteDialogOpen(true);
                        }}
                        title="Delete"
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
      )}

      {/* Create Backup Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create Backup</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            Select what to include in the backup:
          </DialogContentText>
          <FormGroup>
            <FormControlLabel
              control={
                <Checkbox
                  checked={createOptions.include_db}
                  onChange={(e) => setCreateOptions({ ...createOptions, include_db: e.target.checked })}
                />
              }
              label="Database"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={createOptions.include_config}
                  onChange={(e) => setCreateOptions({ ...createOptions, include_config: e.target.checked })}
                />
              }
              label="Configuration"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={createOptions.include_cache}
                  onChange={(e) => setCreateOptions({ ...createOptions, include_cache: e.target.checked })}
                />
              }
              label="Cache"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={createOptions.include_logs}
                  onChange={(e) => setCreateOptions({ ...createOptions, include_logs: e.target.checked })}
                />
              }
              label="Logs"
            />
          </FormGroup>
          <TextField
            fullWidth
            label="Description (optional)"
            value={createOptions.description}
            onChange={(e) => setCreateOptions({ ...createOptions, description: e.target.value })}
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreateBackup} variant="contained" disabled={creating}>
            {creating ? <CircularProgress size={24} /> : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Restore Dialog */}
      <Dialog open={restoreDialogOpen} onClose={() => setRestoreDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Restore Backup</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            Restoring will overwrite current data. This action cannot be undone.
          </Alert>
          <DialogContentText sx={{ mb: 2 }}>
            Select what to restore:
          </DialogContentText>
          <FormGroup>
            <FormControlLabel
              control={
                <Checkbox
                  checked={restoreOptions.restore_db}
                  onChange={(e) => setRestoreOptions({ ...restoreOptions, restore_db: e.target.checked })}
                />
              }
              label="Database"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={restoreOptions.restore_config}
                  onChange={(e) => setRestoreOptions({ ...restoreOptions, restore_config: e.target.checked })}
                />
              }
              label="Configuration"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={restoreOptions.restore_cache}
                  onChange={(e) => setRestoreOptions({ ...restoreOptions, restore_cache: e.target.checked })}
                />
              }
              label="Cache"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={restoreOptions.restore_logs}
                  onChange={(e) => setRestoreOptions({ ...restoreOptions, restore_logs: e.target.checked })}
                />
              }
              label="Logs"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={restoreOptions.create_backup_before_restore}
                  onChange={(e) => setRestoreOptions({ ...restoreOptions, create_backup_before_restore: e.target.checked })}
                />
              }
              label="Create backup before restore"
            />
          </FormGroup>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRestoreDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleRestoreBackup} variant="contained" color="warning" disabled={restoring}>
            {restoring ? <CircularProgress size={24} /> : 'Restore'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Backup</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete this backup? This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleDeleteBackup} variant="contained" color="error" disabled={deleting}>
            {deleting ? <CircularProgress size={24} /> : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Info Dialog */}
      <Dialog open={infoDialogOpen} onClose={() => setInfoDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Backup Information</DialogTitle>
        <DialogContent>
          {backupInfo && (
            <Box>
              <Typography variant="body2" gutterBottom>
                <strong>Created:</strong> {formatDate(backupInfo.created_at)}
              </Typography>
              <Typography variant="body2" gutterBottom>
                <strong>Size:</strong> {formatBytes(backupInfo.size_bytes)}
              </Typography>
              <Typography variant="body2" gutterBottom>
                <strong>Description:</strong> {backupInfo.description || 'None'}
              </Typography>
              <Typography variant="body2" gutterBottom>
                <strong>Includes:</strong>
              </Typography>
              <Box sx={{ pl: 2 }}>
                <Typography variant="body2">• Database: {backupInfo.includes.database ? 'Yes' : 'No'}</Typography>
                <Typography variant="body2">• Configuration: {backupInfo.includes.config ? 'Yes' : 'No'}</Typography>
                <Typography variant="body2">• Cache: {backupInfo.includes.cache ? 'Yes' : 'No'}</Typography>
                <Typography variant="body2">• Logs: {backupInfo.includes.logs ? 'Yes' : 'No'}</Typography>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setInfoDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Backups;
