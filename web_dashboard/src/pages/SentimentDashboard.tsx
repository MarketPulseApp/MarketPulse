import React from 'react';

export const SentimentDashboard: React.FC = () => {
  // Mock sentiment data
  const sentiments = [
    { ticker: 'AAPL', score: 0.85, label: 'Bullish', articles: 124 },
    { ticker: 'TSLA', score: -0.45, label: 'Bearish', articles: 89 },
    { ticker: 'MSFT', score: 0.92, label: 'Very Bullish', articles: 156 },
    { ticker: 'META', score: 0.12, label: 'Neutral', articles: 67 },
    { ticker: 'NVDA', score: 0.95, label: 'Very Bullish', articles: 210 },
  ];

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4 text-gray-800">Social Sentiment Dashboard</h1>
      <p className="text-gray-600 mb-6">Real-time sentiment analysis from social media and news sources.</p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Overall Market Sentiment</h3>
          <div className="flex items-center">
            <span className="text-3xl font-bold text-green-600">Bullish</span>
            <span className="ml-2 text-gray-400">(68%)</span>
          </div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Most Discussed Ticker</h3>
          <div className="flex items-center">
            <span className="text-3xl font-bold text-blue-600">NVDA</span>
            <span className="ml-2 text-gray-400">210 mentions/hr</span>
          </div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Sentiment Shift (24h)</h3>
          <div className="flex items-center">
            <span className="text-3xl font-bold text-green-500">+12%</span>
            <svg className="w-6 h-6 text-green-500 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-800">Top Tickers by Sentiment</h2>
        </div>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ticker</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sentiment Score</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Label</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Article Volume</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sentiments.map((item) => (
              <tr key={item.ticker}>
                <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{item.ticker}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="w-full bg-gray-200 rounded-full h-2.5">
                    <div
                      className={`h-2.5 rounded-full ${item.score > 0.5 ? 'bg-green-600' : item.score < -0.2 ? 'bg-red-600' : 'bg-yellow-400'}`}
                      style={{ width: `${Math.abs(item.score * 100)}%` }}
                    ></div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                    item.score > 0.5 ? 'bg-green-100 text-green-800' :
                    item.score < -0.2 ? 'bg-red-100 text-red-800' :
                    'bg-yellow-100 text-yellow-800'
                  }`}>
                    {item.label}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{item.articles}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
