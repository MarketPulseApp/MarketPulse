import React from 'react';

export const InsiderTrading: React.FC = () => {
  const trades = [
    { id: 1, ticker: 'NVDA', insider: 'Huang Jen Hsun', title: 'CEO', type: 'Sell', shares: '240,000', value: '$21,450,000', date: '2026-09-14' },
    { id: 2, ticker: 'AAPL', insider: 'Cook Timothy D', title: 'CEO', type: 'Sell', shares: '196,410', value: '$34,352,000', date: '2026-09-12' },
    { id: 3, ticker: 'PLTR', insider: 'Karp Alexander', title: 'CEO', type: 'Buy', shares: '500,000', value: '$12,500,000', date: '2026-09-10' },
    { id: 4, ticker: 'AMD', insider: 'Su Lisa T', title: 'CEO', type: 'Sell', shares: '125,000', value: '$19,875,000', date: '2026-09-08' },
    { id: 5, ticker: 'TSLA', insider: 'Musk Elon', title: 'CEO', type: 'Buy', shares: '100,000', value: '$22,500,000', date: '2026-09-05' },
  ];

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4 text-gray-800">Insider Trading Activity</h1>
      <p className="text-gray-600 mb-6">Track recent Form 4 filings for executive buys and sells.</p>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-lg font-medium text-gray-800">Recent Transactions</h2>
          <div className="flex space-x-2">
            <button className="px-3 py-1 bg-green-100 text-green-700 rounded-md text-sm font-medium">Buys</button>
            <button className="px-3 py-1 bg-red-100 text-red-700 rounded-md text-sm font-medium">Sells</button>
          </div>
        </div>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ticker</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Insider</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Shares</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Value</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {trades.map((trade) => (
              <tr key={trade.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{trade.date}</td>
                <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{trade.ticker}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">{trade.insider}</div>
                  <div className="text-xs text-gray-500">{trade.title}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                    trade.type === 'Buy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {trade.type}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{trade.shares}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{trade.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
