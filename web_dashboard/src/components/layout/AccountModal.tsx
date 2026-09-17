import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../../api/client';
import { LogOut } from 'lucide-react';

interface AccountModalProps {
  onClose: () => void;
}

export const AccountModal: React.FC<AccountModalProps> = ({ onClose }) => {
  const [email, setEmail] = useState<string>('Loading...');
  const navigate = useNavigate();

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const response = await apiClient.get('/auth/me');
        if (response.data && response.data.email) {
          setEmail(response.data.email);
        } else {
          setEmail('Unknown User');
        }
      } catch (error) {
        console.error('Failed to fetch user', error);
        setEmail('Error loading user');
      }
    };
    fetchUser();
  }, []);

  const handleSignOut = () => {
    localStorage.removeItem('token');
    navigate('/login');
    onClose();
  };

  return (
    <div className="absolute right-0 top-full mt-2 w-64 bg-white dark:bg-gray-800 rounded-md shadow-lg border border-gray-200 dark:border-gray-700 py-2 z-50">
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <p className="text-sm text-gray-500 dark:text-gray-400">Signed in as</p>
        <p className="text-sm font-medium text-gray-900 dark:text-white truncate" title={email}>
          {email}
        </p>
      </div>
      
      <div className="mt-2">
        <button
          onClick={handleSignOut}
          className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 dark:text-red-400 flex items-center space-x-2 transition-colors"
        >
          <LogOut size={16} />
          <span>Sign Out</span>
        </button>
      </div>
    </div>
  );
};
