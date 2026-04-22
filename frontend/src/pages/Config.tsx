import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Tabs,
  Tab,
  TextField,
  Button,
  Switch,
  FormControlLabel,
  Alert,
  Snackbar,
  CircularProgress,
  Divider,
  Grid,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import SaveIcon from '@mui/icons-material/Save';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import { apiClient } from '../api/client';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

interface ConfigSection {
  [key: string]: any;
}

interface Config {
  polling?: ConfigSection;
  review?: ConfigSection;
  notifications?: ConfigSection;
  performance?: ConfigSection;
  security?: ConfigSection;
  [key: string]: ConfigSection | undefined;
}

export default function ConfigPage() {
  const [tabValue, setTabValue] = useState(0);
  const [config, setConfig] = useState<Config>({});
  const [originalConfig, setOriginalConfig] = useState<Config>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' });
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    loadConfig();
  }, []);

  useEffect(() => {
    setHasChanges(JSON.stringify(config) !== JSON.stringify(originalConfig));
  }, [config, originalConfig]);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/api/config');
      setConfig(response.data);
      setOriginalConfig(JSON.parse(JSON.stringify(response.data)));
    } catch (error) {
      showSnackbar('Failed to load configuration', 'error');
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = async () => {
    try {
      setSaving(true);
      await apiClient.put('/api/config', config);
      setOriginalConfig(JSON.parse(JSON.stringify(config)));
      showSnackbar('Configuration saved successfully', 'success');
    } catch (error) {
      showSnackbar('Failed to save configuration', 'error');
    } finally {
      setSaving(false);
    }
  };

  const resetConfig = () => {
    setConfig(JSON.parse(JSON.stringify(originalConfig)));
    showSnackbar('Configuration reset to last saved state', 'success');
  };

  const showSnackbar = (message: string, severity: 'success' | 'error') => {
    setSnackbar({ open: true, message, severity });
  };

  const updateConfigValue = (section: string, key: string, value: any) => {
    setConfig(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [key]: value
      }
    }));
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
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
        <Typography variant="h4">Configuration</Typography>
        <Box>
          {hasChanges && (
            <Chip label="Unsaved Changes" color="warning" sx={{ mr: 2 }} />
          )}
          <Button
            variant="outlined"
            startIcon={<RestartAltIcon />}
            onClick={resetConfig}
            disabled={!hasChanges || saving}
            sx={{ mr: 1 }}
          >
            Reset
          </Button>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={saveConfig}
            disabled={!hasChanges || saving}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </Box>
      </Box>

      <Paper>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="Polling" />
          <Tab label="Review" />
          <Tab label="Notifications" />
          <Tab label="Performance" />
          <Tab label="Security" />
        </Tabs>

        <TabPanel value={tabValue} index={0}>
          <PollingConfig config={config.polling || {}} updateConfig={updateConfigValue} />
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <ReviewConfig config={config.review || {}} updateConfig={updateConfigValue} />
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <NotificationsConfig config={config.notifications || {}} updateConfig={updateConfigValue} />
        </TabPanel>

        <TabPanel value={tabValue} index={3}>
          <PerformanceConfig config={config.performance || {}} updateConfig={updateConfigValue} />
        </TabPanel>

        <TabPanel value={tabValue} index={4}>
          <SecurityConfig config={config.security || {}} updateConfig={updateConfigValue} />
        </TabPanel>
      </Paper>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert severity={snackbar.severity} onClose={() => setSnackbar({ ...snackbar, open: false })}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

