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
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Knowledge Base</h1>
        <Link to="/search" className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 transition">
          Semantic Search →
        </Link>
      </div>

      <div className="mb-8">
        <FileUpload onUploadComplete={handleRefresh} />
      </div>

      <div className="bg-gray-50 p-6 rounded-xl">
        <h2 className="text-xl font-semibold mb-4 text-gray-700">Recent Documents</h2>
        {/* Force re-render of list when upload completes */}
        <FileList key={refreshKey} />
      </div>
    </div>
  );
};
