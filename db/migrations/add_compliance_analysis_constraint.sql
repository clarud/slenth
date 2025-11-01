-- Migration: Add Database Constraint for Compliance Analysis Guarantee
-- Purpose: Ensure every COMPLETED transaction has a ComplianceAnalysis record
-- Date: 2025-11-02

-- Step 1: Create function to check compliance analysis exists
CREATE OR REPLACE FUNCTION check_completed_transaction_has_compliance()
RETURNS TRIGGER AS $$
BEGIN
    -- Only check when status is being changed to COMPLETED
    IF NEW.status = 'completed' AND (OLD.status IS NULL OR OLD.status != 'completed') THEN
        -- Check if ComplianceAnalysis exists
        IF NOT EXISTS (
            SELECT 1 
            FROM compliance_analysis 
            WHERE transaction_id = NEW.id
        ) THEN
            RAISE EXCEPTION 'INTEGRITY VIOLATION: Cannot mark transaction % as COMPLETED without ComplianceAnalysis record', NEW.transaction_id;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Step 2: Create trigger on transactions table
DROP TRIGGER IF EXISTS enforce_compliance_analysis_on_complete ON transactions;

CREATE TRIGGER enforce_compliance_analysis_on_complete
    BEFORE UPDATE ON transactions
    FOR EACH ROW
    WHEN (NEW.status = 'completed')
    EXECUTE FUNCTION check_completed_transaction_has_compliance();

-- Step 3: Add comment for documentation
COMMENT ON FUNCTION check_completed_transaction_has_compliance() IS 
'Ensures that every transaction marked as COMPLETED has a corresponding ComplianceAnalysis record. This enforces the persistence guarantee at the database level.';

COMMENT ON TRIGGER enforce_compliance_analysis_on_complete ON transactions IS
'Database-level enforcement of the compliance analysis persistence guarantee. Prevents transactions from being marked COMPLETED without compliance analysis.';

-- Step 4: Verify existing data integrity
-- This query will show any COMPLETED transactions without compliance analysis
-- Run this before applying the trigger to identify any existing violations
DO $$
DECLARE
    violation_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO violation_count
    FROM transactions t
    LEFT JOIN compliance_analysis ca ON t.id = ca.transaction_id
    WHERE t.status = 'completed' AND ca.id IS NULL;
    
    IF violation_count > 0 THEN
        RAISE WARNING 'Found % COMPLETED transactions without ComplianceAnalysis. These must be fixed before the trigger will work properly.', violation_count;
    ELSE
        RAISE NOTICE 'All COMPLETED transactions have ComplianceAnalysis records. Migration can proceed safely.';
    END IF;
END $$;

-- Step 5: Query to find violations (for manual cleanup if needed)
-- Uncomment to see the problematic records:
/*
SELECT 
    t.transaction_id,
    t.status,
    t.processing_completed_at,
    CASE WHEN ca.id IS NULL THEN 'MISSING' ELSE 'EXISTS' END as compliance_analysis_status
FROM transactions t
LEFT JOIN compliance_analysis ca ON t.id = ca.transaction_id
WHERE t.status = 'completed' AND ca.id IS NULL;
*/