function PollingConfig({ config, updateConfig }: { config: ConfigSection; updateConfig: (section: string, key: string, value: any) => void }) {
  return (
    <Box>
      <Typography variant="h6" gutterBottom>Bitbucket Polling Configuration</Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Configure how the system polls Bitbucket Server for new and updated pull requests.
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12}>
          <FormControlLabel
            control={
              <Switch
                checked={config.enabled ?? true}
                onChange={(e) => updateConfig('polling', 'enabled', e.target.checked)}
              />
            }
            label="Enable Polling"
          />
        </Grid>

        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Polling Interval (seconds)"
            type="number"
            value={config.interval ?? 300}
            onChange={(e) => updateConfig('polling', 'interval', parseInt(e.target.value))}
            helperText="How often to check for new PRs"
          />
        </Grid>

        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Batch Size"
            type="number"
            value={config.batch_size ?? 10}
            onChange={(e) => updateConfig('polling', 'batch_size', parseInt(e.target.value))}
            helperText="Number of PRs to process in parallel"
          />
        </Grid>

        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Max Retries"
            type="number"
            value={config.max_retries ?? 3}
            onChange={(e) => updateConfig('polling', 'max_retries', parseInt(e.target.value))}
            helperText="Maximum retry attempts for failed requests"
          />
        </Grid>

        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="State Retention Days"
            type="number"
            value={config.state_retention_days ?? 30}
            onChange={(e) => updateConfig('polling', 'state_retention_days', parseInt(e.target.value))}
            helperText="How long to keep polling state history"
          />
        </Grid>
      </Grid>
    </Box>
  );
}

function ReviewConfig({ config, updateConfig }: { config: ConfigSection; updateConfig: (section: string, key: string, value: any) => void }) {
  return (
    <Box>
      <Typography variant="h6" gutterBottom>Review Configuration</Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Configure automatic code review behavior and settings.
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12}>
          <FormControlLabel
            control={
              <Switch
                checked={config.auto_review ?? true}
                onChange={(e) => updateConfig('review', 'auto_review', e.target.checked)}
              />
            }
            label="Enable Auto Review"
          />
        </Grid>

        <Grid item xs={12}>
          <FormControlLabel
            control={
              <Switch
                checked={config.review_on_update ?? true}
                onChange={(e) => updateConfig('review', 'review_on_update', e.target.checked)}
              />
            }
            label="Review on PR Update"
          />
        </Grid>

        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Review Timeout (seconds)"
            type="number"
            value={config.timeout ?? 600}
            onChange={(e) => updateConfig('review', 'timeout', parseInt(e.target.value))}
            helperText="Maximum time for a single review"
          />
        </Grid>

        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Max Context Size (tokens)"
            type="number"
            value={config.max_context_size ?? 8000}
            onChange={(e) => updateConfig('review', 'max_context_size', parseInt(e.target.value))}
            helperText="Maximum tokens for code context"
          />
        </Grid>

        <Grid item xs={12}>
          <FormControlLabel
            control={
              <Switch
                checked={config.include_full_context ?? false}
                onChange={(e) => updateConfig('review', 'include_full_context', e.target.checked)}
              />
            }
            label="Include Full Repository Context"
          />
        </Grid>

        <Grid item xs={12}>
          <TextField
            fullWidth
            label="AI Model"
            value={config.model ?? 'gpt-4'}
            onChange={(e) => updateConfig('review', 'model', e.target.value)}
            helperText="AI model to use for reviews"
          />
        </Grid>
      </Grid>
    </Box>
  );
}

function NotificationsConfig({ config, updateConfig }: { config: ConfigSection; updateConfig: (section: string, key: string, value: any) => void }) {
  return (
    <Box>
      <Typography variant="h6" gutterBottom>Notification Configuration</Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Configure notification channels for review events.
      </Typography>

      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography>Slack</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={config.slack_enabled ?? false}
                    onChange={(e) => updateConfig('notifications', 'slack_enabled', e.target.checked)}
                  />
                }
                label="Enable Slack Notifications"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Slack Webhook URL"
                value={config.slack_webhook_url ?? ''}
                onChange={(e) => updateConfig('notifications', 'slack_webhook_url', e.target.value)}
                disabled={!config.slack_enabled}
              />
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography>Email</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={config.email_enabled ?? false}
                    onChange={(e) => updateConfig('notifications', 'email_enabled', e.target.checked)}
                  />
                }
                label="Enable Email Notifications"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="SMTP Server"
                value={config.smtp_server ?? ''}
                onChange={(e) => updateConfig('notifications', 'smtp_server', e.target.value)}
                disabled={!config.email_enabled}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="SMTP Port"
                type="number"
                value={config.smtp_port ?? 587}
                onChange={(e) => updateConfig('notifications', 'smtp_port', parseInt(e.target.value))}
                disabled={!config.email_enabled}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="From Email"
                value={config.from_email ?? ''}
                onChange={(e) => updateConfig('notifications', 'from_email', e.target.value)}
                disabled={!config.email_enabled}
              />
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography>DingTalk (钉钉)</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={config.dingtalk_enabled ?? false}
                    onChange={(e) => updateConfig('notifications', 'dingtalk_enabled', e.target.checked)}
                  />
                }
                label="Enable DingTalk Notifications"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="DingTalk Webhook URL"
                value={config.dingtalk_webhook_url ?? ''}
                onChange={(e) => updateConfig('notifications', 'dingtalk_webhook_url', e.target.value)}
                disabled={!config.dingtalk_enabled}
              />
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>
    </Box>
  );
}

