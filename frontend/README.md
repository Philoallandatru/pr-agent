# PR Agent Web Platform - Frontend

React + TypeScript + Vite 前端应用

## 技术栈

- React 18
- TypeScript
- Vite
- Material-UI (MUI)
- React Router
- Recharts (图表)
- Axios (HTTP 客户端)

## 开发

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:5173

### 构建生产版本

```bash
npm run build
```

### 预览生产构建

```bash
npm run preview
```

## 项目结构

```
frontend/
├── src/
│   ├── api/           # API 客户端
│   ├── components/    # 可复用组件
│   ├── pages/         # 页面组件
│   ├── types/         # TypeScript 类型定义
│   ├── App.tsx        # 主应用组件
│   └── main.tsx       # 入口文件
├── public/            # 静态资源
└── index.html         # HTML 模板
```

## 功能页面

1. **Dashboard** - 系统概览和统计
2. **Repositories** - 仓库管理
3. **Review History** - PR 审查历史
4. **Prompt Editor** - Prompt 模板编辑

## API 配置

默认连接到 `http://localhost:8000`，可通过环境变量修改:

```bash
VITE_API_BASE_URL=http://your-api-server:8000
```

## 代理配置

开发环境下，Vite 会将 `/api` 请求代理到后端服务器（见 `vite.config.ts`）
