import { useState, useEffect } from 'react';
import { getDb } from '../utils/duckdb';

export const Analytics = () => {
    const [query, setQuery] = useState("SELECT 1 AS num, 'Hello DuckDB' AS msg");
    const [result, setResult] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        // Initialize DB on mount and load some dummy data
        const init = async () => {
            try {
                const db = await getDb();
                const conn = await db.connect();
                // Create a sample table
                await conn.query(`
                    CREATE TABLE IF NOT EXISTS trades (
                        symbol VARCHAR,
                        price DOUBLE,
                        volume INTEGER
                    )
                `);
                await conn.query(`
                    INSERT INTO trades VALUES
                    ('AAPL', 150.5, 1000),
                    ('MSFT', 250.0, 500),
                    ('GOOGL', 2700.2, 200)
                `);
                await conn.close();
            } catch (err: any) {
                console.error("Failed to init DuckDB", err);
            }
        };
        init();
    }, []);

    const runQuery = async () => {
        setLoading(true);
        setError(null);
        try {
            const db = await getDb();
            const conn = await db.connect();
            const arrowResult = await conn.query(query);
            const array = arrowResult.toArray().map(row => row.toJSON());
            setResult(array);
            await conn.close();
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="p-6">
            <h1 className="text-2xl font-bold mb-4">In-Memory Analytics</h1>
            <p className="mb-4 text-gray-600">Ultra-fast client-side data slicing with DuckDB Wasm.</p>

            <div className="mb-4">
                <textarea
                    className="w-full h-32 p-4 border rounded font-mono text-sm shadow-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                />
            </div>

            <button
                className="bg-blue-600 text-white px-6 py-2 rounded shadow hover:bg-blue-700 transition-colors"
                onClick={runQuery}
                disabled={loading}
            >
                {loading ? 'Running...' : 'Run Query'}
            </button>

            {error && (
                <div className="mt-4 p-4 bg-red-50 text-red-700 rounded border border-red-200">
                    {error}
                </div>
            )}

            {result.length > 0 && (
                <div className="mt-6 overflow-x-auto bg-white rounded shadow-sm border">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                {Object.keys(result[0] || {}).map((key) => (
                                    <th key={key} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        {key}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {result.map((row, i) => (
                                <tr key={i} className="hover:bg-gray-50">
                                    {Object.values(row).map((val: any, j) => (
                                        <td key={j} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                            {String(val)}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
};
