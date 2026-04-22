import { Routes, Route, Navigate } from 'react-router-dom';
import { Box } from '@mui/material';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import { AuthProvider } from './contexts/AuthContext';
import Dashboard from './pages/Dashboard';
import Repositories from './pages/Repositories';
import Reviews from './pages/Reviews';
import Prompts from './pages/Prompts';
import Config from './pages/Config';
import Logs from './pages/Logs';
import Backups from './pages/Backups';
import Login from './pages/Login';

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <Box sx={{ display: 'flex', minHeight: '100vh' }}>
                <Layout>
                  <Routes>
                    <Route path="/" element={<Navigate to="/dashboard" replace />} />
                    <Route path="/dashboard" element={<Dashboard />} />
                    <Route path="/repositories" element={<Repositories />} />
                    <Route path="/reviews" element={<Reviews />} />
                    <Route path="/prompts" element={<Prompts />} />
                    <Route path="/config" element={<Config />} />
                    <Route path="/logs" element={<Logs />} />
                    <Route path="/backups" element={<Backups />} />
                  </Routes>
                </Layout>
              </Box>
            </ProtectedRoute>
          }
        />
      </Routes>
    </AuthProvider>
  );
}

export default App;
