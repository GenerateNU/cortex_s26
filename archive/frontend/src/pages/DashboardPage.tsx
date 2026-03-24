import React, { useState } from 'react';
import { FileUpload } from '../components/common/FileUpload';
import { FileList } from '../components/common/FileList';
import { Link } from 'react-router-dom';

export const DashboardPage: React.FC = () => {
  const [refreshKey, setRefreshKey] = useState(0);

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
  };

  return (
    <div className="max-w-4xl w-full mx-auto p-6 flex-1 overflow-y-auto min-h-0">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-zinc-100">Knowledge Base</h1>
        <Link to="/search" className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 transition-colors shadow-sm">
          Semantic Search →
        </Link>
      </div>

      <div className="mb-8 p-6 bg-zinc-900 rounded-xl border border-zinc-800 shadow-lg">
        <FileUpload onUploadComplete={handleRefresh} />
      </div>

      <div className="bg-zinc-900 p-6 rounded-xl border border-zinc-800 shadow-lg">
        <h2 className="text-xl font-semibold mb-4 text-zinc-200">Recent Documents</h2>
        {/* Force re-render of list when upload completes */}
        <FileList key={refreshKey} />
      </div>
    </div>
  );
};
