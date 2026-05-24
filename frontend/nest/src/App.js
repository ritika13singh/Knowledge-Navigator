import React from 'react';
import { Routes, Route } from 'react-router-dom';
import AppLayout from './components/AppLayout';
import Chat from './components/Chat';
import LoginPage from './pages/LoginPage';
import Dashboard from './pages/Dashboard';
import PublicPortal from './pages/PublicPortal';
import ProtectedRoute from './components/ProtectedRoute';
import DriveMonitor from './pages/DriveMonitor';

function App() {
  return (
    <div className="App">
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<PublicPortal />} />
          <Route path="/staff" element={
            <ProtectedRoute>
              <Chat />
            </ProtectedRoute>
          } />
          <Route path="/dashboard" element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          } />
          <Route path="/drive-monitor" element={
            <ProtectedRoute>
              <DriveMonitor />
            </ProtectedRoute>
          } />
          <Route path="/login" element={<LoginPage />} />
        </Route>
      </Routes>
    </div>
  );
}

export default App;
