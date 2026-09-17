import axios from 'axios';

// Get the backend URL from env or fallback to the provided internal IP
const baseURL = import.meta.env.VITE_API_URL || '/api';

export const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  console.log('[API Request]', { baseURL: config.baseURL, url: config.url, headers: config.headers });
  if (config.url && config.url.startsWith('/api/')) {
    config.url = config.url.replace('/api/', '/');
  } else if (config.url && config.url === '/api') {
    config.url = '/';
  }

  const token = localStorage.getItem('token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[API Error]', {
      status: error.response?.status,
      data: error.response?.data,
      url: error.config?.url
    });
    return Promise.reject(error);
  }
);

export default apiClient;
