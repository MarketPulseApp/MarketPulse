import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, TrendingUp, Settings, LogOut, X, Shield, Network, MessageCircle, Globe, Users, Calendar, Database, Brain } from 'lucide-react';

interface SidebarProps {
  onClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ onClose }) => {
  const handleLogout = () => {
    localStorage.removeItem('token');
    window.location.href = '/login';
  };

  return (
    <div className="w-full h-full flex flex-col bg-white dark:bg-gray-800 dark:border-gray-700 border-r">
      <div className="p-4 border-b flex justify-between items-center">
        <h1 className="text-xl font-bold text-indigo-600">MarketPulse</h1>
        {onClose && (
          <button onClick={onClose} className="md:hidden p-1 text-gray-500 hover:text-gray-700 rounded-md hover:bg-gray-100">
            <X size={24} />
          </button>
        )}
      </div>
      <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
        <NavLink
          to="/"
          onClick={onClose}
          className={({ isActive }) =>
            `flex items-center space-x-3 p-2 rounded-lg transition-colors ${
              isActive ? 'bg-indigo-50 text-indigo-700 dark:bg-blue-900 dark:text-white' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`
          }
        >
          <LayoutDashboard size={20} />
          <span>Dashboard</span>
        </NavLink>
        <NavLink
          to="/paper-trading"
          onClick={onClose}
          className={({ isActive }) =>
            `flex items-center space-x-3 p-2 rounded-lg transition-colors ${
              isActive ? 'bg-indigo-50 text-indigo-700 dark:bg-blue-900 dark:text-white' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`
          }
        >
          <TrendingUp size={20} />
          <span>Paper Trading</span>
        </NavLink>
        <NavLink
          to="/correlation"
          onClick={onClose}
          className={({ isActive }) =>
            `flex items-center space-x-3 p-2 rounded-lg transition-colors ${
              isActive ? 'bg-indigo-50 text-indigo-700 dark:bg-blue-900 dark:text-white' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`
          }
        >
          <Network size={20} />
          <span>Correlation Graph</span>
        </NavLink>
        <NavLink
          to="/sentiment"
          onClick={onClose}
          className={({ isActive }) =>
            `flex items-center space-x-3 p-2 rounded-lg transition-colors ${
              isActive ? 'bg-indigo-50 text-indigo-700 dark:bg-blue-900 dark:text-white' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`
          }
        >
          <MessageCircle size={20} />
          <span>Sentiment</span>
        </NavLink>
        <NavLink
          to="/macro"
          onClick={onClose}
          className={({ isActive }) =>
            `flex items-center space-x-3 p-2 rounded-lg transition-colors ${
              isActive ? 'bg-indigo-50 text-indigo-700 dark:bg-blue-900 dark:text-white' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`
          }
        >
          <Globe size={20} />
          <span>Macro Indicators</span>
        </NavLink>
        <NavLink
          to="/insider"
          onClick={onClose}
          className={({ isActive }) =>
            `flex items-center space-x-3 p-2 rounded-lg transition-colors ${
              isActive ? 'bg-indigo-50 text-indigo-700 dark:bg-blue-900 dark:text-white' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`
          }
        >
          <Users size={20} />
          <span>Insider Trading</span>
        </NavLink>
        <NavLink
          to="/earnings"
          onClick={onClose}
          className={({ isActive }) =>
            `flex items-center space-x-3 p-2 rounded-lg transition-colors ${
              isActive ? 'bg-indigo-50 text-indigo-700 dark:bg-blue-900 dark:text-white' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`
          }
        >
          <Calendar size={20} />
          <span>Earnings Calendar</span>
        </NavLink>
        <NavLink
          to="/raw-data"
          onClick={onClose}
          className={({ isActive }) =>
            `flex items-center space-x-3 p-2 rounded-lg transition-colors ${
              isActive ? 'bg-indigo-50 text-indigo-700 dark:bg-blue-900 dark:text-white' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`
          }
        >
          <Database size={20} />
          <span>Raw Ingestion Feed</span>
        </NavLink>
        <NavLink
          to="/training"
          onClick={onClose}
          className={({ isActive }) =>
            `flex items-center space-x-3 p-2 rounded-lg transition-colors ${
              isActive ? 'bg-indigo-50 text-indigo-700 dark:bg-blue-900 dark:text-white' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`
          }
        >
          <Brain size={20} />
          <span>Training</span>
        </NavLink>
        <NavLink
          to="/settings"
          onClick={onClose}
          className={({ isActive }) =>
            `flex items-center space-x-3 p-2 rounded-lg transition-colors ${
              isActive ? 'bg-indigo-50 text-indigo-700 dark:bg-blue-900 dark:text-white' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`
          }
        >
          <Settings size={20} />
          <span>Settings</span>
        </NavLink>
        <NavLink
          to="/admin"
          onClick={onClose}
          className={({ isActive }) =>
            `flex items-center space-x-3 p-2 rounded-lg transition-colors ${
              isActive ? 'bg-indigo-50 text-indigo-700 dark:bg-blue-900 dark:text-white' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`
          }
        >
          <Shield size={20} />
          <span>Admin Console</span>
        </NavLink>
      </nav>
      <div className="p-4 border-t">
        <button
          onClick={handleLogout}
          className="flex items-center space-x-3 p-2 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg w-full transition-colors"
        >
          <LogOut size={20} />
          <span>Logout</span>
        </button>
      </div>
    </div>
  );
};