function PerformanceConfig({ config, updateConfig }: { config: ConfigSection; updateConfig: (section: string, key: string, value: any) => void }) {
  return (
    <Box>
      <Typography variant="h6" gutterBottom>Performance Configuration</Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Configure caching and performance optimization settings.
      </Typography>

      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography>Caching</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={config.cache_enabled ?? true}
                    onChange={(e) => updateConfig('performance', 'cache_enabled', e.target.checked)}
                  />
                }
                label="Enable Caching"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Cache TTL (seconds)"
                type="number"
                value={config.cache_ttl ?? 3600}
                onChange={(e) => updateConfig('performance', 'cache_ttl', parseInt(e.target.value))}
                disabled={!config.cache_enabled}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Max Cache Size (MB)"
                type="number"
                value={config.max_cache_size ?? 1024}
                onChange={(e) => updateConfig('performance', 'max_cache_size', parseInt(e.target.value))}
                disabled={!config.cache_enabled}
              />
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography>Database</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Connection Pool Size"
                type="number"
                value={config.db_pool_size ?? 10}
                onChange={(e) => updateConfig('performance', 'db_pool_size', parseInt(e.target.value))}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Query Timeout (seconds)"
                type="number"
                value={config.db_query_timeout ?? 30}
                onChange={(e) => updateConfig('performance', 'db_query_timeout', parseInt(e.target.value))}
              />
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>
    </Box>
  );
}

function SecurityConfig({ config, updateConfig }: { config: ConfigSection; updateConfig: (section: string, key: string, value: any) => void }) {
  return (
    <Box>
      <Typography variant="h6" gutterBottom>Security Configuration</Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Configure authentication, authorization, and security settings.
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="JWT Secret"
            type="password"
            value={config.jwt_secret ?? ''}
            onChange={(e) => updateConfig('security', 'jwt_secret', e.target.value)}
            helperText="Secret key for JWT token signing"
          />
        </Grid>

        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Token Expiry (seconds)"
            type="number"
            value={config.token_expiry ?? 3600}
            onChange={(e) => updateConfig('security', 'token_expiry', parseInt(e.target.value))}
            helperText="JWT token expiration time"
          />
        </Grid>

        <Grid item xs={12}>
          <FormControlLabel
            control={
              <Switch
                checked={config.require_https ?? true}
                onChange={(e) => updateConfig('security', 'require_https', e.target.checked)}
              />
            }
            label="Require HTTPS"
          />
        </Grid>

        <Grid item xs={12}>
          <FormControlLabel
            control={
              <Switch
                checked={config.enable_cors ?? true}
                onChange={(e) => updateConfig('security', 'enable_cors', e.target.checked)}
              />
            }
            label="Enable CORS"
          />
        </Grid>

        <Grid item xs={12}>
          <TextField
            fullWidth
            label="Allowed Origins"
            value={config.allowed_origins ?? '*'}
            onChange={(e) => updateConfig('security', 'allowed_origins', e.target.value)}
            helperText="Comma-separated list of allowed origins"
            disabled={!config.enable_cors}
          />
        </Grid>

        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Max Login Attempts"
            type="number"
            value={config.max_login_attempts ?? 5}
            onChange={(e) => updateConfig('security', 'max_login_attempts', parseInt(e.target.value))}
            helperText="Maximum failed login attempts before lockout"
          />
        </Grid>

        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Lockout Duration (seconds)"
            type="number"
            value={config.lockout_duration ?? 900}
            onChange={(e) => updateConfig('security', 'lockout_duration', parseInt(e.target.value))}
            helperText="Account lockout duration after max attempts"
          />
        </Grid>
      </Grid>
    </Box>
  );
}
