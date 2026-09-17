import { useState, useEffect } from 'react';
import apiClient from '../api/client';

interface Quota {
  source_name: string;
  daily_used: number;
  monthly_used: number;
  is_unlimited: boolean;
  daily_limit: number | null;
  monthly_limit: number | null;
  api_key_masked: string | null;
}

export const Quotas = () => {
  const [quotas, setQuotas] = useState<Quota[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const [editingSource, setEditingSource] = useState<string | null>(null);
  const [editDailyLimit, setEditDailyLimit] = useState<string>("");
  const [editMonthlyLimit, setEditMonthlyLimit] = useState<string>("");
  const [editApiKey, setEditApiKey] = useState<string>("");

  const [isAdding, setIsAdding] = useState(false);
  const [newSource, setNewSource] = useState("");
  const [newDaily, setNewDaily] = useState("");
  const [newMonthly, setNewMonthly] = useState("");
  const [newApiKey, setNewApiKey] = useState("");

  useEffect(() => {
    fetchQuotas();
  }, []);

  const fetchQuotas = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.get('/api/v1/quotas');
      if (response.data && Array.isArray(response.data)) {
        setQuotas(response.data);
      } else {
        console.error('Invalid response data:', response.data);
      }
    } catch (error) {
      console.error('Failed to fetch quotas:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const startEditing = (q: Quota) => {
    setEditingSource(q.source_name);
    setEditDailyLimit(q.daily_limit ? q.daily_limit.toString() : "");
    setEditMonthlyLimit(q.monthly_limit ? q.monthly_limit.toString() : "");
    setEditApiKey(q.api_key_masked || "");
  };

  const saveEditing = async (source_name: string) => {
    try {
      const payload = {
        daily_limit: editDailyLimit ? parseInt(editDailyLimit) : null,
        monthly_limit: editMonthlyLimit ? parseInt(editMonthlyLimit) : null,
        api_key: editApiKey
      };
      await apiClient.put(`/api/v1/quotas/${source_name}`, payload);
      setEditingSource(null);
      await fetchQuotas();
    } catch (error) {
      console.error('Failed to update quota:', error);
    }
  };

  const saveNewSource = async () => {
    try {
      const payload = {
        source_name: newSource.toLowerCase().trim(),
        daily_limit: newDaily ? parseInt(newDaily) : null,
        monthly_limit: newMonthly ? parseInt(newMonthly) : null,
        api_key: newApiKey
      };
      if (!payload.source_name) return;
      await apiClient.post(`/api/v1/quotas`, payload);
      setIsAdding(false);
      setNewSource("");
      setNewDaily("");
      setNewMonthly("");
      setNewApiKey("");
      await fetchQuotas();
    } catch (error) {
      console.error('Failed to create quota:', error);
    }
  };

  const calcPercentage = (used: number, limit: number | null) => {
    if (!limit) return 0;
    const p = (used / limit) * 100;
    return p > 100 ? 100 : p;
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">API Setup & Quotas</h1>
          <p className="text-sm text-gray-500">Manage API keys and rate limits for external data sources. Keys sync instantly to Valkey for the ingestion worker.</p>
        </div>
        <button onClick={() => setIsAdding(!isAdding)} className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700">
          {isAdding ? 'Cancel' : '+ Add Source'}
        </button>
      </div>

      {isAdding && (
        <div className="bg-indigo-50 dark:bg-indigo-900/20 rounded-lg p-6 mb-6 border border-indigo-100 dark:border-indigo-800">
          <h2 className="text-lg font-semibold mb-4 text-indigo-900 dark:text-indigo-100">Add New Data Source</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">Source Name</label>
              <input type="text" value={newSource} onChange={e => setNewSource(e.target.value)} className="mt-1 block w-full text-sm border-gray-300 rounded-md shadow-sm dark:bg-gray-700 dark:border-gray-600" placeholder="e.g. finnhub" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">API Key</label>
              <input type="text" value={newApiKey} onChange={e => setNewApiKey(e.target.value)} className="mt-1 block w-full text-sm border-gray-300 rounded-md shadow-sm dark:bg-gray-700 dark:border-gray-600" placeholder="Secret Key" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">Daily Limit</label>
              <input type="number" value={newDaily} onChange={e => setNewDaily(e.target.value)} className="mt-1 block w-full text-sm border-gray-300 rounded-md shadow-sm dark:bg-gray-700 dark:border-gray-600" placeholder="Empty = Unlimited" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">Monthly Limit</label>
              <input type="number" value={newMonthly} onChange={e => setNewMonthly(e.target.value)} className="mt-1 block w-full text-sm border-gray-300 rounded-md shadow-sm dark:bg-gray-700 dark:border-gray-600" placeholder="Empty = Unlimited" />
            </div>
          </div>
          <button onClick={saveNewSource} className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 text-sm font-medium">Save Source</button>
        </div>
      )}

      {isLoading ? (
        <div className="text-sm text-gray-500">Loading...</div>
      ) : (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {quotas.map(q => (
            <div key={q.source_name} className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border border-gray-200 dark:border-gray-700">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-semibold uppercase">{q.source_name}</h2>
                {editingSource !== q.source_name ? (
                  <button onClick={() => startEditing(q)} className="text-sm text-blue-600 hover:text-blue-800">Edit</button>
                ) : (
                  <div className="space-x-2">
                    <button onClick={() => saveEditing(q.source_name)} className="text-sm text-green-600 hover:text-green-800 font-bold">Save</button>
                    <button onClick={() => setEditingSource(null)} className="text-sm text-gray-500 hover:text-gray-700">Cancel</button>
                  </div>
                )}
              </div>

              {editingSource === q.source_name ? (
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">API Key</label>
                    <input type="text" value={editApiKey} onChange={e => setEditApiKey(e.target.value)} className="mt-1 block w-full text-sm border-gray-300 rounded-md shadow-sm dark:bg-gray-700 dark:border-gray-600" placeholder="Enter new key" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">Daily Limit</label>
                    <input type="number" value={editDailyLimit} onChange={e => setEditDailyLimit(e.target.value)} className="mt-1 block w-full text-sm border-gray-300 rounded-md shadow-sm dark:bg-gray-700 dark:border-gray-600" placeholder="Empty = Unlimited" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">Monthly Limit</label>
                    <input type="number" value={editMonthlyLimit} onChange={e => setEditMonthlyLimit(e.target.value)} className="mt-1 block w-full text-sm border-gray-300 rounded-md shadow-sm dark:bg-gray-700 dark:border-gray-600" placeholder="Empty = Unlimited" />
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div>
                    <div className="text-xs text-gray-500 mb-1">API Key</div>
                    <div className="text-sm font-mono bg-gray-100 dark:bg-gray-900 p-2 rounded">{q.api_key_masked || "Not set"}</div>
                  </div>

                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span>Daily Usage: {q.daily_used} / {q.daily_limit || "Unlimited"}</span>
                      <span>{q.daily_limit ? calcPercentage(q.daily_used, q.daily_limit).toFixed(1) + "%" : ""}</span>
                    </div>
                    {q.daily_limit && (
                      <div className="w-full bg-gray-200 rounded-full h-2 dark:bg-gray-700">
                        <div className="bg-blue-600 h-2 rounded-full" style={{ width: `${calcPercentage(q.daily_used, q.daily_limit)}%` }}></div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
