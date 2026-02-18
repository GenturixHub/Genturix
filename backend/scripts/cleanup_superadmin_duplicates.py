#!/usr/bin/env python3
"""
GENTURIX - SuperAdmin Duplicate Cleanup Script
==============================================
Safely removes duplicate superadmin records after backup.

Steps:
1. Backup records to JSON
2. Log cleanup operation
3. Delete inactive duplicates
4. Verify single record remains
5. Create unique index on email
"""

import asyncio
import os
import json
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import uuid

# Load environment variables
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

# IDs to keep and delete
KEEP_ID = "1f0884cd-8121-419c-90a0-94dc556bf912"
DELETE_IDS = [
    "66739e50-ce06-4e24-8959-7d9f62681bc4",
    "a7dffc38-4943-4dd2-8641-22e7c085299e",
    "d5e6354f-8201-4a4a-a7e6-acae78eb5305",
    "36dbc952-6269-4864-834a-137acb7266dd",
    "0f162296-8cfd-4dac-9262-4389d1fae812",
    "73daa081-ce3e-4439-be79-65fc86be9e9b"
]

BACKUP_DIR = ROOT_DIR / "backups"


async def cleanup_superadmin_duplicates():
    """Execute the cleanup operation with backup and verification."""
    
    print("=" * 70)
    print("GENTURIX - SuperAdmin Duplicate Cleanup")
    print(f"Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # ================================================================
        # STEP 1: Create backup
        # ================================================================
        print("[STEP 1] Creating JSON backup of records to delete...")
        print()
        
        # Ensure backup directory exists
        BACKUP_DIR.mkdir(exist_ok=True)
        
        # Fetch records to delete
        records_to_delete = await db.users.find(
            {"id": {"$in": DELETE_IDS}},
            {"_id": 0}  # Exclude MongoDB _id for clean JSON
        ).to_list(None)
        
        if len(records_to_delete) != len(DELETE_IDS):
            found_ids = [r["id"] for r in records_to_delete]
            missing = set(DELETE_IDS) - set(found_ids)
            print(f"  [WARNING] Expected {len(DELETE_IDS)} records, found {len(records_to_delete)}")
            print(f"  Missing IDs: {missing}")
        
        # Create backup file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"superadmin_duplicates_backup_{timestamp}.json"
        backup_path = BACKUP_DIR / backup_filename
        
        backup_data = {
            "backup_timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": "SYSTEM_CLEANUP_SUPERADMIN_DUPLICATES",
            "kept_record_id": KEEP_ID,
            "deleted_count": len(records_to_delete),
            "records": records_to_delete
        }
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, default=str)
        
        print(f"  [OK] Backup created: {backup_path}")
        print(f"  [OK] Records backed up: {len(records_to_delete)}")
        print()
        
        # ================================================================
        # STEP 2: Log cleanup operation in audit_logs
        # ================================================================
        print("[STEP 2] Logging cleanup operation to audit_logs...")
        print()
        
        audit_entry = {
            "id": str(uuid.uuid4()),
            "event_type": "SYSTEM_CLEANUP_SUPERADMIN_DUPLICATES",
            "user_id": "SYSTEM",
            "resource": "users",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": {
                "action": "delete_duplicate_superadmin_records",
                "email": "superadmin@genturix.com",
                "kept_record_id": KEEP_ID,
                "deleted_record_ids": DELETE_IDS,
                "deleted_count": len(DELETE_IDS),
                "backup_file": str(backup_path),
                "reason": "Duplicate email cleanup to enable unique index"
            },
            "ip_address": "127.0.0.1",
            "user_agent": "cleanup_script/1.0"
        }
        
        await db.audit_logs.insert_one(audit_entry)
        print(f"  [OK] Audit log created with ID: {audit_entry['id']}")
        print()
        
        # ================================================================
        # STEP 3: Delete inactive records
        # ================================================================
        print("[STEP 3] Deleting inactive duplicate records...")
        print()
        
        delete_result = await db.users.delete_many({"id": {"$in": DELETE_IDS}})
        
        print(f"  [OK] Records deleted: {delete_result.deleted_count}")
        print()
        
        if delete_result.deleted_count != len(DELETE_IDS):
            print(f"  [WARNING] Expected to delete {len(DELETE_IDS)}, actually deleted {delete_result.deleted_count}")
        
        # ================================================================
        # STEP 4: Verify single record remains
        # ================================================================
        print("[STEP 4] Verifying single superadmin record remains...")
        print()
        
        remaining = await db.users.find(
            {"email": "superadmin@genturix.com"}
        ).to_list(None)
        
        if len(remaining) == 1:
            print(f"  [OK] Verification passed: 1 record remaining")
            print(f"  [OK] Remaining ID: {remaining[0]['id']}")
            if remaining[0]['id'] == KEEP_ID:
                print(f"  [OK] Correct record preserved")
            else:
                print(f"  [ERROR] Wrong record preserved! Expected {KEEP_ID}")
                return False
        else:
            print(f"  [ERROR] Verification failed: {len(remaining)} records found")
            for r in remaining:
                print(f"    - {r['id']}")
            return False
        
        print()
        
        # ================================================================
        # STEP 5: Create unique index on email
        # ================================================================
        print("[STEP 5] Creating unique index on users.email...")
        print()
        
        try:
            index_name = await db.users.create_index(
                "email",
                unique=True,
                background=True
            )
            print(f"  [OK] Unique index created: {index_name}")
        except Exception as e:
            error_code = getattr(e, 'code', None)
            if error_code == 85:
                print(f"  [OK] Index already exists (no action needed)")
            else:
                print(f"  [ERROR] Failed to create index: {e}")
                return False
        
        print()
        
        # ================================================================
        # Final Summary
        # ================================================================
        print("=" * 70)
        print("CLEANUP COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print()
        print(f"  Records deleted:    {delete_result.deleted_count}")
        print(f"  Record preserved:   {KEEP_ID}")
        print(f"  Backup location:    {backup_path}")
        print(f"  Unique index:       Created on users.email")
        print()
        print("The duplicate email issue has been resolved.")
        print("=" * 70)
        
        return True
        
    finally:
        client.close()


if __name__ == "__main__":
    success = asyncio.run(cleanup_superadmin_duplicates())
    exit(0 if success else 1)
