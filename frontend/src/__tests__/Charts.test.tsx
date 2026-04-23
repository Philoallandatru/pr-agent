import { render, screen } from '@testing-library/react';
import {
  LineChart,
  BarChart,
  PieChart,
  DoughnutChart,
  generateChartColors,
  formatTrendData,
  formatDistributionData,
} from '../components/Charts';

const mockLineData = {
  labels: ['Jan', 'Feb', 'Mar'],
  datasets: [
    {
      label: 'Reviews',
      data: [10, 20, 15],
      borderColor: 'rgb(75, 192, 192)',
      backgroundColor: 'rgba(75, 192, 192, 0.2)',
    },
  ],
};

const mockBarData = {
  labels: ['Alice', 'Bob', 'Charlie'],
  datasets: [
    {
      label: 'Reviews',
      data: [45, 38, 37],
      backgroundColor: 'rgba(54, 162, 235, 0.8)',
    },
  ],
};

const mockPieData = {
  labels: ['Completed', 'Pending', 'Failed'],
  datasets: [
    {
      data: [120, 30, 5],
      backgroundColor: [
        'rgba(75, 192, 192, 0.8)',
        'rgba(255, 206, 86, 0.8)',
        'rgba(255, 99, 132, 0.8)',
      ],
    },
  ],
};

describe('Chart Components', () => {
  describe('LineChart', () => {
    it('renders line chart with title', () => {
      render(<LineChart title="Review Trends" data={mockLineData} />);
      expect(screen.getByText('Review Trends')).toBeInTheDocument();
    });

    it('renders line chart without title', () => {
      render(<LineChart data={mockLineData} />);
      expect(screen.queryByRole('heading')).not.toBeInTheDocument();
    });
  });

  describe('BarChart', () => {
    it('renders bar chart with title', () => {
      render(<BarChart title="Top Reviewers" data={mockBarData} />);
      expect(screen.getByText('Top Reviewers')).toBeInTheDocument();
    });

    it('renders bar chart without title', () => {
      render(<BarChart data={mockBarData} />);
      expect(screen.queryByRole('heading')).not.toBeInTheDocument();
    });
  });

  describe('PieChart', () => {
    it('renders pie chart with title', () => {
      render(<PieChart title="Review Status" data={mockPieData} />);
      expect(screen.getByText('Review Status')).toBeInTheDocument();
    });
  });

  describe('DoughnutChart', () => {
    it('renders doughnut chart with title', () => {
      render(<DoughnutChart title="Distribution" data={mockPieData} />);
      expect(screen.getByText('Distribution')).toBeInTheDocument();
    });
  });
});

describe('Chart Utilities', () => {
  describe('generateChartColors', () => {
    it('generates correct number of colors', () => {
      const colors = generateChartColors(5);
      expect(colors).toHaveLength(5);
    });

    it('generates colors with correct opacity', () => {
      const colors = generateChartColors(3, 0.5);
      colors.forEach((color) => {
        expect(color).toContain('0.5');
      });
    });

    it('cycles through colors when count exceeds palette', () => {
      const colors = generateChartColors(15);
      expect(colors).toHaveLength(15);
    });
  });

  describe('formatTrendData', () => {
    it('formats trend data correctly', () => {
      const data = [
        { date: '2024-01-01', value: 10 },
        { date: '2024-01-02', value: 20 },
      ];
      const result = formatTrendData(data, 'Reviews');

      expect(result.labels).toEqual(['2024-01-01', '2024-01-02']);
      expect(result.datasets[0].label).toBe('Reviews');
      expect(result.datasets[0].data).toEqual([10, 20]);
    });

    it('handles alternative field names', () => {
      const data = [
        { label: 'Jan', count: 10 },
        { label: 'Feb', count: 20 },
      ];
      const result = formatTrendData(data, 'Reviews');

      expect(result.labels).toEqual(['Jan', 'Feb']);
      expect(result.datasets[0].data).toEqual([10, 20]);
    });
  });

  describe('formatDistributionData', () => {
    it('formats distribution data correctly', () => {
      const data = [
        { label: 'Completed', value: 120 },
        { label: 'Pending', value: 30 },
      ];
      const result = formatDistributionData(data);

      expect(result.labels).toEqual(['Completed', 'Pending']);
      expect(result.datasets[0].data).toEqual([120, 30]);
      expect(result.datasets[0].backgroundColor).toHaveLength(2);
    });
  });
});
