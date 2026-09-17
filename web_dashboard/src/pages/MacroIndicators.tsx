import React from 'react';

export const MacroIndicators: React.FC = () => {
  const indicators = [
    { name: 'US GDP Growth', value: '2.4%', previous: '2.1%', status: 'up' },
    { name: 'Inflation (CPI)', value: '3.1%', previous: '3.2%', status: 'down' },
    { name: 'Unemployment Rate', value: '3.7%', previous: '3.9%', status: 'down' },
    { name: 'Fed Funds Rate', value: '5.25-5.50%', previous: '5.25-5.50%', status: 'neutral' },
  ];

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4 text-gray-800">Macroeconomic Indicators</h1>
      <p className="text-gray-600 mb-6">Track key global economic data points affecting market performance.</p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {indicators.map((ind, idx) => (
          <div key={idx} className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 flex flex-col justify-between">
            <h3 className="text-sm font-medium text-gray-500 mb-4">{ind.name}</h3>
            <div>
              <div className="text-3xl font-bold text-gray-900 mb-1">{ind.value}</div>
              <div className="text-sm text-gray-500 flex items-center">
                <span>Prev: {ind.previous}</span>
                {ind.status === 'up' && <svg className="w-4 h-4 text-green-500 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" /></svg>}
                {ind.status === 'down' && <svg className="w-4 h-4 text-red-500 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" /></svg>}
                {ind.status === 'neutral' && <svg className="w-4 h-4 text-gray-400 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14" /></svg>}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-medium text-gray-800 mb-4">Yield Curve</h2>
        <div className="h-64 flex items-end justify-between space-x-2 pb-6 border-b border-gray-200">
          {/* Mock yield curve chart */}
          {['1M', '3M', '6M', '1Y', '2Y', '5Y', '10Y', '30Y'].map((maturity, i) => {
            // Inverted yield curve mock
            const heights = [100, 110, 115, 110, 95, 80, 85, 90];
            return (
              <div key={maturity} className="flex flex-col items-center flex-1">
                <div
                  className="w-full bg-blue-500 rounded-t-sm"
                  style={{ height: `${heights[i]}%`, maxHeight: '100%' }}
                ></div>
                <span className="text-xs text-gray-500 mt-2">{maturity}</span>
              </div>
            )
          })}
        </div>
        <p className="text-sm text-gray-500 mt-4 text-center">US Treasury Yields - The curve remains slightly inverted.</p>
      </div>
    </div>
  );
};
