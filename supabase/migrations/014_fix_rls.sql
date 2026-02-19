-- MIGRATION 014: FIX RLS POLICIES FOR FRONTEND ACCESS

-- 1. Enable RLS on tables (good practice, though we will open them up for now)
ALTER TABLE raw_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE extracted_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE file_relationships ENABLE ROW LEVEL SECURITY;

-- 2. Create "Allow All" policies for valid MVP usage (Frontend uses anon key)
-- In a real prod app, you'd restrict this to authenticated users.

-- raw_files
CREATE POLICY "Allow public insert" ON raw_files FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public select" ON raw_files FOR SELECT USING (true);
CREATE POLICY "Allow public update" ON raw_files FOR UPDATE USING (true);
CREATE POLICY "Allow public delete" ON raw_files FOR DELETE USING (true);

-- extracted_files
CREATE POLICY "Allow public select extracted" ON extracted_files FOR SELECT USING (true);
CREATE POLICY "Allow public insert extracted" ON extracted_files FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public update extracted" ON extracted_files FOR UPDATE USING (true);

-- relationships
CREATE POLICY "Allow public select relationships" ON relationships FOR SELECT USING (true);
CREATE POLICY "Allow public insert relationships" ON relationships FOR INSERT WITH CHECK (true);

-- file_relationships
CREATE POLICY "Allow public select file_rel" ON file_relationships FOR SELECT USING (true);
CREATE POLICY "Allow public insert file_rel" ON file_relationships FOR INSERT WITH CHECK (true);


-- 3. STORAGE POLICIES (Crucial for file upload)
-- Make sure the 'documents' bucket exists
INSERT INTO storage.buckets (id, name, public) 
VALUES ('documents', 'documents', true)
ON CONFLICT (id) DO NOTHING;

-- Allow public access to storage.objects for the 'documents' bucket
CREATE POLICY "Allow public upload" ON storage.objects
FOR INSERT WITH CHECK (bucket_id = 'documents');

CREATE POLICY "Allow public select" ON storage.objects
FOR SELECT USING (bucket_id = 'documents');

CREATE POLICY "Allow public update" ON storage.objects
FOR UPDATE USING (bucket_id = 'documents');
