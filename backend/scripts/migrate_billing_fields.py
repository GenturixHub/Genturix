#!/usr/bin/env python3
"""
GENTURIX - Billing Fields Migration Script
==========================================

Ensures all condominiums have the required billing fields.
Safe to run multiple times (idempotent).

Usage:
    cd /app/backend
    python scripts/migrate_billing_fields.py

Required fields and defaults:
    - billing_status: "active"
    - billing_cycle: "monthly"  
    - next_billing_date: 30 days from now
    - grace_period_days: 5
    - paid_seats: 50 (note: using paid_seats, not seat_limit for consistency)
    - active_users: 0 (note: using active_users for consistency with existing code)
    - balance_due: 0
    - total_paid_current_cycle: 0
    - next_invoice_amount: 0
"""

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

# Default values for billing fields
BILLING_DEFAULTS = {
    "billing_status": "active",
    "billing_cycle": "monthly",
    "grace_period_days": 5,
    "paid_seats": 50,
    "active_users": 0,
    "balance_due": 0,
    "total_paid_current_cycle": 0,
    "next_invoice_amount": 0,
    "price_per_seat": 2.99,  # Default price per seat
}

# Fields that should exist in every condominium
REQUIRED_FIELDS = [
    "billing_status",
    "billing_cycle", 
    "next_billing_date",
    "grace_period_days",
    "paid_seats",
    "active_users",
    "balance_due",
    "total_paid_current_cycle",
    "next_invoice_amount",
]


async def migrate_billing_fields():
    """
    Main migration function.
    Finds condominiums missing billing fields and sets defaults.
    """
    print("=" * 60)
    print("GENTURIX - Billing Fields Migration")
    print("=" * 60)
    print(f"\nConnecting to MongoDB: {MONGO_URL}")
    print(f"Database: {DB_NAME}")
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Statistics
    stats = {
        "total_condos": 0,
        "condos_updated": 0,
        "condos_skipped": 0,
        "fields_added": {},
        "errors": []
    }
    
    try:
        # Get all condominiums
        condos = await db.condominiums.find({}, {"_id": 0}).to_list(None)
        stats["total_condos"] = len(condos)
        
        print(f"\nFound {stats['total_condos']} condominiums to check\n")
        print("-" * 60)
        
        for condo in condos:
            condo_id = condo.get("id", "unknown")
            condo_name = condo.get("name", "Unknown")[:30]
            
            # Calculate next_billing_date default (30 days from now)
            default_next_billing = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
            
            # Check which fields are missing
            missing_fields = {}
            for field in REQUIRED_FIELDS:
                if field not in condo or condo[field] is None:
                    if field == "next_billing_date":
                        missing_fields[field] = default_next_billing
                    else:
                        missing_fields[field] = BILLING_DEFAULTS.get(field, None)
                    
                    # Track statistics
                    if field not in stats["fields_added"]:
                        stats["fields_added"][field] = 0
                    stats["fields_added"][field] += 1
            
            # Also check for price_per_seat (important for billing calculations)
            if "price_per_seat" not in condo or condo["price_per_seat"] is None:
                missing_fields["price_per_seat"] = BILLING_DEFAULTS["price_per_seat"]
                if "price_per_seat" not in stats["fields_added"]:
                    stats["fields_added"]["price_per_seat"] = 0
                stats["fields_added"]["price_per_seat"] += 1
            
            if missing_fields:
                # Update the condominium with missing fields
                try:
                    # Add updated_at timestamp
                    missing_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
                    missing_fields["billing_migration_date"] = datetime.now(timezone.utc).isoformat()
                    
                    result = await db.condominiums.update_one(
                        {"id": condo_id},
                        {"$set": missing_fields}
                    )
                    
                    if result.modified_count > 0:
                        stats["condos_updated"] += 1
                        print(f"✅ Updated: {condo_name}")
                        print(f"   Fields added: {list(missing_fields.keys())}")
                    else:
                        stats["condos_skipped"] += 1
                        print(f"⚠️  No changes: {condo_name}")
                        
                except Exception as e:
                    stats["errors"].append(f"{condo_name}: {str(e)}")
                    print(f"❌ Error updating {condo_name}: {e}")
            else:
                stats["condos_skipped"] += 1
                print(f"✓  Complete: {condo_name}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)
        print(f"\nTotal condominiums: {stats['total_condos']}")
        print(f"Updated: {stats['condos_updated']}")
        print(f"Already complete: {stats['condos_skipped']}")
        print(f"Errors: {len(stats['errors'])}")
        
        if stats["fields_added"]:
            print(f"\nFields added:")
            for field, count in stats["fields_added"].items():
                print(f"  - {field}: {count} condos")
        
        if stats["errors"]:
            print(f"\nErrors encountered:")
            for error in stats["errors"]:
                print(f"  - {error}")
        
        print("\n" + "=" * 60)
        
        # Verify migration
        print("\nVERIFICATION - Sample of migrated data:")
        print("-" * 60)
        
        sample = await db.condominiums.find(
            {"is_active": True},
            {"_id": 0, "name": 1, "billing_status": 1, "paid_seats": 1, "billing_cycle": 1}
        ).limit(5).to_list(5)
        
        for s in sample:
            print(f"  {s.get('name', '?')[:25]} | status: {s.get('billing_status', 'N/A')} | seats: {s.get('paid_seats', 'N/A')} | cycle: {s.get('billing_cycle', 'N/A')}")
        
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        client.close()
    
    return stats


async def verify_billing_fields():
    """
    Verify all condominiums have required billing fields.
    Returns list of condos with missing fields.
    """
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # Build query to find condos missing any required field
        or_conditions = []
        for field in REQUIRED_FIELDS:
            or_conditions.append({field: {"$exists": False}})
            or_conditions.append({field: None})
        
        missing = await db.condominiums.find(
            {"$or": or_conditions},
            {"_id": 0, "id": 1, "name": 1}
        ).to_list(None)
        
        return missing
    finally:
        client.close()


if __name__ == "__main__":
    print("\n🚀 Starting Billing Fields Migration...\n")
    
    # Run migration
    asyncio.run(migrate_billing_fields())
    
    # Verify
    print("\n📋 Post-migration verification...")
    missing = asyncio.run(verify_billing_fields())
    
    if missing:
        print(f"\n⚠️  {len(missing)} condominiums still have missing fields:")
        for m in missing[:10]:
            print(f"   - {m.get('name', 'Unknown')}")
    else:
        print("\n✅ All condominiums have complete billing fields!")
    
    print("\n🏁 Migration script finished.\n")
