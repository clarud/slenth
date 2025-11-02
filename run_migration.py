"""
Run database migration to add document-transaction linking
"""
import sys
from sqlalchemy import text
from db.database import engine

def run_migration():
    """Execute the migration SQL"""
    
    migration_sql = [
        # Add columns to documents table
        """
        ALTER TABLE documents 
        ADD COLUMN IF NOT EXISTS transaction_id VARCHAR(255),
        ADD COLUMN IF NOT EXISTS workflow_metadata JSONB
        """,
        
        # Create index
        """
        CREATE INDEX IF NOT EXISTS idx_documents_transaction_id ON documents(transaction_id)
        """,
        
        # Add columns to document_findings table
        """
        ALTER TABLE document_findings
        ADD COLUMN IF NOT EXISTS finding_details JSONB,
        ADD COLUMN IF NOT EXISTS detected_at TIMESTAMP DEFAULT NOW()
        """,
        
        # Update existing records
        """
        UPDATE document_findings 
        SET detected_at = created_at 
        WHERE detected_at IS NULL
        """
    ]
    
    try:
        with engine.connect() as conn:
            # Execute as a transaction
            with conn.begin():
                # Execute each statement
                for i, statement in enumerate(migration_sql, 1):
                    print(f"[{i}/{len(migration_sql)}] Executing: {statement.strip()[:60]}...")
                    conn.execute(text(statement))
                
                print("\n✅ Migration completed successfully!")
                
                # Verify changes
                print("\n📋 Verifying changes...")
                
                # Check documents table
                result = conn.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'documents' 
                    AND column_name IN ('transaction_id', 'workflow_metadata')
                    ORDER BY column_name
                """))
                
                print("\n   Documents table new columns:")
                for row in result:
                    print(f"      - {row[0]}: {row[1]}")
                
                # Check document_findings table
                result = conn.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'document_findings' 
                    AND column_name IN ('finding_details', 'detected_at')
                    ORDER BY column_name
                """))
                
                print("\n   Document_findings table new columns:")
                for row in result:
                    print(f"      - {row[0]}: {row[1]}")
                
                # Check indexes
                result = conn.execute(text("""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE tablename = 'documents' 
                    AND indexname = 'idx_documents_transaction_id'
                """))
                
                if result.fetchone():
                    print("\n   ✓ Index created: idx_documents_transaction_id")
                
                return True
                
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*80)
    print("DATABASE MIGRATION: Add Document-Transaction Linking")
    print("="*80)
    
    success = run_migration()
    
    if success:
        print("\n" + "="*80)
        print("Migration completed successfully! ✅")
        print("="*80)
        sys.exit(0)
    else:
        print("\n" + "="*80)
        print("Migration failed! ❌")
        print("="*80)
        sys.exit(1)
