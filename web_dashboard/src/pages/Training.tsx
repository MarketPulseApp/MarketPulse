import React, { useState, useEffect, useRef } from 'react';
import { Play, Square, Activity } from 'lucide-react';

interface TrainingStatus {
  epoch: number;
  loss: number;
  dataSource: string;
  stage: string;
  progress: number;
}

export const Training: React.FC = () => {
  const [isTraining, setIsTraining] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [status, setStatus] = useState<TrainingStatus>({
    epoch: 0,
    loss: 0.0,
    dataSource: '-',
    stage: 'Idle',
    progress: 0,
  });
  
  const wsRef = useRef<WebSocket | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const handleStartTraining = () => {
    if (isTraining) return;
    setIsTraining(true);
    setLogs(prev => [...prev, '> Initializing training sequence...']);
    
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/training`;
      
      
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setLogs(prev => [...prev, '> Connected to training server.']);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'log') {
          setLogs(prev => [...prev, `> ${data.message}`]);
        }
        if (data.type === 'status') {
          setStatus(prev => ({
            ...prev,
            ...data.payload
          }));
        }
      } catch (e) {
        setLogs(prev => [...prev, `> ${event.data}`]);
      }
    };

    ws.onclose = () => {
      setLogs(prev => [...prev, '> Connection closed.']);
      setIsTraining(false);
    };

    ws.onerror = () => {
      setLogs(prev => [...prev, '> WebSocket error occurred.']);
      setIsTraining(false);
    };
  };

  const handleStopTraining = () => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    setIsTraining(false);
    setStatus(prev => ({ ...prev, stage: 'Stopped' }));
    setLogs(prev => [...prev, '> Training stopped by user.']);
  };

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Model Training</h1>
          <p className="text-gray-500 dark:text-gray-400">Monitor and control the deep learning training pipeline.</p>
        </div>
        <div className="flex space-x-4">
          {!isTraining ? (
            <button
              onClick={handleStartTraining}
              className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
            >
              <Play size={20} />
              <span>Start Training</span>
            </button>
          ) : (
            <button
              onClick={handleStopTraining}
              className="flex items-center space-x-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              <Square size={20} />
              <span>Stop Training</span>
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 p-4 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="text-sm text-gray-500 dark:text-gray-400">Epoch</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{status.epoch}</div>
        </div>
        <div className="bg-white dark:bg-gray-800 p-4 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="text-sm text-gray-500 dark:text-gray-400">Loss</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{status.loss.toFixed(4)}</div>
        </div>
        <div className="bg-white dark:bg-gray-800 p-4 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="text-sm text-gray-500 dark:text-gray-400">Current Data Source</div>
          <div className="text-lg font-bold text-gray-900 dark:text-white truncate">{status.dataSource}</div>
        </div>
        <div className="bg-white dark:bg-gray-800 p-4 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="text-sm text-gray-500 dark:text-gray-400">Stage</div>
          <div className="text-lg font-bold text-gray-900 dark:text-white">{status.stage}</div>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm space-y-4">
        <div className="flex justify-between text-sm font-medium text-gray-700 dark:text-gray-300">
          <span>Overall Progress</span>
          <span>{status.progress}%</span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
          <div 
            className="bg-indigo-600 h-2.5 rounded-full transition-all duration-300" 
            style={{ width: `${status.progress}%` }}
          ></div>
        </div>
      </div>

      <div className="bg-black rounded-xl p-4 shadow-lg flex flex-col h-96">
        <div className="flex items-center space-x-2 mb-4 border-b border-gray-800 pb-2">
          <Activity size={16} className="text-green-500" />
          <span className="text-green-500 font-mono text-sm">Terminal Output</span>
        </div>
        <div className="flex-1 overflow-y-auto font-mono text-sm text-green-400 space-y-1 custom-scrollbar">
          {logs.map((log, i) => (
            <div key={i}>{log}</div>
          ))}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  );
};
