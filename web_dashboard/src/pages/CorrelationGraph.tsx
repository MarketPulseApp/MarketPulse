import React, { useMemo, useRef, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

export const CorrelationGraph: React.FC = () => {
  const fgRef = useRef<any>(null);
  
  // Mock data for correlation graph
  const graphData = useMemo(() => {
    const nodes = [
      { id: 'AAPL', group: 1, val: 20 },
      { id: 'MSFT', group: 1, val: 18 },
      { id: 'GOOGL', group: 1, val: 15 },
      { id: 'AMZN', group: 1, val: 15 },
      { id: 'NVDA', group: 2, val: 25 },
      { id: 'AMD', group: 2, val: 12 },
      { id: 'TSLA', group: 3, val: 16 },
      { id: 'META', group: 1, val: 14 },
    ];
    
    const links = [
      { source: 'AAPL', target: 'MSFT', value: 8 },
      { source: 'AAPL', target: 'GOOGL', value: 6 },
      { source: 'MSFT', target: 'GOOGL', value: 7 },
      { source: 'AMZN', target: 'AAPL', value: 5 },
      { source: 'NVDA', target: 'AMD', value: 9 },
      { source: 'NVDA', target: 'MSFT', value: 6 },
      { source: 'TSLA', target: 'AAPL', value: 3 },
      { source: 'META', target: 'GOOGL', value: 8 },
      { source: 'META', target: 'AMZN', value: 4 },
    ];
    
    return { nodes, links };
  }, []);

  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  // Update dimensions on mount
  React.useEffect(() => {
    const container = document.getElementById('graph-container');
    if (container) {
      setDimensions({
        width: container.clientWidth,
        height: container.clientHeight || 600
      });
    }
  }, []);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4 text-gray-800">Ticker Correlation Graph</h1>
      <p className="text-gray-600 mb-6">Interactive force-directed graph showing correlations between major tech stocks.</p>
      
      <div 
        id="graph-container" 
        className="w-full h-[600px] bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden"
      >
        <ForceGraph2D
          ref={fgRef}
          width={dimensions.width}
          height={dimensions.height}
          graphData={graphData}
          nodeLabel="id"
          nodeAutoColorBy="group"
          nodeVal="val"
          linkDirectionalParticles={2}
          linkDirectionalParticleSpeed={d => d.value * 0.001}
          nodeCanvasObject={(node: any, ctx, globalScale) => {
            const label = node.id;
            const fontSize = 12/globalScale;
            ctx.font = `${fontSize}px Sans-Serif`;
            const textWidth = ctx.measureText(label).width;
            const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2); // some padding

            ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
            ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, bckgDimensions[0], bckgDimensions[1]);

            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = node.color;
            ctx.fillText(label, node.x, node.y);
          }}
        />
      </div>
    </div>
  );
};
