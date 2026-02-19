import React, { useState } from 'react';
import { supabase } from '../../config/supabase.config';
import { api } from '../../services/api';

export const FileUpload: React.FC<{ onUploadComplete: () => void }> = ({ onUploadComplete }) => {
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    try {
      setUploading(true);
      setMessage('');
      
      if (!event.target.files || event.target.files.length === 0) {
        return;
      }
      
      const file = event.target.files[0];
      const fileExt = file.name.split('.').pop();
      const fileName = `${Math.random().toString(36).substring(2)}.${fileExt}`;
      const filePath = `${fileName}`;

      // 1. Upload to Storage
      const { error: uploadError } = await supabase.storage
        .from('documents')
        .upload(filePath, file);

      if (uploadError) throw uploadError;

      // 2. Insert to raw_files
      // We generate UUID here or let DB do it. 
      // Architecture V3: raw_files defauts file_id to gen_random_uuid()
      // BUT we need the ID to call the API. So we should insert and select back OR generate one.
      // Let's rely on DB generation and select returned ID.
      
      const { data: rawFile, error: dbError } = await supabase
        .from('raw_files')
        .insert({
          file_name: file.name,
          file_link: `documents/${filePath}` // Storing path relative to bucket or full URL? Backend expects path or link.
          // backend/preprocess_service.py: pdf_bytes = await self.extraction_repo.download_file(file_link)
          // extraction_repo.py: path = file_path_or_link.split("/storage/v1/object/public/documents/")[-1]
          // So just passing the path inside 'documents' is safest if repo handles "documents" bucket logic.
        })
        .select()
        .single();

      if (dbError) throw dbError;
      
      if (!rawFile) throw new Error('Failed to create file record');

      // 3. Trigger Preprocessing
      setMessage(`Uploaded! Processing ${file.name}...`);
      // Cast rawFile to access file_id since TS doesn't know the shape
      if (rawFile) {
           await api.preprocess(rawFile.file_id);
      }
      
      setMessage('Processing started!');
      onUploadComplete();

    } catch (error: unknown) {
      console.error(error);
      const errMsg = error instanceof Error ? error.message : 'Unknown error';
      setMessage(`Error: ${errMsg}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="p-4 border-2 border-dashed border-zinc-700 bg-zinc-900 rounded-xl text-center hover:border-purple-500 hover:bg-zinc-800/50 transition-all cursor-pointer">
      <input
        type="file"
        id="file-upload"
        className="hidden"
        accept=".pdf,.csv"
        onChange={handleFileUpload}
        disabled={uploading}
      />
      <label 
        htmlFor="file-upload" 
        className={`cursor-pointer block p-6 ${uploading ? 'opacity-50' : ''}`}
      >
        {uploading ? (
          <span className="text-purple-400 font-semibold flex items-center justify-center gap-2">
            <svg className="animate-spin h-5 w-5 text-purple-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Uploading & Processing...
          </span>
        ) : (
          <div>
            <span className="text-zinc-300 text-lg font-medium">Click to Upload PDF or CSV</span>
            <p className="text-sm text-zinc-500 mt-2">Analyzes content, type, and relationships automatically.</p>
          </div>
        )}
      </label>
      {message && <div className="mt-4 p-2 bg-purple-900/20 rounded-lg text-sm font-medium text-purple-300 border border-purple-500/20">{message}</div>}
    </div>
  );
};
