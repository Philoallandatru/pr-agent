import { Routes, Route, Navigate } from 'react-router-dom';
import { Box } from '@mui/material';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Repositories from './pages/Repositories';
import Reviews from './pages/Reviews';
import Prompts from './pages/Prompts';

function App() {
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/repositories" element={<Repositories />} />
          <Route path="/reviews" element={<Reviews />} />
          <Route path="/prompts" element={<Prompts />} />
        </Routes>
      </Layout>
    </Box>
  );
}

export default App;
