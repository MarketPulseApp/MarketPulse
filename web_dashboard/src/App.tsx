import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { Dashboard } from './pages/Dashboard';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { PaperTrading } from './pages/PaperTrading';
import { Settings } from './pages/Settings';
import { CorrelationGraph } from './pages/CorrelationGraph';
import { SentimentDashboard } from './pages/SentimentDashboard';
import { MacroIndicators } from './pages/MacroIndicators';
import { InsiderTrading } from './pages/InsiderTrading';
import { EarningsCalendar } from './pages/EarningsCalendar';
import { AdminConsole } from './pages/AdminConsole';
import { Why } from './pages/Why';
import { Analytics } from './pages/Analytics';
import { RawData } from './pages/RawData';
import { Training } from './pages/Training';
import { Quotas } from './pages/Quotas';

const PrivateRoute = ({ children }: { children: React.ReactNode }) => {
  const isAuthenticated = !!localStorage.getItem('token');
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
};

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        <Route
          path="/"
          element={
            <PrivateRoute>
              <Layout />
            </PrivateRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="paper-trading" element={<PaperTrading />} />
          <Route path="settings" element={<Settings />} />
          <Route path="admin" element={<AdminConsole />} />
          <Route path="why" element={<Why />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="visualizations" element={<CorrelationGraph />} />
          <Route path="sentiment" element={<SentimentDashboard />} />
          <Route path="macro" element={<MacroIndicators />} />
          <Route path="insider" element={<InsiderTrading />} />
          <Route path="earnings" element={<EarningsCalendar />} />
          <Route path="raw-data" element={<RawData />} />
          <Route path="training" element={<Training />} />
          <Route path="quotas" element={<Quotas />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
