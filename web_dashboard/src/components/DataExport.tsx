import React from 'react';
import { Download, FileJson, FileText, Table } from 'lucide-react';

interface DataExportProps {
  data: any[];
  filename?: string;
  className?: string;
}

export const DataExport: React.FC<DataExportProps> = ({ data, filename = 'export', className = '' }) => {
  const downloadFile = (content: string, type: string, extension: string) => {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${filename}.${extension}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const exportCSV = () => {
    if (!data || !data.length) return;
    const headers = Object.keys(data[0]);
    const csvContent = [
      headers.join(','),
      ...data.map(row => headers.map(header => JSON.stringify(row[header] || '')).join(','))
    ].join('\n');
    downloadFile(csvContent, 'text/csv;charset=utf-8;', 'csv');
  };

  const exportJSON = () => {
    if (!data) return;
    downloadFile(JSON.stringify(data, null, 2), 'application/json', 'json');
  };

  const exportNDJSON = () => {
    if (!data || !data.length) return;
    const ndjsonContent = data.map(item => JSON.stringify(item)).join('\n');
    downloadFile(ndjsonContent, 'application/x-ndjson', 'ndjson');
  };

  const exportXML = () => {
    if (!data || !data.length) return;
    let xml = '<?xml version="1.0" encoding="UTF-8"?>\n<root>\n';
    data.forEach(item => {
      xml += '  <item>\n';
      Object.keys(item).forEach(key => {
        const val = item[key] !== null && item[key] !== undefined ? item[key] : '';
        xml += `    <${key}>${val}</${key}>\n`;
      });
      xml += '  </item>\n';
    });
    xml += '</root>';
    downloadFile(xml, 'application/xml', 'xml');
  };

  const exportPDF = () => {
    // For a simple PDF export without extra heavy libraries like jsPDF, 
    // we trigger the browser print dialog and the user can 'Save as PDF'.
    window.print();
  };

  return (
    <div className={`flex flex-wrap gap-2 ${className}`}>
      <button onClick={exportCSV} className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors shadow-sm">
        <Table className="w-4 h-4 text-blue-500" /> 
        <span>CSV</span>
      </button>
      <button onClick={exportJSON} className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors shadow-sm">
        <FileJson className="w-4 h-4 text-yellow-500" /> 
        <span>JSON</span>
      </button>
      <button onClick={exportNDJSON} className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors shadow-sm">
        <FileJson className="w-4 h-4 text-orange-500" /> 
        <span>NDJSON</span>
      </button>
      <button onClick={exportXML} className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors shadow-sm">
        <FileText className="w-4 h-4 text-purple-500" /> 
        <span>XML</span>
      </button>
      <button onClick={exportPDF} className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors shadow-sm">
        <Download className="w-4 h-4 text-red-500" /> 
        <span>PDF</span>
      </button>
    </div>
  );
};
