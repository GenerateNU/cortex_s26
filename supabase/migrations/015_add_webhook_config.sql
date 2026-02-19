-- -----------------------------------------------------------------------------
-- MIGRATION 015: RESTORE WEBHOOK CONFIGURATION
-- -----------------------------------------------------------------------------
-- Purpose:
-- Restore the webhook_config table and the update_webhook_config function
-- which were lost in previous migrations but are required by the backend.
-- -----------------------------------------------------------------------------

-- 1. Create Table
CREATE TABLE IF NOT EXISTS webhook_config (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. RLS Policies
ALTER TABLE webhook_config ENABLE ROW LEVEL SECURITY;

-- Allow service role (and potentially others) full access
CREATE POLICY "Allow full access to webhook_config" 
ON webhook_config 
FOR ALL 
USING (true) 
WITH CHECK (true);

-- 3. Function
CREATE OR REPLACE FUNCTION update_webhook_config(url text, secret text)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    INSERT INTO webhook_config (key, value)
    VALUES 
        ('webhook_url', url),
        ('webhook_secret', secret)
    ON CONFLICT (key) 
    DO UPDATE SET 
        value = EXCLUDED.value,
        updated_at = NOW();
END;
$$;
