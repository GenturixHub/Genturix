#!/usr/bin/env python3
"""
MongoDB Index Creation Script
=============================
Creates strategic indexes for Genturix application performance.

Usage:
    python scripts/create_indexes.py

This script is idempotent - safe to run multiple times.
Indexes that already exist will be skipped.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment
load_dotenv(Path(__file__).parent.parent / '.env')

MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME', 'genturix')

if not MONGO_URL:
    print("ERROR: MONGO_URL not configured in .env")
    sys.exit(1)


async def create_indexes():
    """Create all strategic indexes."""
    print(f"Connecting to MongoDB: {DB_NAME}")
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Test connection
    try:
        await db.command("ping")
        print("✓ MongoDB connection successful")
    except Exception as e:
        print(f"✗ MongoDB connection failed: {e}")
        return
    
    indexes = [
        # ==================== BILLING (HIGH IMPACT) ====================
        {
            "collection": "billing_payments",
            "keys": [("condominium_id", 1), ("created_at", -1)],
            "options": {"background": True},
            "reason": "Optimizes payment history queries"
        },
        {
            "collection": "billing_events",
            "keys": [("condominium_id", 1), ("created_at", -1)],
            "options": {"background": True},
            "reason": "Optimizes audit trail queries"
        },
        {
            "collection": "condominiums",
            "keys": [("billing_status", 1)],
            "options": {"background": True},
            "reason": "Optimizes financial dashboard"
        },
        {
            "collection": "condominiums",
            "keys": [("id", 1)],
            "options": {"unique": True, "background": True},
            "reason": "Unique constraint on id field"
        },
        {
            "collection": "seat_upgrade_requests",
            "keys": [("condominium_id", 1), ("status", 1)],
            "options": {"background": True},
            "reason": "Optimizes upgrade request lookups"
        },
        {
            "collection": "billing_scheduler_runs",
            "keys": [("run_date", 1)],
            "options": {"background": True},
            "reason": "Optimizes scheduler history queries"
        },
        {
            "collection": "billing_email_log",
            "keys": [("condominium_id", 1), ("email_type", 1), ("sent_date", 1)],
            "options": {"background": True},
            "reason": "Optimizes email deduplication checks"
        },
        
        # ==================== GUARDS & SHIFTS ====================
        {
            "collection": "guards",
            "keys": [("condominium_id", 1)],
            "options": {"background": True},
            "reason": "Optimizes guard queries by condo"
        },
        {
            "collection": "shifts",
            "keys": [("condominium_id", 1), ("guard_id", 1)],
            "options": {"background": True},
            "reason": "Optimizes shift lookups"
        },
        {
            "collection": "shifts",
            "keys": [("condominium_id", 1), ("start_time", -1)],
            "options": {"background": True},
            "reason": "Optimizes shift history queries"
        },
        
        # ==================== USERS ====================
        {
            "collection": "users",
            "keys": [("email", 1)],
            "options": {"unique": True, "background": True},
            "reason": "Unique email constraint"
        },
        {
            "collection": "users",
            "keys": [("condominium_id", 1)],
            "options": {"background": True},
            "reason": "Optimizes user counts by condo"
        },
        
        # ==================== VISITS (PILOT CRITICAL) ====================
        {
            "collection": "visits",
            "keys": [("condominium_id", 1), ("created_at", -1)],
            "options": {"background": True},
            "reason": "Optimizes visit history queries by condo"
        },
        {
            "collection": "visits",
            "keys": [("resident_id", 1), ("status", 1)],
            "options": {"background": True},
            "reason": "Optimizes resident visit lookups"
        },
        {
            "collection": "visits",
            "keys": [("condominium_id", 1), ("status", 1), ("entry_at", -1)],
            "options": {"background": True},
            "reason": "Optimizes active visit queries"
        },
        
        # ==================== ALERTS (SECURITY CRITICAL) ====================
        {
            "collection": "alerts",
            "keys": [("condominium_id", 1), ("created_at", -1)],
            "options": {"background": True},
            "reason": "Optimizes alert history queries by condo"
        },
        {
            "collection": "alerts",
            "keys": [("type", 1), ("status", 1)],
            "options": {"background": True},
            "reason": "Optimizes alert filtering by type/status"
        },
        {
            "collection": "alerts",
            "keys": [("condominium_id", 1), ("acknowledged", 1)],
            "options": {"background": True},
            "reason": "Optimizes unacknowledged alert queries"
        },
    ]
    
    print(f"\nCreating {len(indexes)} indexes...\n")
    
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    for idx in indexes:
        collection_name = idx["collection"]
        keys = idx["keys"]
        options = idx["options"]
        reason = idx["reason"]
        
        collection = db[collection_name]
        
        # Convert keys to proper format
        if isinstance(keys, list):
            key_spec = keys
            key_str = str(keys)
        else:
            key_spec = keys
            key_str = str(keys)
        
        try:
            result = await collection.create_index(key_spec, **options)
            print(f"✓ {collection_name}.{key_str}")
            print(f"  → {reason}")
            print(f"  → Index name: {result}")
            success_count += 1
        except Exception as e:
            error_code = getattr(e, 'code', None)
            if error_code == 85:  # IndexOptionsConflict
                print(f"○ {collection_name}.{key_str} (already exists)")
                skip_count += 1
            elif error_code == 11000:  # DuplicateKey
                print(f"✗ {collection_name}.{key_str} - duplicate key error")
                fail_count += 1
            else:
                print(f"✗ {collection_name}.{key_str} - {e}")
                fail_count += 1
        
        print()
    
    print("=" * 50)
    print(f"SUMMARY:")
    print(f"  Created: {success_count}")
    print(f"  Skipped: {skip_count}")
    print(f"  Failed:  {fail_count}")
    print(f"  Total:   {len(indexes)}")
    print("=" * 50)
    
    client.close()


if __name__ == "__main__":
    asyncio.run(create_indexes())
