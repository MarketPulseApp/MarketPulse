import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Terminal, RefreshCw, AlertCircle } from 'lucide-react';

interface RawDataEntry {
  id?: string | number;
  source?: string;
  timestamp?: string;
  type?: string;
  payload?: any;
  [key: string]: any;
}

export const RawData: React.FC = () => {
  const [data, setData] = useState<RawDataEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const endOfListRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const fetchData = async () => {
    try {
      const response = await axios.get('/api/api/v1/data-stream/raw', {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      });
      
      let incomingData: RawDataEntry[] = [];
      if (Array.isArray(response.data)) {
        incomingData = response.data;
      } else if (response.data && Array.isArray(response.data.data)) {
        incomingData = response.data.data;
      } else if (response.data) {
        incomingData = [response.data];
      }

      setData(prev => {
        // Keep last 100 items for memory safety if polling
        const combined = [...prev, ...incomingData];
        // Ensure uniqueness if id is present, though for raw stream maybe not needed
        // Just slice to 100 for now
        return combined.slice(-100);
      });
      
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.message || err.message || 'Failed to fetch raw data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    
    let interval: ReturnType<typeof setInterval>;
    if (autoRefresh) {
      interval = setInterval(() => {
        fetchData();
      }, 3000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  useEffect(() => {
    if (autoRefresh && endOfListRef.current && containerRef.current) {
      // scroll to bottom smoothly
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [data, autoRefresh]);

  return (
    <div className="p-6 space-y-6 h-[calc(100vh-5rem)] flex flex-col bg-gray-950">
      <div className="flex justify-between items-center bg-black p-4 rounded-lg border border-green-900 shadow-[0_0_15px_rgba(0,255,0,0.15)]">
        <div className="flex items-center space-x-3 text-green-500">
          <Terminal size={24} />
          <h1 className="text-2xl font-bold font-mono tracking-wider text-green-500 shadow-green-500 drop-shadow-md">RAW_INGESTION_FIREHOSE</h1>
        </div>
        <div className="flex items-center space-x-4">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center space-x-2 px-4 py-2 rounded font-mono text-sm transition-all duration-300 ${
              autoRefresh 
                ? 'bg-green-900/40 text-green-400 border border-green-500 shadow-[0_0_10px_rgba(0,255,0,0.2)]' 
                : 'bg-gray-900 text-gray-500 border border-gray-700'
            }`}
          >
            <RefreshCw size={16} className={autoRefresh ? 'animate-[spin_3s_linear_infinite]' : ''} />
            <span>{autoRefresh ? 'AUTO-SYNC: ON' : 'AUTO-SYNC: OFF'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-950/50 border border-red-900 p-4 rounded-lg flex items-center space-x-3 text-red-500 font-mono shadow-[0_0_10px_rgba(255,0,0,0.1)]">
          <AlertCircle size={20} />
          <span>ERR_CONNECTION: {error}</span>
        </div>
      )}

      <div className="flex-1 bg-black rounded-lg border border-green-900/50 overflow-hidden shadow-inner flex flex-col font-mono text-sm relative">
        <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(0,255,0,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(0,255,0,0.03)_1px,transparent_1px)] bg-[size:20px_20px]"></div>
        
        <div className="grid grid-cols-12 gap-4 p-4 border-b border-green-900/50 text-green-700 uppercase font-bold sticky top-0 bg-black/95 backdrop-blur z-10">
          <div className="col-span-2">Timestamp</div>
          <div className="col-span-2">Source</div>
          <div className="col-span-2">Type</div>
          <div className="col-span-6">Payload</div>
        </div>
        
        <div ref={containerRef} className="flex-1 overflow-y-auto p-4 space-y-1 relative z-0 scroll-smooth custom-scrollbar">
          {loading && data.length === 0 ? (
            <div className="text-green-500/50 flex flex-col items-center justify-center h-full space-y-4">
              <RefreshCw size={32} className="animate-[spin_2s_linear_infinite]" />
              <p className="animate-pulse">INITIALIZING_SECURE_STREAM...</p>
            </div>
          ) : data.length === 0 ? (
            <div className="text-green-500/30 text-center py-10">
              [ AWAITING_DATA_STREAM ]
            </div>
          ) : (
            data.map((item, index) => {
              const displayTime = item.timestamp ? new Date(item.timestamp).toISOString() : new Date().toISOString();
              return (
                <div 
                  key={index} 
                  className="grid grid-cols-12 gap-4 py-2 border-b border-green-900/20 text-green-400 hover:bg-green-900/20 transition-colors"
                >
                  <div className="col-span-2 whitespace-nowrap opacity-70">
                    {displayTime}
                  </div>
                  <div className="col-span-2 text-green-300 font-bold">
                    [{item.source || 'UNKNOWN_SRC'}]
                  </div>
                  <div className="col-span-2 text-yellow-500/80">
                    {item.type || 'RAW_PACKET'}
                  </div>
                  <div className="col-span-6">
                    <pre className="text-xs text-green-500/60 whitespace-pre-wrap break-all">
                      {JSON.stringify(item.payload || item, null, 2)}
                    </pre>
                  </div>
                </div>
              );
            })
          )}
          <div ref={endOfListRef} className="h-4" />
        </div>
      </div>
      
      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: #000;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(0, 255, 0, 0.2);
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(0, 255, 0, 0.4);
        }
      `}</style>
    </div>
  );
};
