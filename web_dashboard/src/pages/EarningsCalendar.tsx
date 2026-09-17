import React from 'react';

export const EarningsCalendar: React.FC = () => {
  const earnings = [
    { id: 1, date: '2026-09-17', time: 'BMO', ticker: 'ORCL', name: 'Oracle Corp', estEPS: '$1.15', rev: '$12.4B' },
    { id: 2, date: '2026-09-17', time: 'AMC', ticker: 'ADBE', name: 'Adobe Inc.', estEPS: '$4.05', rev: '$5.1B' },
    { id: 3, date: '2026-09-18', time: 'BMO', ticker: 'LEN', name: 'Lennar Corp', estEPS: '$3.20', rev: '$8.5B' },
    { id: 4, date: '2026-09-19', time: 'AMC', ticker: 'FDX', name: 'FedEx Corp', estEPS: '$4.85', rev: '$21.9B' },
    { id: 5, date: '2026-09-20', time: 'BMO', ticker: 'DRI', name: 'Darden Restaurants', estEPS: '$1.75', rev: '$2.7B' },
  ];

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4 text-gray-800">Earnings Calendar</h1>
      <p className="text-gray-600 mb-6">Upcoming earnings announcements and estimates.</p>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center bg-gray-50">
          <h2 className="text-lg font-medium text-gray-800">This Week</h2>
          <select className="block w-48 pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md">
            <option>This Week</option>
            <option>Next Week</option>
            <option>This Month</option>
          </select>
        </div>
        
        <div className="divide-y divide-gray-200">
          {earnings.map((item) => (
            <div key={item.id} className="p-6 flex items-center hover:bg-gray-50 transition-colors">
              <div className="flex-shrink-0 mr-6 w-24 text-center">
                <div className="text-sm font-bold text-gray-900">{new Date(item.date).toLocaleDateString('en-US', { weekday: 'short' })}</div>
                <div className="text-xl font-light text-gray-500">{new Date(item.date).getDate()}</div>
                <div className="text-xs font-semibold text-gray-400 mt-1">{item.time === 'BMO' ? '☀️ Pre-Market' : '🌙 After-Close'}</div>
              </div>
              
              <div className="flex-grow flex items-center justify-between">
                <div>
                  <div className="text-lg font-bold text-blue-600">{item.ticker}</div>
                  <div className="text-sm text-gray-500">{item.name}</div>
                </div>
                
                <div className="flex space-x-12">
                  <div className="text-right">
                    <div className="text-xs text-gray-500 uppercase">Est EPS</div>
                    <div className="text-md font-medium text-gray-900">{item.estEPS}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-gray-500 uppercase">Est Rev</div>
                    <div className="text-md font-medium text-gray-900">{item.rev}</div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
