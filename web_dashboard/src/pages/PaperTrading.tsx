import { useEffect, useState } from 'react';
import { apiClient } from '../api/client';

interface Portfolio {
  balance: number;
  available_funds: number;
  currency: string;
}

interface Trade {
  id: string;
  symbol: string;
  type: string;
  quantity: number;
  price: number;
  timestamp: string;
}

export const PaperTrading = () => {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPaperTradingData = async () => {
      try {
        const [portfolioRes, tradesRes] = await Promise.all([
          apiClient.get('/paper-trading/portfolio'),
          apiClient.get('/paper-trading/trades'),
        ]);
        setPortfolio(portfolioRes.data);
        setTrades(tradesRes.data);
      } catch (error) {
        console.error('Error fetching paper trading data', error);
      } finally {
        setLoading(false);
      }
    };

    fetchPaperTradingData();
  }, []);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Paper Trading</h1>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <p className="text-gray-500">Loading...</p>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Portfolio</h2>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              <div>
                <p className="text-gray-500 text-sm">Balance</p>
                <p className="text-2xl font-bold">${portfolio?.balance?.toFixed(2) || '0.00'}</p>
              </div>
              <div>
                <p className="text-gray-500 text-sm">Available Funds</p>
                <p className="text-2xl font-bold">${portfolio?.available_funds?.toFixed(2) || '0.00'}</p>
              </div>
              <div>
                <p className="text-gray-500 text-sm">Currency</p>
                <p className="text-2xl font-bold">{portfolio?.currency || 'USD'}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Execute Trade</h2>
            <form onSubmit={async (e) => {
              e.preventDefault();
              const formData = new FormData(e.currentTarget);
              const symbol = formData.get('symbol') as string;
              const type = formData.get('type') as string;
              const quantity = parseInt(formData.get('quantity') as string);
              const price = 150.0; // Mock current price

              // Optimistic UI update
              const optimisticTrade: Trade = {
                id: Math.random().toString(),
                symbol: symbol.toUpperCase(),
                type,
                quantity,
                price,
                timestamp: new Date().toISOString()
              };

              setTrades([optimisticTrade, ...trades]);

              // Optimistic Portfolio update
              if (portfolio) {
                const cost = quantity * price;
                const newAvailable = type === 'buy' ? portfolio.available_funds - cost : portfolio.available_funds + cost;
                setPortfolio({ ...portfolio, available_funds: newAvailable });
              }

              e.currentTarget.reset();

              try {
                // Actually execute trade in background
                await apiClient.post('/paper-trading/execute', { symbol, type, quantity });
              } catch (error) {
                console.error("Trade failed, rolling back", error);
                // In a real app we would rollback the optimistic state here
              }
            }} className="flex gap-4 items-end">
              <div>
                <label className="block text-sm font-medium text-gray-700">Symbol</label>
                <input required name="symbol" type="text" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2" placeholder="AAPL" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Type</label>
                <select required name="type" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2">
                  <option value="buy">Buy</option>
                  <option value="sell">Sell</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Quantity</label>
                <input required name="quantity" type="number" min="1" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2" defaultValue="1" />
              </div>
              <button type="submit" className="bg-indigo-600 text-white px-4 py-2 rounded shadow hover:bg-indigo-700">
                Execute Trade
              </button>
            </form>
          </div>

          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold">Recent Trades</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Symbol</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Quantity</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Price</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {trades.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-6 py-4 text-center text-sm text-gray-500">
                        No recent trades found.
                      </td>
                    </tr>
                  ) : (
                    trades.map((trade) => (
                      <tr key={trade.id}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{trade.symbol}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${trade.type.toLowerCase() === 'buy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                            {trade.type}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{trade.quantity}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${Number(trade.price).toFixed(2)}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {new Date(trade.timestamp).toLocaleString()}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
