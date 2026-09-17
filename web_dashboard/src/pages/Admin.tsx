import React from 'react';
import { ShieldAlert, Users, ServerCrash, Cpu, Network, Shield, AlertTriangle, Terminal, DatabaseBackup, Activity, Settings2, Unlock, Lock, FileJson, Mail, Bell, GitMerge, Fingerprint, Bug, CloudCog, HardDrive, Key, LayoutDashboard, Zap } from 'lucide-react';
import { QuotaApiMonitor } from '../components/QuotaApiMonitor';

export const Admin: React.FC = () => {
  const panels = [
    { id: 2, title: 'Active Users', icon: Users, color: 'text-blue-500', value: '1,204', desc: 'Currently online' },
    { id: 3, title: 'CPU Usage', icon: Cpu, color: 'text-rose-500', value: '78%', desc: 'Cluster avg' },
    { id: 4, title: 'Memory', icon: HardDrive, color: 'text-purple-500', value: '64GB', desc: 'Out of 128GB' },
    { id: 5, title: 'Network I/O', icon: Network, color: 'text-green-500', value: '1.2 GB/s', desc: 'Traffic rate' },
    { id: 6, title: 'System Alerts', icon: AlertTriangle, color: 'text-amber-500', value: '3', desc: 'Requires attention' },
    { id: 7, title: 'Security Scans', icon: Shield, color: 'text-indigo-500', value: 'Pass', desc: 'Last: 2m ago' },
    { id: 8, title: 'Threat Blocked', icon: ShieldAlert, color: 'text-red-500', value: '142', desc: 'Today' },
    { id: 9, title: 'Live Terminal', icon: Terminal, color: 'text-gray-700', value: 'Connected', desc: 'root@prod-01' },
    { id: 10, title: 'DB Backups', icon: DatabaseBackup, color: 'text-emerald-500', value: 'Success', desc: 'Last: 1h ago' },
    { id: 11, title: 'Cluster Status', icon: CloudCog, color: 'text-cyan-500', value: 'Healthy', desc: '5/5 Nodes' },
    { id: 12, title: 'Auth Service', icon: Key, color: 'text-orange-500', value: 'Stable', desc: '99.99% Uptime' },
    { id: 13, title: 'Errors / Exceptions', icon: Bug, color: 'text-red-600', value: '12', desc: 'In last hour' },
    { id: 14, title: 'Identity Config', icon: Fingerprint, color: 'text-teal-500', value: 'Strict', desc: 'MFA Enforced' },
    { id: 15, title: 'CI/CD Pipelines', icon: GitMerge, color: 'text-blue-600', value: 'Deployed', desc: 'v2.4.1' },
    { id: 16, title: 'Notification Queue', icon: Bell, color: 'text-yellow-500', value: '0', desc: 'Empty' },
    { id: 17, title: 'Email Relay', icon: Mail, color: 'text-slate-500', value: 'OK', desc: 'SendGrid' },
    { id: 18, title: 'Cache Hits', icon: Zap, color: 'text-yellow-400', value: '94%', desc: 'Redis' },
    { id: 19, title: 'Config Sync', icon: FileJson, color: 'text-gray-500', value: 'Synced', desc: 'Consul' },
    { id: 20, title: 'Admin Locks', icon: Lock, color: 'text-rose-600', value: 'Secured', desc: 'Superuser' },
    { id: 21, title: 'API Gateway', icon: Unlock, color: 'text-green-600', value: 'Open', desc: 'Rate limited' },
    { id: 22, title: 'Load Balancer', icon: Activity, color: 'text-blue-400', value: 'Active', desc: 'HAProxy' },
    { id: 23, title: 'Core Settings', icon: Settings2, color: 'text-gray-800', value: 'Locked', desc: 'Immutable' },
    { id: 24, title: 'Failover', icon: ServerCrash, color: 'text-red-500', value: 'Ready', desc: 'Standby mode' },
    { id: 25, title: 'System Logs', icon: LayoutDashboard, color: 'text-indigo-600', value: 'Streaming', desc: 'ELK Stack' }
  ];

  // We need to import Zap, but it's not imported. Let's add Zap to the import above.

  return (
    <div className="p-6 h-full flex flex-col bg-gray-50 overflow-y-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Admin Console</h1>
        <p className="text-gray-600">Mission Control - Backend & Infrastructure Management</p>
      </div>

      {/* Grid of 25 panels. The first panel will span 2 rows and 2 cols maybe, or just be a normal panel. */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">

        {/* Panel 1: Quota & API Usage (Span 2 rows if possible, or just be in a 2x2 grid depending on layout, we will just let it span col and row) */}
        <div className="col-span-1 sm:col-span-2 row-span-2">
          <QuotaApiMonitor />
        </div>

        {/* The other 24 panels */}
        {panels.map((panel) => (
          <div key={panel.id} className="bg-white p-4 rounded-lg shadow-sm border border-gray-100 flex flex-col justify-between hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between mb-2">
              <h3 className="font-medium text-gray-700 text-sm">{panel.title}</h3>
              <panel.icon size={18} className={panel.color} />
            </div>
            <div>
              <p className="text-xl font-bold text-gray-900">{panel.value}</p>
              <p className="text-xs text-gray-500 mt-1">{panel.desc}</p>
            </div>
          </div>
        ))}

      </div>
    </div>
  );
};
