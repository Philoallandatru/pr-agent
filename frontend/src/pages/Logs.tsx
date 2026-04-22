import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  IconButton,
  Chip,
  Stack,
  Alert,
} from '@mui/material';
import {
  PlayArrow,
  Pause,
  Clear,
  Download,
  Refresh,
} from '@mui/icons-material';

interface LogEntry {
  timestamp: string;
  level: string;
  logger: string;
  message: string;
  module: string;
  function: string;
  line: number;
}

const LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];

const LEVEL_COLORS: Record<string, string> = {
  DEBUG: '#9e9e9e',
  INFO: '#2196f3',
  WARNING: '#ff9800',
  ERROR: '#f44336',
  CRITICAL: '#d32f2f',
};

export default function Logs() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filteredLogs, setFilteredLogs] = useState<LogEntry[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [levelFilter, setLevelFilter] = useState<string>('INFO');
  const [isPaused, setIsPaused] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  const wsRef = useRef<WebSocket | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const logsContainerRef = useRef<HTMLDivElement>(null);

  // WebSocket connection
  useEffect(() => {
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [levelFilter]);

  const connectWebSocket = () => {
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.hostname}:8000/ws/logs?level=${levelFilter}`;

      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
        console.log('WebSocket connected');
      };

      ws.onmessage = (event) => {
        if (isPaused) return;

        try {
          const data = JSON.parse(event.data);

          if (data.type === 'keepalive' || data.type === 'pong') {
            return;
          }

          if (data.type === 'clear') {
            setLogs([]);
            return;
          }

          // Add new log entry
          setLogs((prev) => {
            const newLogs = [...prev, data as LogEntry];
            // Keep only last 1000 logs
            if (newLogs.length > 1000) {
              return newLogs.slice(-1000);
            }
            return newLogs;
          });
        } catch (err) {
          console.error('Failed to parse log message:', err);
        }
      };

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        setError('WebSocket connection error');
        setIsConnected(false);
      };

      ws.onclose = () => {
        setIsConnected(false);
        console.log('WebSocket disconnected');

        // Attempt to reconnect after 5 seconds
        setTimeout(() => {
          if (!isPaused) {
            connectWebSocket();
          }
        }, 5000);
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('Failed to connect WebSocket:', err);
      setError('Failed to connect to log stream');
    }
  };

  // Filter logs based on search term
  useEffect(() => {
    if (!searchTerm) {
      setFilteredLogs(logs);
      return;
    }

    const filtered = logs.filter(
      (log) =>
        log.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.logger.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.module.toLowerCase().includes(searchTerm.toLowerCase())
    );
    setFilteredLogs(filtered);
  }, [logs, searchTerm]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [filteredLogs, autoScroll]);

  // Handle scroll to detect manual scrolling
  const handleScroll = () => {
    if (!logsContainerRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = logsContainerRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;

    setAutoScroll(isAtBottom);
  };

  const handlePauseToggle = () => {
    setIsPaused(!isPaused);
  };

  const handleClear = () => {
    setLogs([]);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ command: 'clear' }));
    }
  };

  const handleRefresh = () => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    setLogs([]);
    connectWebSocket();
  };

  const handleExport = async () => {
    try {
      const response = await fetch('/api/logs/export?format=txt&lines=1000', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) throw new Error('Export failed');

      const data = await response.json();
      const blob = new Blob([data.content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `logs-${new Date().toISOString()}.txt`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to export logs:', err);
      setError('Failed to export logs');
    }
  };

  const getLevelColor = (level: string) => {
    return LEVEL_COLORS[level] || '#9e9e9e';
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Real-time Logs
      </Typography>

      {error && (
        <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
          <TextField
            label="Search"
            variant="outlined"
            size="small"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            sx={{ minWidth: 300 }}
          />

          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Level</InputLabel>
            <Select
              value={levelFilter}
              label="Level"
              onChange={(e) => setLevelFilter(e.target.value)}
            >
              {LOG_LEVELS.map((level) => (
                <MenuItem key={level} value={level}>
                  {level}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Chip
            label={isConnected ? 'Connected' : 'Disconnected'}
            color={isConnected ? 'success' : 'error'}
            size="small"
          />

          <Box sx={{ flexGrow: 1 }} />

          <IconButton onClick={handlePauseToggle} color={isPaused ? 'primary' : 'default'}>
            {isPaused ? <PlayArrow /> : <Pause />}
          </IconButton>

          <IconButton onClick={handleClear}>
            <Clear />
          </IconButton>

          <IconButton onClick={handleRefresh}>
            <Refresh />
          </IconButton>

          <Button startIcon={<Download />} onClick={handleExport} variant="outlined">
            Export
          </Button>
        </Stack>
      </Paper>

      <Paper
        ref={logsContainerRef}
        onScroll={handleScroll}
        sx={{
          p: 2,
          height: 'calc(100vh - 300px)',
          overflow: 'auto',
          backgroundColor: '#1e1e1e',
          fontFamily: 'monospace',
          fontSize: '0.875rem',
        }}
      >
        {filteredLogs.length === 0 ? (
          <Typography color="text.secondary" sx={{ color: '#888' }}>
            No logs to display
          </Typography>
        ) : (
          filteredLogs.map((log, index) => (
            <Box
              key={index}
              sx={{
                mb: 0.5,
                p: 0.5,
                borderLeft: `3px solid ${getLevelColor(log.level)}`,
                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 0.1)',
                },
              }}
            >
              <Stack direction="row" spacing={1} alignItems="center">
                <Typography
                  component="span"
                  sx={{ color: '#888', minWidth: 180, fontSize: '0.75rem' }}
                >
                  {new Date(log.timestamp).toLocaleString()}
                </Typography>
                <Chip
                  label={log.level}
                  size="small"
                  sx={{
                    backgroundColor: getLevelColor(log.level),
                    color: '#fff',
                    fontWeight: 'bold',
                    minWidth: 80,
                  }}
                />
                <Typography component="span" sx={{ color: '#4fc3f7', fontSize: '0.75rem' }}>
                  {log.logger}
                </Typography>
                <Typography component="span" sx={{ color: '#fff', flex: 1 }}>
                  {log.message}
                </Typography>
                <Typography
                  component="span"
                  sx={{ color: '#888', fontSize: '0.7rem', minWidth: 150 }}
                >
                  {log.module}:{log.function}:{log.line}
                </Typography>
              </Stack>
            </Box>
          ))
        )}
        <div ref={logsEndRef} />
      </Paper>

      {!autoScroll && (
        <Button
          variant="contained"
          size="small"
          onClick={() => {
            setAutoScroll(true);
            logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
          }}
          sx={{
            position: 'fixed',
            bottom: 20,
            right: 20,
          }}
        >
          Scroll to Bottom
        </Button>
      )}
    </Box>
  );
}
