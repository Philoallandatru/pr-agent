import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  IconButton,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Alert,
  LinearProgress,
  Tabs,
  Tab,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  PlayArrow as ActivateIcon,
  Refresh as RefreshIcon,
  Assessment as MetricsIcon,
  Science as TestIcon,
} from '@mui/icons-material';
import { apiClient } from '../api/client';

interface Model {
  model_id: string;
  name: string;
  provider: string;
  model_type: string;
  version: string;
  status: string;
  created_at: string;
  updated_at: string;
  metrics: ModelMetrics;
  tags: string[];
}

interface ModelMetrics {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  total_tokens: number;
  avg_latency: number;
  error_rate: number;
  last_used: string | null;
}

interface ABTest {
  test_id: string;
  models: string[];
  traffic_split: Record<string, number>;
  created_at: string;
  metrics: Record<string, ModelMetrics>;
}

const Models: React.FC = () => {
  const [models, setModels] = useState<Model[]>([]);
  const [abTests, setABTests] = useState<ABTest[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTab, setSelectedTab] = useState(0);

  // Dialog states
  const [registerDialogOpen, setRegisterDialogOpen] = useState(false);
  const [metricsDialogOpen, setMetricsDialogOpen] = useState(false);
  const [abTestDialogOpen, setABTestDialogOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState<Model | null>(null);

  // Form states
  const [newModel, setNewModel] = useState({
    model_id: '',
    name: '',
    provider: 'openai',
    model_type: 'chat',
    version: '',
    config: '{}',
    tags: '',
  });

  const [newABTest, setNewABTest] = useState({
    test_id: '',
    models: [] as string[],
    traffic_split: {} as Record<string, number>,
  });

  useEffect(() => {
    loadModels();
    loadABTests();
  }, []);

  const loadModels = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get('/api/models');
      setModels(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load models');
    } finally {
      setLoading(false);
    }
  };

  const loadABTests = async () => {
    try {
      // Note: This endpoint would need to be added to list all tests
      // For now, we'll just use an empty array
      setABTests([]);
    } catch (err) {
      console.error('Failed to load A/B tests:', err);
    }
  };

  const handleRegisterModel = async () => {
    try {
      const config = JSON.parse(newModel.config);
      const tags = newModel.tags.split(',').map(t => t.trim()).filter(t => t);

      await apiClient.post('/api/models', {
        ...newModel,
        config,
        tags,
      });

      setRegisterDialogOpen(false);
      setNewModel({
        model_id: '',
        name: '',
        provider: 'openai',
        model_type: 'chat',
        version: '',
        config: '{}',
        tags: '',
      });
      loadModels();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to register model');
    }
  };

  const handleActivateModel = async (modelId: string) => {
    try {
      await apiClient.post(`/api/models/${modelId}/activate`);
      loadModels();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to activate model');
    }
  };

  const handleDeleteModel = async (modelId: string) => {
    if (!window.confirm(`Are you sure you want to delete model ${modelId}?`)) {
      return;
    }

    try {
      await apiClient.delete(`/api/models/${modelId}`);
      loadModels();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete model');
    }
  };

  const handleViewMetrics = (model: Model) => {
    setSelectedModel(model);
    setMetricsDialogOpen(true);
  };

  const handleCreateABTest = async () => {
    try {
      await apiClient.post('/api/ab-tests', newABTest);
      setABTestDialogOpen(false);
      setNewABTest({
        test_id: '',
        models: [],
        traffic_split: {},
      });
      loadABTests();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create A/B test');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'success';
      case 'testing': return 'info';
      case 'inactive': return 'default';
      case 'deprecated': return 'warning';
      case 'failed': return 'error';
      default: return 'default';
    }
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat().format(num);
  };

  const formatPercentage = (num: number) => {
    return `${(num * 100).toFixed(2)}%`;
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">AI Model Management</Typography>
        <Box>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setRegisterDialogOpen(true)}
            sx={{ mr: 1 }}
          >
            Register Model
          </Button>
          <Button
            variant="outlined"
            startIcon={<TestIcon />}
            onClick={() => setABTestDialogOpen(true)}
            sx={{ mr: 1 }}
          >
            Create A/B Test
          </Button>
          <IconButton onClick={loadModels}>
            <RefreshIcon />
          </IconButton>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {loading && <LinearProgress sx={{ mb: 2 }} />}

      <Tabs value={selectedTab} onChange={(_, v) => setSelectedTab(v)} sx={{ mb: 2 }}>
        <Tab label="Models" />
        <Tab label="A/B Tests" />
      </Tabs>

      {selectedTab === 0 && (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Model ID</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>Provider</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Version</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Requests</TableCell>
                <TableCell>Error Rate</TableCell>
                <TableCell>Avg Latency</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {models.map((model) => (
                <TableRow key={model.model_id}>
                  <TableCell>{model.model_id}</TableCell>
                  <TableCell>{model.name}</TableCell>
                  <TableCell>{model.provider}</TableCell>
                  <TableCell>{model.model_type}</TableCell>
                  <TableCell>{model.version}</TableCell>
                  <TableCell>
                    <Chip
                      label={model.status}
                      color={getStatusColor(model.status) as any}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>{formatNumber(model.metrics.total_requests)}</TableCell>
                  <TableCell>{formatPercentage(model.metrics.error_rate)}</TableCell>
                  <TableCell>{model.metrics.avg_latency.toFixed(2)}s</TableCell>
                  <TableCell>
                    <IconButton
                      size="small"
                      onClick={() => handleViewMetrics(model)}
                      title="View Metrics"
                    >
                      <MetricsIcon />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => handleActivateModel(model.model_id)}
                      disabled={model.status === 'active'}
                      title="Activate"
                    >
                      <ActivateIcon />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => handleDeleteModel(model.model_id)}
                      title="Delete"
                    >
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {selectedTab === 1 && (
        <Grid container spacing={2}>
          {abTests.length === 0 ? (
            <Grid item xs={12}>
              <Paper sx={{ p: 3, textAlign: 'center' }}>
                <Typography color="textSecondary">
                  No A/B tests running. Create one to get started.
                </Typography>
              </Paper>
            </Grid>
          ) : (
            abTests.map((test) => (
              <Grid item xs={12} md={6} key={test.test_id}>
                <Card>
                  <CardContent>
                    <Typography variant="h6">{test.test_id}</Typography>
                    <Typography color="textSecondary" gutterBottom>
                      Models: {test.models.join(', ')}
                    </Typography>
                    {/* Add test metrics display here */}
                  </CardContent>
                </Card>
              </Grid>
            ))
          )}
        </Grid>
      )}

      {/* Register Model Dialog */}
      <Dialog open={registerDialogOpen} onClose={() => setRegisterDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Register New Model</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Model ID"
            value={newModel.model_id}
            onChange={(e) => setNewModel({ ...newModel, model_id: e.target.value })}
            margin="normal"
            required
          />
          <TextField
            fullWidth
            label="Name"
            value={newModel.name}
            onChange={(e) => setNewModel({ ...newModel, name: e.target.value })}
            margin="normal"
            required
          />
          <Select
            fullWidth
            value={newModel.provider}
            onChange={(e) => setNewModel({ ...newModel, provider: e.target.value })}
            margin="dense"
          >
            <MenuItem value="openai">OpenAI</MenuItem>
            <MenuItem value="anthropic">Anthropic</MenuItem>
            <MenuItem value="ollama">Ollama</MenuItem>
            <MenuItem value="azure">Azure</MenuItem>
            <MenuItem value="google">Google</MenuItem>
          </Select>
          <Select
            fullWidth
            value={newModel.model_type}
            onChange={(e) => setNewModel({ ...newModel, model_type: e.target.value })}
            margin="dense"
          >
            <MenuItem value="chat">Chat</MenuItem>
            <MenuItem value="completion">Completion</MenuItem>
            <MenuItem value="embedding">Embedding</MenuItem>
            <MenuItem value="classification">Classification</MenuItem>
          </Select>
          <TextField
            fullWidth
            label="Version"
            value={newModel.version}
            onChange={(e) => setNewModel({ ...newModel, version: e.target.value })}
            margin="normal"
            required
          />
          <TextField
            fullWidth
            label="Config (JSON)"
            value={newModel.config}
            onChange={(e) => setNewModel({ ...newModel, config: e.target.value })}
            margin="normal"
            multiline
            rows={3}
          />
          <TextField
            fullWidth
            label="Tags (comma-separated)"
            value={newModel.tags}
            onChange={(e) => setNewModel({ ...newModel, tags: e.target.value })}
            margin="normal"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRegisterDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleRegisterModel} variant="contained">Register</Button>
        </DialogActions>
      </Dialog>

      {/* Metrics Dialog */}
      <Dialog open={metricsDialogOpen} onClose={() => setMetricsDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Model Metrics: {selectedModel?.name}</DialogTitle>
        <DialogContent>
          {selectedModel && (
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle2" color="textSecondary">Total Requests</Typography>
                  <Typography variant="h4">{formatNumber(selectedModel.metrics.total_requests)}</Typography>
                </Paper>
              </Grid>
              <Grid item xs={6}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle2" color="textSecondary">Success Rate</Typography>
                  <Typography variant="h4">
                    {formatPercentage(1 - selectedModel.metrics.error_rate)}
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={6}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle2" color="textSecondary">Total Tokens</Typography>
                  <Typography variant="h4">{formatNumber(selectedModel.metrics.total_tokens)}</Typography>
                </Paper>
              </Grid>
              <Grid item xs={6}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle2" color="textSecondary">Avg Latency</Typography>
                  <Typography variant="h4">{selectedModel.metrics.avg_latency.toFixed(2)}s</Typography>
                </Paper>
              </Grid>
              <Grid item xs={12}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle2" color="textSecondary">Last Used</Typography>
                  <Typography>{selectedModel.metrics.last_used || 'Never'}</Typography>
                </Paper>
              </Grid>
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setMetricsDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* A/B Test Dialog */}
      <Dialog open={abTestDialogOpen} onClose={() => setABTestDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create A/B Test</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Test ID"
            value={newABTest.test_id}
            onChange={(e) => setNewABTest({ ...newABTest, test_id: e.target.value })}
            margin="normal"
            required
          />
          <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>
            Select Models (hold Ctrl/Cmd to select multiple)
          </Typography>
          <Select
            fullWidth
            multiple
            value={newABTest.models}
            onChange={(e) => {
              const selected = e.target.value as string[];
              const split: Record<string, number> = {};
              const percentage = 1 / selected.length;
              selected.forEach(id => split[id] = percentage);
              setNewABTest({ ...newABTest, models: selected, traffic_split: split });
            }}
          >
            {models.map((model) => (
              <MenuItem key={model.model_id} value={model.model_id}>
                {model.name} ({model.model_id})
              </MenuItem>
            ))}
          </Select>
          {newABTest.models.length > 0 && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2">Traffic Split</Typography>
              {newABTest.models.map((modelId) => (
                <Box key={modelId} sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                  <Typography sx={{ flex: 1 }}>{modelId}</Typography>
                  <TextField
                    type="number"
                    value={newABTest.traffic_split[modelId] || 0}
                    onChange={(e) => {
                      const value = parseFloat(e.target.value);
                      setNewABTest({
                        ...newABTest,
                        traffic_split: { ...newABTest.traffic_split, [modelId]: value }
                      });
                    }}
                    inputProps={{ min: 0, max: 1, step: 0.1 }}
                    sx={{ width: 100 }}
                  />
                </Box>
              ))}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setABTestDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreateABTest} variant="contained">Create Test</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Models;
