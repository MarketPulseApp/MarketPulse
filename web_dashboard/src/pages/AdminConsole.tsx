

export const AdminConsole = () => {
    return (
        <div className="p-6">
            <h1 className="text-2xl font-bold mb-4">Admin Console</h1>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-white p-6 rounded shadow-sm border">
                    <h2 className="text-lg font-semibold mb-4 border-b pb-2">System Status</h2>
                    <ul className="space-y-3">
                        <li className="flex justify-between items-center">
                            <span className="text-gray-600">API Gateway</span>
                            <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-medium">Online</span>
                        </li>
                        <li className="flex justify-between items-center">
                            <span className="text-gray-600">Database Engine</span>
                            <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-medium">Online</span>
                        </li>
                        <li className="flex justify-between items-center">
                            <span className="text-gray-600">ML Prediction Service</span>
                            <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs font-medium">Degraded</span>
                        </li>
                    </ul>
                </div>
                
                <div className="bg-white p-6 rounded shadow-sm border">
                    <h2 className="text-lg font-semibold mb-4 border-b pb-2">User Management</h2>
                    <div className="flex justify-between items-center mb-4">
                        <span className="text-3xl font-bold text-gray-800">1,248</span>
                        <span className="text-sm text-gray-500">Active Users</span>
                    </div>
                    <button className="w-full py-2 bg-gray-800 text-white rounded hover:bg-gray-700 transition-colors">
                        View User Directory
                    </button>
                </div>
            </div>
        </div>
    );
};
