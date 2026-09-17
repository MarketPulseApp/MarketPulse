import React, { useState } from 'react';
import { Bell, UserCircle, Menu, Sun, Moon } from 'lucide-react';
import { AccountModal } from './AccountModal';
import { useTheme } from '../../ThemeContext';
import { useHealthCheck } from '../../api/useHealthCheck';

interface TopbarProps {
  onMenuClick?: () => void;
}

export const Topbar: React.FC<TopbarProps> = ({ onMenuClick }) => {
  const [isAccountModalOpen, setIsAccountModalOpen] = useState(false);
  const { isDark, toggleTheme } = useTheme();
  const { status } = useHealthCheck();

  return (
    <div className="h-16 bg-white dark:bg-gray-800 dark:border-gray-700 border-b flex items-center justify-between px-4 sm:px-6">
      <div className="flex items-center">
        {onMenuClick && (
          <button
            onClick={onMenuClick}
            className="mr-4 md:hidden p-2 text-gray-500 hover:text-gray-700 dark:text-gray-200 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <Menu size={24} />
          </button>
        )}
        <div className="text-lg font-semibold text-gray-800 dark:text-white hidden sm:block">
          Overview
        </div>
        <div className="hidden sm:flex items-center space-x-2 bg-gray-100 dark:bg-gray-700 px-3 py-1 rounded-full ml-4">
          <div className={`w-2 h-2 rounded-full ${status === 'healthy' ? 'bg-green-500' : status === 'degraded' ? 'bg-yellow-500' : 'bg-red-500'}`}></div>
          <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
            {status === 'healthy' ? 'System: Healthy' : status === 'degraded' ? 'System: Degraded' : 'System: Offline'}
          </span>
        </div>
      </div>
      <div className="flex items-center space-x-2 sm:space-x-4">
        <button
          onClick={toggleTheme}
          className="p-2 text-gray-400 dark:text-gray-300 hover:text-gray-600 dark:hover:text-white rounded-full hover:bg-gray-100 dark:hover:bg-gray-700"
        >
          {isDark ? <Sun size={20} /> : <Moon size={20} />}
        </button>
        <button className="p-2 text-gray-400 dark:text-gray-300 hover:text-gray-600 dark:hover:text-white rounded-full hover:bg-gray-100 dark:hover:bg-gray-700">
          <Bell size={20} />
        </button>

        <div className="relative">
          <button
            onClick={() => setIsAccountModalOpen(!isAccountModalOpen)}
            className="flex items-center space-x-2 focus:outline-none hover:opacity-80 transition-opacity"
          >
            <div className="w-8 h-8 bg-indigo-100 dark:bg-indigo-900 rounded-full flex items-center justify-center text-indigo-600 dark:text-indigo-300 font-bold">
              <UserCircle size={20} />
            </div>
            <span className="text-sm font-medium text-gray-700 dark:text-gray-200 hidden sm:block">Admin</span>
          </button>

          {isAccountModalOpen && (
            <AccountModal onClose={() => setIsAccountModalOpen(false)} />
          )}
        </div>
      </div>
    </div>
  );
};
