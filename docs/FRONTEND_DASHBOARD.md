# Frontend Dashboard System

代码审查分析仪表板前端系统，提供实时数据可视化和交互式分析功能。

## 技术栈

- **React 18** - UI 框架
- **TypeScript** - 类型安全
- **Material-UI (MUI)** - UI 组件库
- **Chart.js** - 图表库
- **React Router** - 路由管理
- **Axios** - HTTP 客户端
- **Vite** - 构建工具
- **Vitest** - 单元测试

## 项目结构

```
frontend/
├── src/
│   ├── pages/
│   │   └── Dashboard.tsx          # 仪表板主页
│   ├── components/
│   │   ├── Charts.tsx             # 图表组件库
│   │   ├── Layout.tsx             # 响应式布局
│   │   └── ProtectedRoute.tsx    # 路由保护
│   ├── api/
│   │   └── client.ts              # API 客户端
│   ├── contexts/
│   │   └── AuthContext.tsx        # 认证上下文
│   ├── __tests__/
│   │   ├── Dashboard.test.tsx     # 仪表板测试
│   │   └── Charts.test.tsx        # 图表测试
│   ├── App.tsx                    # 应用入口
│   └── main.tsx                   # 主入口
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## 功能特性

### 1. 实时数据展示

仪表板实时显示代码审查关键指标：

- 总审查数量
- 已完成审查
- 待处理审查
- 平均审查时间
- 平均评论数
- 质量评分

### 2. 交互式图表

支持多种图表类型：

- **折线图** - 审查趋势、质量趋势
- **柱状图** - 审查者排名、团队对比
- **饼图/环形图** - 审查状态分布
- **雷达图** - 多维度质量分析

### 3. 时间范围过滤

支持多种时间范围：
- 最近 24 小时
- 最近 7 天
- 最近 30 天
- 最近 90 天

### 4. 响应式设计

- 桌面端：侧边栏导航 + 主内容区
- 移动端：抽屉式导航 + 全屏内容
- 自适应布局，支持各种屏幕尺寸

## 快速开始

### 安装依赖

```bash
cd frontend
npm install
```

### 开发模式

```bash
npm run dev
```

访问 http://localhost:5173

### 生产构建

```bash
npm run build
```

构建产物在 `dist/` 目录

### 运行测试

```bash
# 运行所有测试
npm test

# 测试 UI
npm run test:ui

# 测试覆盖率
npm run test:coverage
```

## 组件使用

### Dashboard 组件

```tsx
import Dashboard from './pages/Dashboard';

function App() {
  return <Dashboard />;
}
```

### 图表组件

```tsx
import { LineChart, BarChart, PieChart } from './components/Charts';

// 折线图
<LineChart
  title="Review Trends"
  data={{
    labels: ['Jan', 'Feb', 'Mar'],
    datasets: [{
      label: 'Reviews',
      data: [10, 20, 15],
      borderColor: 'rgb(75, 192, 192)',
    }]
  }}
  height={300}
/>

// 柱状图
<BarChart
  title="Top Reviewers"
  data={{
    labels: ['Alice', 'Bob'],
    datasets: [{
      label: 'Reviews',
      data: [45, 38],
    }]
  }}
/>

// 饼图
<PieChart
  title="Status Distribution"
  data={{
    labels: ['Completed', 'Pending'],
    datasets: [{
      data: [120, 30],
      backgroundColor: ['#4caf50', '#ff9800'],
    }]
  }}
/>
```

### API 客户端

```tsx
import { apiClient, dashboardApi } from './api/client';

// 直接使用 API 客户端
const response = await apiClient.get('/api/dashboards/main/stats');

// 使用封装的 API 方法
const stats = await dashboardApi.getStats('main', '7d');
const trends = await dashboardApi.getTrends('main', 'reviews', '30d');
```

## API 集成

### 仪表板 API

```typescript
// 获取统计数据
GET /api/dashboards/{dashboard_id}/stats?time_range=7d

// 获取趋势数据
GET /api/dashboards/{dashboard_id}/trends?metric=reviews&time_range=30d

// 获取分布数据
GET /api/dashboards/{dashboard_id}/distribution

// 获取 Top 审查者
GET /api/dashboards/{dashboard_id}/top-reviewers?limit=5
```

### 响应格式

```json
{
  "total_reviews": 150,
  "completed_reviews": 120,
  "pending_reviews": 30,
  "average_review_time": 2.5,
  "average_comments": 8.3,
  "quality_score": 87.5
}
```

## 图表工具函数

### generateChartColors

生成图表颜色数组：

```typescript
import { generateChartColors } from './components/Charts';

