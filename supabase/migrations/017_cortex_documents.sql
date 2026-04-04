CREATE TABLE cortex_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  original_filename TEXT NOT NULL,
  dataset_name TEXT NOT NULL,
  document_type TEXT CHECK (document_type IN ('RFQ', 'PO', 'Invoice', 'Sales', 'Client Data')),
  status TEXT NOT NULL DEFAULT 'processing' CHECK (status IN ('processing', 'completed', 'failed')),
  progress_stage TEXT NOT NULL DEFAULT 'uploading' CHECK (progress_stage IN (
    'uploading', 'ingesting', 'building_graph', 'analyzing', 'extracting_insights', 'completed', 'failed'
  )),
  summary TEXT,
  insights JSONB DEFAULT '[]',
  entities JSONB DEFAULT '[]',
  raw_chunks_count INTEGER DEFAULT 0,
  error_message TEXT,
  uploaded_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX idx_cortex_documents_status ON cortex_documents(status);
CREATE INDEX idx_cortex_documents_dataset ON cortex_documents(dataset_name);
CREATE INDEX idx_cortex_documents_uploaded ON cortex_documents(uploaded_at DESC);
