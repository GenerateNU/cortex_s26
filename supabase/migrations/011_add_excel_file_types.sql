-- Add Excel file types to file_type enum for existing databases
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_enum
    WHERE enumlabel = 'xlsx'
      AND enumtypid = 'file_type'::regtype
  ) THEN
    ALTER TYPE file_type ADD VALUE 'xlsx';
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_enum
    WHERE enumlabel = 'xls'
      AND enumtypid = 'file_type'::regtype
  ) THEN
    ALTER TYPE file_type ADD VALUE 'xls';
  END IF;
END $$;
