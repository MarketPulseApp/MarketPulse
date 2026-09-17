

export const Why = () => {
    return (
        <div className="p-6">
            <h1 className="text-2xl font-bold mb-4">The "Why"</h1>
            <div className="bg-white p-6 rounded shadow-sm border">
                <h2 className="text-xl font-semibold mb-2">Why MarketPulse?</h2>
                <p className="text-gray-700 mb-4">
                    MarketPulse provides cutting edge, real-time insights into the market. We aim to empower traders with ultra-fast execution, predictive analytics, and an edge over the competition.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
                    <div className="p-4 bg-blue-50 rounded-lg">
                        <h3 className="font-bold text-blue-800">Speed</h3>
                        <p className="text-sm text-blue-600 mt-2">Zero-latency data pipelines powered by Rust and WebSockets.</p>
                    </div>
                    <div className="p-4 bg-purple-50 rounded-lg">
                        <h3 className="font-bold text-purple-800">Intelligence</h3>
                        <p className="text-sm text-purple-600 mt-2">Machine learning models that predict market movements before they happen.</p>
                    </div>
                    <div className="p-4 bg-green-50 rounded-lg">
                        <h3 className="font-bold text-green-800">Reliability</h3>
                        <p className="text-sm text-green-600 mt-2">Distributed architecture ensuring 99.99% uptime during peak volatility.</p>
                    </div>
                </div>
            </div>
        </div>
    );
};
