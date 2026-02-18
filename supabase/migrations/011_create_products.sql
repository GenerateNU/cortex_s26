-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create products table
CREATE TABLE IF NOT EXISTS products (
    id BIGSERIAL PRIMARY KEY,
    product_id TEXT UNIQUE,
    metadata JSONB,
    searchable_text TEXT NOT NULL,
    embedding vector(768) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create HNSW index for similarity search
CREATE INDEX IF NOT EXISTS products_embedding_idx
ON products
USING hnsw (embedding vector_ip_ops);

-- Create Hybrid Search Function
CREATE OR REPLACE FUNCTION match_products(
    query_embedding vector(768),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 20,
    filter_metadata jsonb DEFAULT '{}'
)
RETURNS TABLE (
    id bigint,
    product_id text,
    metadata jsonb,
    searchable_text text,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.product_id,
        p.metadata,
        p.searchable_text,
        (p.embedding <#> query_embedding) * -1 as similarity
    FROM products p
    WHERE 1 - (p.embedding <=> query_embedding) > match_threshold
    AND (filter_metadata = '{}'::jsonb OR p.metadata @> filter_metadata)
    ORDER BY p.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
