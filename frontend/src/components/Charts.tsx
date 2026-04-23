import React from 'react';
import { Line, Bar, Pie, Doughnut, Radar } from 'react-chartjs-2';
import { Box, Paper, Typography, useTheme } from '@mui/material';

interface ChartProps {
  title?: string;
  data: any;
  options?: any;
  height?: number;
}

// Line Chart Component
export const LineChart: React.FC<ChartProps> = ({ title, data, options, height = 300 }) => {
  const theme = useTheme();

  const defaultOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'top' as const,
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        grid: {
          color: theme.palette.divider,
        },
      },
      x: {
        grid: {
          color: theme.palette.divider,
        },
      },
    },
    ...options,
  };

  return (
    <Paper sx={{ p: 3 }}>
      {title && (
        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>
      )}
      <Box height={height}>
        <Line data={data} options={defaultOptions} />
      </Box>
    </Paper>
  );
};

// Bar Chart Component
export const BarChart: React.FC<ChartProps> = ({ title, data, options, height = 300 }) => {
  const theme = useTheme();

  const defaultOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'top' as const,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        grid: {
          color: theme.palette.divider,
        },
      },
      x: {
        grid: {
          display: false,
        },
      },
    },
    ...options,
  };

  return (
    <Paper sx={{ p: 3 }}>
      {title && (
        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>
      )}
      <Box height={height}>
        <Bar data={data} options={defaultOptions} />
      </Box>
    </Paper>
  );
};

// Pie Chart Component
export const PieChart: React.FC<ChartProps> = ({ title, data, options, height = 300 }) => {
  const defaultOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'bottom' as const,
      },
    },
    ...options,
  };

  return (
    <Paper sx={{ p: 3 }}>
      {title && (
        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>
      )}
      <Box height={height}>
        <Pie data={data} options={defaultOptions} />
      </Box>
    </Paper>
  );
};

// Doughnut Chart Component
export const DoughnutChart: React.FC<ChartProps> = ({ title, data, options, height = 300 }) => {
  const defaultOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'bottom' as const,
      },
    },
    ...options,
  };

  return (
    <Paper sx={{ p: 3 }}>
      {title && (
        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>
      )}
      <Box height={height}>
        <Doughnut data={data} options={defaultOptions} />
      </Box>
    </Paper>
  );
};

// Radar Chart Component
export const RadarChart: React.FC<ChartProps> = ({ title, data, options, height = 300 }) => {
  const theme = useTheme();

  const defaultOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'top' as const,
      },
    },
    scales: {
      r: {
        beginAtZero: true,
        grid: {
          color: theme.palette.divider,
        },
      },
    },
    ...options,
  };

  return (
    <Paper sx={{ p: 3 }}>
      {title && (
        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>
      )}
      <Box height={height}>
        <Radar data={data} options={defaultOptions} />
      </Box>
    </Paper>
  );
};

// Utility function to generate chart colors
export const generateChartColors = (count: number, opacity: number = 0.8): string[] => {
  const colors = [
    `rgba(75, 192, 192, ${opacity})`,
    `rgba(255, 99, 132, ${opacity})`,
    `rgba(54, 162, 235, ${opacity})`,
    `rgba(255, 206, 86, ${opacity})`,
    `rgba(153, 102, 255, ${opacity})`,
    `rgba(255, 159, 64, ${opacity})`,
    `rgba(199, 199, 199, ${opacity})`,
    `rgba(83, 102, 255, ${opacity})`,
    `rgba(255, 99, 255, ${opacity})`,
    `rgba(99, 255, 132, ${opacity})`,
  ];

  const result: string[] = [];
  for (let i = 0; i < count; i++) {
    result.push(colors[i % colors.length]);
  }
  return result;
};

// Utility function to format trend data
export const formatTrendData = (
  data: any[],
  label: string,
  color: string = 'rgb(75, 192, 192)'
) => {
  return {
    labels: data.map((item) => item.date || item.label || item.x),
    datasets: [
      {
        label,
        data: data.map((item) => item.value || item.count || item.y),
        borderColor: color,
        backgroundColor: color.replace('rgb', 'rgba').replace(')', ', 0.2)'),
        fill: true,
        tension: 0.4,
      },
    ],
  };
};

// Utility function to format multi-series data
export const formatMultiSeriesData = (
  labels: string[],
  series: { label: string; data: number[]; color?: string }[]
) => {
  return {
    labels,
    datasets: series.map((s, index) => ({
      label: s.label,
      data: s.data,
      borderColor: s.color || generateChartColors(1, 1)[0],
      backgroundColor: s.color
        ? s.color.replace('rgb', 'rgba').replace(')', ', 0.2)')
        : generateChartColors(1, 0.2)[0],
      fill: true,
      tension: 0.4,
    })),
  };
};

// Utility function to format distribution data
export const formatDistributionData = (data: { label: string; value: number }[]) => {
  return {
    labels: data.map((item) => item.label),
    datasets: [
      {
        data: data.map((item) => item.value),
        backgroundColor: generateChartColors(data.length, 0.8),
        borderWidth: 1,
      },
    ],
  };
};

export default {
  LineChart,
  BarChart,
  PieChart,
  DoughnutChart,
  RadarChart,
  generateChartColors,
  formatTrendData,
  formatMultiSeriesData,
  formatDistributionData,
};
