#!/usr/bin/env python3
"""
GENTURIX - Duplicate Email Detection Script
==========================================
Diagnostic tool to identify duplicate email addresses in the users collection.

This script:
- Groups users by email
- Detects emails with count > 1
- Logs duplicate entries with user IDs, names, and creation dates
- Does NOT delete or modify any data

Usage:
    cd /app/backend
    python scripts/detect_duplicate_emails.py
"""

import asyncio
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Load environment variables
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')


async def detect_duplicate_emails():
    """Detect and report duplicate emails in users collection."""
    
    print("=" * 70)
    print("GENTURIX - Duplicate Email Detection Report")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # Aggregation pipeline to find duplicate emails
        pipeline = [
            {
                "$group": {
                    "_id": "$email",
                    "count": {"$sum": 1},
                    "users": {
                        "$push": {
                            "id": "$id",
                            "full_name": "$full_name",
                            "roles": "$roles",
                            "is_active": "$is_active",
                            "status": "$status",
                            "condominium_id": "$condominium_id",
                            "created_at": "$created_at"
                        }
                    }
                }
            },
            {
                "$match": {
                    "count": {"$gt": 1}
                }
            },
            {
                "$sort": {
                    "count": -1
                }
            }
        ]
        
        duplicates = await db.users.aggregate(pipeline).to_list(None)
        
        # Get total user count
        total_users = await db.users.count_documents({})
        
        print(f"Total users in database: {total_users}")
        print(f"Duplicate email groups found: {len(duplicates)}")
        print()
        
        if not duplicates:
            print("[OK] No duplicate emails detected!")
            print()
            print("The unique index on 'email' field can be safely created.")
            return 0
        
        # Calculate total affected users
        total_affected = sum(d["count"] for d in duplicates)
        
        print(f"[WARNING] {total_affected} users affected by duplicates")
        print()
        print("-" * 70)
        print("DUPLICATE DETAILS")
        print("-" * 70)
        print()
        
        for i, dup in enumerate(duplicates, 1):
            email = dup["_id"]
            count = dup["count"]
            users = dup["users"]
            
            print(f"[{i}] Email: {email}")
            print(f"    Occurrences: {count}")
            print()
            
            for j, user in enumerate(users, 1):
                user_id = user.get("id", "N/A")
                full_name = user.get("full_name", "N/A")
                roles = user.get("roles", [])
                is_active = user.get("is_active", "N/A")
                status = user.get("status", "active")
                condo_id = user.get("condominium_id", "N/A")
                created_at = user.get("created_at", "N/A")
                
                # Truncate condo_id for display
                condo_display = condo_id[:8] + "..." if condo_id and len(str(condo_id)) > 8 else condo_id
                
                print(f"    User {j}:")
                print(f"      - ID: {user_id}")
                print(f"      - Name: {full_name}")
                print(f"      - Roles: {', '.join(roles) if roles else 'N/A'}")
                print(f"      - Active: {is_active}")
                print(f"      - Status: {status}")
                print(f"      - Condo: {condo_display}")
                print(f"      - Created: {created_at}")
                print()
            
            print("-" * 70)
            print()
        
        # Summary and recommendations
        print("=" * 70)
        print("SUMMARY & RECOMMENDATIONS")
        print("=" * 70)
        print()
        print(f"  - {len(duplicates)} email(s) have duplicates")
        print(f"  - {total_affected} total user records affected")
        print()
        print("To resolve duplicates, consider:")
        print("  1. Keep the most recent active user for each email")
        print("  2. Merge data from duplicates before deletion")
        print("  3. Deactivate or delete older/inactive duplicates")
        print()
        print("After cleanup, run this script again to verify.")
        print("Once clean, the unique index will be created automatically on next startup.")
        print()
        
        return len(duplicates)
        
    finally:
        client.close()


if __name__ == "__main__":
    result = asyncio.run(detect_duplicate_emails())
    exit(0 if result == 0 else 1)
