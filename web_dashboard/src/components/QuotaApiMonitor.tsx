import React from 'react';
import { Activity, Database, Server, Zap } from 'lucide-react';

export const QuotaApiMonitor: React.FC = () => {
  return (
    <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-100 flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-800 flex items-center gap-2">
          <Activity size={18} className="text-indigo-600" />
          Quota & API Usage
        </h3>
        <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full">Active</span>
      </div>
      
      <div className="space-y-4 flex-1">
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-600 flex items-center gap-1"><Zap size={14} /> Requests / min</span>
            <span className="font-medium">4,521 / 5,000</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div className="bg-amber-500 h-2 rounded-full" style={{ width: '90%' }}></div>
          </div>
        </div>

        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-600 flex items-center gap-1"><Database size={14} /> DB Connections</span>
            <span className="font-medium">42 / 100</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div className="bg-indigo-500 h-2 rounded-full" style={{ width: '42%' }}></div>
          </div>
        </div>

        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-600 flex items-center gap-1"><Server size={14} /> Bandwidth (TB)</span>
            <span className="font-medium">1.2 / 5.0</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div className="bg-green-500 h-2 rounded-full" style={{ width: '24%' }}></div>
          </div>
        </div>
      </div>
      
      <div className="mt-4 pt-4 border-t border-gray-100 grid grid-cols-2 gap-2 text-center text-sm">
        <div className="bg-gray-50 p-2 rounded">
          <p className="text-gray-500 text-xs">Latency</p>
          <p className="font-bold text-gray-800">24ms</p>
        </div>
        <div className="bg-gray-50 p-2 rounded">
          <p className="text-gray-500 text-xs">Error Rate</p>
          <p className="font-bold text-green-600">0.01%</p>
        </div>
      </div>
    </div>
  );
};