const colors = generateChartColors(5, 0.8);
// ['rgba(75, 192, 192, 0.8)', 'rgba(255, 99, 132, 0.8)', ...]
```

### formatTrendData

格式化趋势数据：

```typescript
import { formatTrendData } from './components/Charts';

const data = [
  { date: '2024-01-01', value: 10 },
  { date: '2024-01-02', value: 20 },
];

const chartData = formatTrendData(data, 'Reviews', 'rgb(75, 192, 192)');
```

### formatDistributionData

格式化分布数据：

```typescript
import { formatDistributionData } from './components/Charts';

const data = [
  { label: 'Completed', value: 120 },
  { label: 'Pending', value: 30 },
];

const chartData = formatDistributionData(data);
```

## 环境变量

创建 `.env` 文件：

```env
# API 基础 URL
REACT_APP_API_BASE_URL=http://localhost:8000

# 其他配置
REACT_APP_ENABLE_ANALYTICS=true
```

## 主题定制

Material-UI 主题可以在 `App.tsx` 中定制：

```tsx
import { createTheme, ThemeProvider } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
  typography: {
    fontFamily: 'Roboto, Arial, sans-serif',
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      {/* Your app */}
    </ThemeProvider>
  );
}
```

## 性能优化

### 1. 代码分割

```tsx
import { lazy, Suspense } from 'react';

const Dashboard = lazy(() => import('./pages/Dashboard'));

function App() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <Dashboard />
    </Suspense>
  );
}
```

### 2. 数据缓存

```tsx
import { useEffect, useState } from 'react';

function useCachedData(key: string, fetcher: () => Promise<any>) {
  const [data, setData] = useState(() => {
    const cached = localStorage.getItem(key);
    return cached ? JSON.parse(cached) : null;
  });

  useEffect(() => {
    fetcher().then((result) => {
      setData(result);
      localStorage.setItem(key, JSON.stringify(result));
    });
  }, [key]);

  return data;
}
```

### 3. 图表优化

```tsx
// 使用 useMemo 缓存图表数据
import { useMemo } from 'react';

const chartData = useMemo(() => {
  return formatTrendData(rawData, 'Reviews');
}, [rawData]);
```

## 测试

### 单元测试示例

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import Dashboard from './pages/Dashboard';

test('renders dashboard with data', async () => {
  render(<Dashboard />);
  
  await waitFor(() => {
    expect(screen.getByText('Code Review Dashboard')).toBeInTheDocument();
  });
  
  expect(screen.getByText('Total Reviews')).toBeInTheDocument();
});
```

### Mock API 调用

```tsx
import { apiClient } from './api/client';

jest.mock('./api/client');

const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;

mockApiClient.get.mockResolvedValue({
  data: { total_reviews: 150 }
});
```

## 部署

### Docker 部署

```dockerfile
FROM node:18-alpine as build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Nginx 配置

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 故障排查

### 常见问题

1. **API 连接失败**
   - 检查 `REACT_APP_API_BASE_URL` 配置
   - 确认后端服务运行正常
   - 检查 CORS 配置

2. **图表不显示**
   - 确认 Chart.js 已正确安装
   - 检查数据格式是否正确
   - 查看浏览器控制台错误

3. **路由不工作**
   - 确认使用 BrowserRouter
   - 检查路由配置
   - Nginx 配置 try_files

## 最佳实践

1. **组件设计**
   - 保持组件小而专注
   - 使用 TypeScript 类型
   - 提取可复用逻辑到自定义 Hooks

2. **状态管理**
   - 使用 Context API 管理全局状态
   - 本地状态优先使用 useState
   - 复杂状态使用 useReducer

3. **性能**
   - 使用 React.memo 避免不必要的重渲染
   - 使用 useMemo 和 useCallback 优化计算
   - 实现虚拟滚动处理大列表

4. **可访问性**
   - 使用语义化 HTML
   - 添加 ARIA 标签
   - 支持键盘导航

## 相关文档

- [Dashboard API](../DASHBOARD.md)
- [Metrics Collection](../METRICS_COLLECTION.md)
- [Reports Generation](../REPORT_GENERATION.md)
- [AI Assistant](../AI_ASSISTANT.md)
