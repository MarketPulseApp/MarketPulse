import React, { useState, useEffect, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { DataExport } from '../components/DataExport';
import { Info, Brain, Activity, TrendingUp } from 'lucide-react';

const FEATURE_IMPORTANCES = [
  { feature: 'RSI (14)', importance: 0.35, description: 'Relative Strength Index over 14 periods' },
  { feature: 'MACD Signal', importance: 0.22, description: 'Moving Average Convergence Divergence' },
  { feature: 'Volume Change', importance: 0.15, description: 'Percentage change in volume over 24h' },
  { feature: 'SMA (50) Distance', importance: 0.12, description: 'Distance from 50-day Simple Moving Average' },
  { feature: 'Bollinger Band %b', importance: 0.09, description: 'Position relative to Bollinger Bands' },
  { feature: 'VWAP Distance', importance: 0.07, description: 'Distance from Volume Weighted Average Price' },
];

const TREE_DATA = {
  nodes: [
    { id: 'root', name: 'RSI > 70?', val: 10, color: '#6366f1' },
    { id: 'n1', name: 'MACD > 0?', val: 8, color: '#6366f1' },
    { id: 'n2', name: 'SELL', val: 6, color: '#ef4444' },
    { id: 'n3', name: 'Vol > 1M?', val: 8, color: '#6366f1' },
    { id: 'n4', name: 'HOLD', val: 6, color: '#9ca3af' },
    { id: 'n5', name: 'BUY', val: 6, color: '#22c55e' },
    { id: 'n6', name: 'HOLD', val: 6, color: '#9ca3af' }
  ],
  links: [
    { source: 'root', target: 'n1', label: 'No' },
    { source: 'root', target: 'n2', label: 'Yes' },
    { source: 'n1', target: 'n3', label: 'Yes' },
    { source: 'n1', target: 'n4', label: 'No' },
    { source: 'n3', target: 'n5', label: 'Yes' },
    { source: 'n3', target: 'n6', label: 'No' }
  ]
};

export const WhyTab: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 400 });

  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: 400
        });
      }
    };
    
    // Initial size
    handleResize();
    
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <div className="max-w-7xl mx-auto pb-10">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Brain className="w-6 h-6 text-indigo-500" />
            Model Explanations (Why)
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Understand the internal decision-making process of the trading model.
          </p>
        </div>
        
        {/* Export Module is placed here to easily export feature importance data */}
        <div className="bg-white p-2 rounded-lg border border-gray-200 shadow-sm">
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 block px-2 pt-1">
            Export Model Data
          </span>
          <DataExport data={FEATURE_IMPORTANCES} filename="feature_importances" />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        
        {/* Feature Importances Card */}
        <div className="lg:col-span-1 bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex flex-col">
          <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-500" />
            Feature Importances
          </h2>
          
          <div className="flex-1 overflow-y-auto pr-2">
            <div className="space-y-4">
              {FEATURE_IMPORTANCES.map((feature, idx) => (
                <div key={idx} className="group">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm font-medium text-gray-700 flex items-center gap-1">
                      {feature.feature}
                      <div className="relative flex items-center">
                        <Info className="w-3 h-3 text-gray-400 cursor-help" />
                        <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 hidden group-hover:block w-48 p-2 bg-gray-800 text-white text-xs rounded shadow-lg z-10 text-center">
                          {feature.description}
                          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800"></div>
                        </div>
                      </div>
                    </span>
                    <span className="text-sm font-bold text-gray-900">
                      {(feature.importance * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2.5">
                    <div 
                      className="bg-blue-500 h-2.5 rounded-full transition-all duration-1000 ease-out"
                      style={{ width: Math.max(feature.importance * 100, 2) + '%' }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Decision Tree Visualizer Card */}
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex flex-col">
          <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-emerald-500" />
            Decision Tree Visualizer
          </h2>
          
          <div 
            ref={containerRef} 
            className="flex-1 w-full bg-gray-50 rounded-lg border border-gray-200 overflow-hidden relative min-h-[400px]"
          >
            <ForceGraph2D
              width={dimensions.width}
              height={dimensions.height}
              graphData={TREE_DATA}
              dagMode="td"
              dagLevelDistance={60}
              backgroundColor="#f9fafb"
              linkColor={() => '#cbd5e1'}
              linkDirectionalArrowLength={3.5}
              linkDirectionalArrowRelPos={1}
              nodeCanvasObject={(node: any, ctx, globalScale) => {
                const label = node.name;
                const fontSize = 14 / globalScale;
                ctx.font = fontSize + 'px Sans-Serif';
                
                const textWidth = ctx.measureText(label).width;
                const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.8) as [number, number];
                
                ctx.fillStyle = node.color || '#3b82f6';
                ctx.beginPath();
                ctx.roundRect(
                  node.x - bckgDimensions[0] / 2,
                  node.y - bckgDimensions[1] / 2,
                  bckgDimensions[0],
                  bckgDimensions[1],
                  4 / globalScale
                );
                ctx.fill();

                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = '#ffffff';
                ctx.fillText(label, node.x, node.y);
              }}
              linkCanvasObjectMode={() => 'after'}
              linkCanvasObject={(link: any, ctx, globalScale) => {
                if (!link.label) return;
                
                const MAX_FONT_SIZE = 12;
                
                const start = link.source;
                const end = link.target;
                
                // ignore unbound links
                if (typeof start !== 'object' || typeof end !== 'object') return;
                
                // calculate label positioning
                const textPos = Object.assign({}, ...['x', 'y'].map(c => ({
                  [c]: start[c] + (end[c] - start[c]) / 2 
                })));
                
                const relLink = { x: end.x - start.x, y: end.y - start.y };
                let textAngle = Math.atan2(relLink.y, relLink.x);
                
                // maintain label upright
                if (textAngle > Math.PI / 2) textAngle = -(Math.PI - textAngle);
                if (textAngle < -Math.PI / 2) textAngle = -(-Math.PI - textAngle);

                const fontSize = Math.min(MAX_FONT_SIZE, 12 / globalScale);
                ctx.font = fontSize + 'px Sans-Serif';
                
                ctx.save();
                ctx.translate(textPos.x, textPos.y);
                ctx.rotate(textAngle);
                
                const label = link.label;
                const padding = 2;
                const textWidth = ctx.measureText(label).width;
                
                ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
                ctx.fillRect(-textWidth / 2 - padding, -fontSize / 2 - padding, textWidth + padding * 2, fontSize + padding * 2);
                
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = '#64748b';
                ctx.fillText(label, 0, 0);
                ctx.restore();
              }}
            />
          </div>
        </div>
      </div>
      
      {/* Advanced Explanations section */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="text-md font-semibold text-gray-800 mb-3">Model Insight Summary</h3>
        <p className="text-sm text-gray-600 leading-relaxed">
          The current model relies heavily on <strong>RSI (14)</strong> and <strong>MACD Signal</strong> to determine overbought or oversold conditions. 
          When RSI exceeds the 70 threshold, the model typically looks for a MACD crossover to confirm downward momentum. 
          If volume is lacking, the model may abstain (HOLD) rather than entering a low-conviction trade.
        </p>
      </div>
    </div>
  );
};
