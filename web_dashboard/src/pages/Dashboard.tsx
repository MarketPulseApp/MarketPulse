import React, { useEffect, useRef, useState } from 'react';
import { createChart, CandlestickSeries, createSeriesMarkers } from 'lightweight-charts';
import type { IChartApi, ISeriesApi, CandlestickData, Time, SeriesMarker } from 'lightweight-charts';

export const Dashboard: React.FC = () => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  const [connectionStatus, setConnectionStatus] = useState<string>('Connecting...');

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Initialize chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 400,
      layout: {
        background: { color: '#ffffff' },
        textColor: '#333',
      },
      grid: {
        vertLines: { color: '#f0f0f0' },
        horzLines: { color: '#f0f0f0' },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: true,
      }
    });

    chartRef.current = chart;

    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });

    seriesRef.current = candlestickSeries;

    const markersPlugin = createSeriesMarkers(candlestickSeries, []);

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    window.addEventListener('resize', handleResize);

    // WebSocket connection
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/market`;
    let ws: WebSocket;

    let reconnectTimeout: ReturnType<typeof setTimeout>;

    // Keep track of markers
    let markers: SeriesMarker<Time>[] = [];

    // Helper to format time to unix seconds safely
    const formatTime = (timeData: any): Time => {
      // if it's already a string like "2021-12-31" lightweight-charts accepts it if it's daily
      // but usually for intraday we need a unix timestamp in seconds
      if (typeof timeData === 'string') {
        const parsed = new Date(timeData).getTime();
        if (!isNaN(parsed)) return Math.floor(parsed / 1000) as Time;
      }
      if (typeof timeData === 'number') {
        // if it's in milliseconds (larger than year 2300 in seconds)
        if (timeData > 10000000000) {
          return Math.floor(timeData / 1000) as Time;
        }
        return timeData as Time;
      }
      // Fallback to current time
      return Math.floor(Date.now() / 1000) as Time;
    };

    const connectWs = () => {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setConnectionStatus('Connected');
        console.log('WebSocket connected to', wsUrl);
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          let data = payload;
          if (payload.data) {
             data = payload.data;
          }

          // Check for candlestick data
          if (data.open !== undefined && data.close !== undefined) {
            const candle: CandlestickData = {
              time: formatTime(data.time || data.timestamp),
              open: parseFloat(data.open),
              high: parseFloat(data.high),
              low: parseFloat(data.low),
              close: parseFloat(data.close),
            };
            if (data.time || data.timestamp || candle.time) {
              candlestickSeries.update(candle);
            }
          }

          // Check for trade execution (Paper Trade)
          const typeOrSide = data.side || data.action || payload.side || payload.action || payload.type || data.type;
          const isTrade = typeof typeOrSide === 'string' && (typeOrSide.toLowerCase() === 'buy' || typeOrSide.toLowerCase() === 'sell');

          if (isTrade && data.price !== undefined) {
            const tradeTime = formatTime(data.time || data.timestamp);
            const sideStr = typeOrSide.toLowerCase();

            markers.push({
              time: tradeTime,
              position: sideStr === 'buy' ? 'belowBar' : 'aboveBar',
              color: sideStr === 'buy' ? '#26a69a' : '#ef5350',
              shape: sideStr === 'buy' ? 'arrowUp' : 'arrowDown',
              text: `${sideStr.toUpperCase()} @ ${data.price}`,
              size: 2,
            });

            // Sort markers by time
            markers.sort((a, b) => (a.time as number) - (b.time as number));

            markersPlugin.setMarkers(markers);
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err, event.data);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('Error');
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected. Reconnecting in 5s...');
        setConnectionStatus('Disconnected');
        reconnectTimeout = setTimeout(connectWs, 5000);
      };
    };

    connectWs();

    return () => {
      window.removeEventListener('resize', handleResize);
      clearTimeout(reconnectTimeout);
      if (ws) ws.close();
      chart.remove();
    };
  }, []);

  return (
    <div>
      <div className="flex justify-between items-center mb-4 sm:mb-6">
        <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Market Overview</h1>
        <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-full shadow-sm border border-gray-100">
          <span className={`w-2.5 h-2.5 rounded-full ${
            connectionStatus === 'Connected' ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' :
            connectionStatus === 'Error' ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]' :
            'bg-yellow-500 shadow-[0_0_8px_rgba(234,179,8,0.6)]'
          }`}></span>
          <span className="text-xs sm:text-sm font-medium text-gray-600">{connectionStatus}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 sm:gap-6 mb-6 sm:mb-8">
        <div className="bg-white p-4 sm:p-6 rounded-xl shadow-sm border border-gray-100">
          <h3 className="text-xs sm:text-sm font-medium text-gray-500 mb-1">Total Portfolio Value</h3>
          <p className="text-xl sm:text-2xl font-bold text-gray-900">$10,000.00</p>
        </div>
        <div className="bg-white p-4 sm:p-6 rounded-xl shadow-sm border border-gray-100">
          <h3 className="text-xs sm:text-sm font-medium text-gray-500 mb-1">24h Return</h3>
          <p className="text-xl sm:text-2xl font-bold text-green-500">+2.4%</p>
        </div>
        <div className="bg-white p-4 sm:p-6 rounded-xl shadow-sm border border-gray-100">
          <h3 className="text-xs sm:text-sm font-medium text-gray-500 mb-1">Active Positions</h3>
          <p className="text-xl sm:text-2xl font-bold text-gray-900">4</p>
        </div>

        {/* Zero-click Prediction Card */}
        <div className="group bg-gradient-to-br from-indigo-50 to-white p-4 sm:p-6 rounded-xl shadow-sm border border-indigo-100 relative overflow-hidden transition-all duration-300 cursor-default">
          <div className="absolute inset-0 bg-indigo-600 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col items-center justify-center text-white z-10">
            <span className="text-2xl font-bold">Buy</span>
            <span className="text-sm">Confidence: 94%</span>
          </div>
          <div className="relative z-0 group-hover:opacity-0 transition-opacity duration-300">
            <div className="flex justify-between items-center mb-1">
              <h3 className="text-xs sm:text-sm font-bold text-indigo-900">AI Prediction</h3>
              <span className="text-xs bg-indigo-200 text-indigo-800 px-2 py-0.5 rounded-full">AAPL</span>
            </div>
            <p className="text-sm text-gray-600">Next 5m Trend</p>
            <div className="mt-2 text-indigo-600 font-medium text-sm flex items-center">
              Hover to reveal <span className="ml-1">→</span>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white p-4 sm:p-6 rounded-xl shadow-sm border border-gray-100 mb-6 sm:mb-8">
        <h2 className="text-base sm:text-lg font-bold text-gray-900 mb-3 sm:mb-4">Live Market Data (1s)</h2>
        <div ref={chartContainerRef} className="w-full h-[450px]" />
      </div>
    </div>
  );
};
