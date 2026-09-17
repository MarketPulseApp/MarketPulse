import { useState, useEffect } from 'react';
import apiClient from './client';

export type HealthStatus = 'healthy' | 'degraded' | 'offline';

export const useHealthCheck = (intervalMs = 10000) => {
  const [status, setStatus] = useState<HealthStatus>('healthy');

  useEffect(() => {
    let mounted = true;

    const checkHealth = async () => {
      try {
        const response = await apiClient.get('/health/full');
        if (mounted) {
          if (response.data && response.data.status === 'degraded') {
            setStatus('degraded');
          } else {
            setStatus('healthy');
          }
        }
      } catch (error) {
        if (mounted) {
          setStatus('offline');
        }
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, intervalMs);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [intervalMs]);

  return { status };
};
