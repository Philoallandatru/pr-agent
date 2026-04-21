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
  ContentCopy as CopyIcon,
} from '@mui/icons-material';
import {
  getPromptTemplates,
  createPromptTemplate,
  updatePromptTemplate,
  deletePromptTemplate,
} from '../api/client';
import type { PromptTemplate } from '../types';

export default function Prompts() {
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<PromptTemplate | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    content: '',
    is_default: false,
  });

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      const data = await getPromptTemplates();
      setTemplates(data);
      setError(null);
    } catch (err) {
      setError('Failed to load prompt templates');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (template?: PromptTemplate) => {
    if (template) {
      setEditingTemplate(template);
      setFormData({
        name: template.name,
        description: template.description || '',
        content: template.content,
        is_default: template.is_default,
      });
    } else {
      setEditingTemplate(null);
      setFormData({
        name: '',
        description: '',
        content: '',
        is_default: false,
      });
    }
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingTemplate(null);
  };

  const handleSave = async () => {
    try {
      if (editingTemplate) {
        await updatePromptTemplate(editingTemplate.id, formData);
      } else {
        await createPromptTemplate(formData);
      }

      handleCloseDialog();
      loadTemplates();
    } catch (err) {
      setError('Failed to save prompt template');
      console.error(err);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this prompt template?')) return;

    try {
      await deletePromptTemplate(id);
      loadTemplates();
    } catch (err) {
      setError('Failed to delete prompt template');
      console.error(err);
    }
  };

  const handleDuplicate = (template: PromptTemplate) => {
    setEditingTemplate(null);
    setFormData({
      name: `${template.name} (Copy)`,
      description: template.description || '',
      content: template.content,
      is_default: false,
    });
    setDialogOpen(true);
  };

  const handleSetDefault = async (template: PromptTemplate) => {
    try {
      await updatePromptTemplate(template.id, { is_default: true });
      loadTemplates();
    } catch (err) {
      setError('Failed to set default template');
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
        <Typography variant="h4">Prompt Templates</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpenDialog()}
        >
          Add Template
        </Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Description</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Created</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {templates.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  <Typography color="text.secondary">No prompt templates</Typography>
                </TableCell>
              </TableRow>
            ) : (
              templates.map((template) => (
                <TableRow key={template.id}>
                  <TableCell>
                    <Box display="flex" alignItems="center" gap={1}>
                      {template.name}
                      {template.is_default && (
                        <Chip label="Default" color="primary" size="small" />
                      )}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" noWrap sx={{ maxWidth: 300 }}>
                      {template.description || '-'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {template.is_default ? (
                      <Chip label="Active" color="success" size="small" />
                    ) : (
                      <Button
                        size="small"
                        onClick={() => handleSetDefault(template)}
                      >
                        Set as Default
                      </Button>
                    )}
                  </TableCell>
                  <TableCell>
                    {new Date(template.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      onClick={() => handleDuplicate(template)}
                      title="Duplicate"
                    >
                      <CopyIcon />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => handleOpenDialog(template)}
                    >
                      <EditIcon />
                    </IconButton>
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => handleDelete(template.id)}
                      disabled={template.is_default}
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
      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingTemplate ? 'Edit Prompt Template' : 'Add Prompt Template'}
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
              label="Description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              fullWidth
              multiline
              rows={2}
            />
            <TextField
              label="Prompt Content"
              value={formData.content}
              onChange={(e) => setFormData({ ...formData, content: e.target.value })}
              fullWidth
              required
              multiline
              rows={12}
              placeholder="Enter your prompt template here..."
            />
            <Box display="flex" alignItems="center" gap={1}>
              <Typography>Set as Default:</Typography>
              <Switch
                checked={formData.is_default}
                onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
              />
            </Box>
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
