-- Migration: Add transaction_id and workflow_metadata to documents table
-- Description: Link documents to Part 1 transactions and store workflow results

-- Add transaction_id column to documents table
ALTER TABLE documents 
ADD COLUMN IF NOT EXISTS transaction_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS workflow_metadata JSONB;

-- Add foreign key constraint
ALTER TABLE documents
ADD CONSTRAINT fk_documents_transaction_id 
FOREIGN KEY (transaction_id) 
REFERENCES transactions(transaction_id) 
ON DELETE SET NULL;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_documents_transaction_id ON documents(transaction_id);

-- Add finding_details and detected_at to document_findings table
ALTER TABLE document_findings
ADD COLUMN IF NOT EXISTS finding_details JSONB,
ADD COLUMN IF NOT EXISTS detected_at TIMESTAMP DEFAULT NOW();

-- Update existing records to set detected_at = created_at if NULL
UPDATE document_findings 
SET detected_at = created_at 
WHERE detected_at IS NULL;

COMMENT ON COLUMN documents.transaction_id IS 'Links document to Part 1 transaction for corroboration';
COMMENT ON COLUMN documents.workflow_metadata IS 'Stores complete workflow state including all findings';
COMMENT ON COLUMN document_findings.finding_details IS 'Complete finding object from Part 2 workflow';
COMMENT ON COLUMN document_findings.detected_at IS 'Timestamp when finding was detected during workflow execution';
