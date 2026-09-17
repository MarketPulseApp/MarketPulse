import { useState, useEffect } from 'react';
import apiClient from '../api/client';

const STRATEGIES = [
  {
    id: 'zero_loss_random_forest',
    name: 'Zero-Loss Random Forest',
    description: 'Strict anomaly detection, 99.9% default, relies heavily on Insider + Macro filtering to avoid macro-drawdowns.'
  },
  {
    id: 'social_sentiment_scalper',
    name: 'Social Sentiment Scalper',
    description: 'Aggressive Gradient Boosting, highly weights Reddit/StockTwits data to catch momentum bursts.'
  },
  {
    id: 'options_flow_statarb',
    name: 'Options Flow StatArb',
    description: 'Focuses on put/call ratios and gamma squeezes.'
  },
  {
    id: 'omni_fusion_ensemble',
    name: 'Omni-Fusion Ensemble',
    description: 'The ultimate master strategy. Utilizes all data simultaneously (Reddit, StockTwits, Insider/Congressional trades, FRED, Options, RSS, OHLCV) using a massive unified feature array to find complex, non-linear correlations across every data source.'
  }
];

export const Settings = () => {
  const [strategy, setStrategy] = useState('zero_loss_random_forest');
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.999);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');

  useEffect(() => {
    fetchTradingSettings();
  }, []);

  const fetchTradingSettings = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.get('/api/api/v1/settings/trading');
      if (response.data) {
        if (response.data.active_strategy) setStrategy(response.data.active_strategy);
        if (response.data.confidence_threshold !== undefined) {
          setConfidenceThreshold(response.data.confidence_threshold);
        }
      }
    } catch (error) {
      console.error('Failed to fetch trading settings:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const saveTradingSettings = async () => {
    setIsSaving(true);
    setSaveStatus('idle');
    const payload = {
      active_strategy: strategy,
      confidence_threshold: confidenceThreshold
    };
    try {
      console.log('Sending trading settings payload:', payload);
      await apiClient.put('/api/api/v1/settings/trading', payload);
      setSaveStatus('success');
      setTimeout(() => setSaveStatus('idle'), 3000);
    } catch (error) {
      console.error('Failed to save trading settings. Full error:', error, { payload });
      setSaveStatus('error');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>
      
      <div className="space-y-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">ML Trading Configuration</h2>
          {isLoading ? (
            <div className="text-sm text-gray-500 dark:text-gray-400">Loading settings...</div>
          ) : (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">ML Strategy</label>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  {STRATEGIES.map((strat) => (
                    <div
                      key={strat.id}
                      onClick={() => setStrategy(strat.id)}
                      className={`relative flex cursor-pointer rounded-lg border bg-white dark:bg-gray-700 p-4 shadow-sm focus:outline-none ${
                        strategy === strat.id
                          ? 'border-blue-500 ring-1 ring-blue-500'
                          : 'border-gray-300 dark:border-gray-600 hover:border-blue-400'
                      }`}
                    >
                      <div className="flex flex-1">
                        <div className="flex flex-col">
                          <span className="block text-sm font-medium text-gray-900 dark:text-white">
                            {strat.name}
                          </span>
                          <span className="mt-1 flex items-center text-xs text-gray-500 dark:text-gray-400">
                            {strat.description}
                          </span>
                        </div>
                      </div>
                      {strategy === strat.id && (
                        <div className="absolute -top-2 -right-2 h-5 w-5 rounded-full bg-blue-500 flex items-center justify-center text-white">
                          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                          </svg>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">Confidence Threshold</label>
                  <span className="text-sm font-semibold text-blue-600 bg-blue-50 px-2 py-1 rounded">
                    {(confidenceThreshold * 100).toFixed(1)}%
                  </span>
                </div>
                <input
                  type="range"
                  min="0.50"
                  max="0.999"
                  step="0.001"
                  value={confidenceThreshold}
                  onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
                  className="w-full h-2 bg-gray-200 dark:bg-gray-600 rounded-lg appearance-none cursor-pointer accent-blue-600"
                />
                <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                  Minimum prediction confidence required to execute a trade. Higher values mean fewer, safer trades.
                </p>
              </div>

              <div className="pt-4 flex items-center justify-end space-x-4">
                {saveStatus === 'success' && (
                  <span className="text-sm text-green-600 font-medium flex items-center">
                    <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path></svg>
                    Saved successfully
                  </span>
                )}
                {saveStatus === 'error' && (
                  <span className="text-sm text-red-600 font-medium">
                    Failed to save
                  </span>
                )}
                <button
                  onClick={saveTradingSettings}
                  disabled={isSaving}
                  className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isSaving ? 'Saving...' : 'Save Configuration'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
