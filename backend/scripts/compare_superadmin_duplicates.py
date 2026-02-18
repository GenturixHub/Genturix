#!/usr/bin/env python3
"""
GENTURIX - SuperAdmin Duplicate Comparison Report
=================================================
Detailed diagnostic comparing all duplicate superadmin records.

This script analyzes each duplicate record and shows:
- Basic user info
- Activity metrics (last login, password changes)
- Related entities (audit logs, condominiums created, etc.)

Does NOT modify any data.
"""

import asyncio
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from collections import defaultdict

# Load environment variables
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')


async def analyze_superadmin_duplicates():
    """Generate detailed comparison report for duplicate superadmin records."""
    
    print("=" * 80)
    print("GENTURIX - SuperAdmin Duplicate Comparison Report")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # Find all superadmin@genturix.com users
        superadmins = await db.users.find(
            {"email": "superadmin@genturix.com"}
        ).sort("created_at", 1).to_list(None)
        
        print(f"Found {len(superadmins)} records with email: superadmin@genturix.com")
        print()
        
        if len(superadmins) <= 1:
            print("[OK] No duplicates to compare.")
            return
        
        # Collect detailed info for each record
        records_analysis = []
        
        for user in superadmins:
            user_id = user.get("id")
            
            # Count audit logs by this user
            audit_count = await db.audit_logs.count_documents({"user_id": user_id})
            
            # Get audit log types breakdown
            audit_types = await db.audit_logs.aggregate([
                {"$match": {"user_id": user_id}},
                {"$group": {"_id": "$event_type", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]).to_list(None)
            
            # Count condominiums created by this user
            condos_created = await db.condominiums.count_documents({"created_by": user_id})
            
            # Get list of condominiums created
            condos_list = await db.condominiums.find(
                {"created_by": user_id},
                {"_id": 0, "id": 1, "name": 1, "created_at": 1, "is_active": 1}
            ).to_list(None)
            
            # Count users created by this superadmin
            users_created = await db.users.count_documents({"created_by": user_id})
            
            # Check for any push subscriptions
            push_subs = await db.push_subscriptions.count_documents({"user_id": user_id})
            
            # Check billing transactions
            billing_count = await db.billing_transactions.count_documents({"user_id": user_id})
            
            # Get last audit log timestamp
            last_audit = await db.audit_logs.find_one(
                {"user_id": user_id},
                sort=[("timestamp", -1)]
            )
            last_audit_time = last_audit.get("timestamp") if last_audit else None
            last_audit_type = last_audit.get("event_type") if last_audit else None
            
            # Check for login events specifically
            login_events = await db.audit_logs.count_documents({
                "user_id": user_id,
                "event_type": {"$in": ["login_success", "LOGIN_SUCCESS"]}
            })
            
            records_analysis.append({
                "id": user_id,
                "full_name": user.get("full_name"),
                "created_at": user.get("created_at"),
                "updated_at": user.get("updated_at"),
                "last_login_at": user.get("last_login_at"),
                "password_changed_at": user.get("password_changed_at"),
                "status": user.get("status", "active"),
                "is_active": user.get("is_active"),
                "roles": user.get("roles", []),
                "audit_count": audit_count,
                "audit_types": audit_types,
                "login_events": login_events,
                "last_audit_time": last_audit_time,
                "last_audit_type": last_audit_type,
                "condos_created": condos_created,
                "condos_list": condos_list,
                "users_created": users_created,
                "push_subscriptions": push_subs,
                "billing_transactions": billing_count
            })
        
        # Print detailed comparison
        print("-" * 80)
        print("DETAILED RECORD COMPARISON")
        print("-" * 80)
        print()
        
        for i, record in enumerate(records_analysis, 1):
            print(f"{'='*80}")
            print(f"RECORD #{i}")
            print(f"{'='*80}")
            print()
            print(f"  ID:                  {record['id']}")
            print(f"  Full Name:           {record['full_name']}")
            print(f"  Roles:               {', '.join(record['roles'])}")
            print(f"  Status:              {record['status']}")
            print(f"  Is Active:           {record['is_active']}")
            print()
            print("  TIMESTAMPS:")
            print(f"    Created At:        {record['created_at'] or 'N/A'}")
            print(f"    Updated At:        {record['updated_at'] or 'N/A'}")
            print(f"    Last Login At:     {record['last_login_at'] or 'N/A'}")
            print(f"    Password Changed:  {record['password_changed_at'] or 'N/A'}")
            print()
            print("  ACTIVITY METRICS:")
            print(f"    Total Audit Logs:  {record['audit_count']}")
            print(f"    Login Events:      {record['login_events']}")
            print(f"    Last Activity:     {record['last_audit_time'] or 'N/A'}")
            print(f"    Last Action Type:  {record['last_audit_type'] or 'N/A'}")
            print()
            print("  RELATED ENTITIES:")
            print(f"    Condos Created:    {record['condos_created']}")
            print(f"    Users Created:     {record['users_created']}")
            print(f"    Push Subscriptions: {record['push_subscriptions']}")
            print(f"    Billing Txns:      {record['billing_transactions']}")
            
            if record['condos_list']:
                print()
                print("    Condominiums Created:")
                for condo in record['condos_list']:
                    status = "Active" if condo.get('is_active') else "Inactive"
                    print(f"      - {condo.get('name', 'N/A')} ({status})")
                    print(f"        ID: {condo.get('id', 'N/A')[:20]}...")
            
            if record['audit_types']:
                print()
                print("    Top Audit Event Types:")
                for at in record['audit_types'][:5]:
                    print(f"      - {at['_id']}: {at['count']}")
            
            print()
        
        # Summary comparison table
        print("=" * 80)
        print("SUMMARY COMPARISON TABLE")
        print("=" * 80)
        print()
        print(f"{'#':<3} {'ID (short)':<12} {'Created':<12} {'Logins':<8} {'Audits':<8} {'Condos':<8} {'Users':<8}")
        print("-" * 80)
        
        for i, record in enumerate(records_analysis, 1):
            id_short = record['id'][:10] + ".."
            created = record['created_at'][:10] if record['created_at'] else "N/A"
            print(f"{i:<3} {id_short:<12} {created:<12} {record['login_events']:<8} {record['audit_count']:<8} {record['condos_created']:<8} {record['users_created']:<8}")
        
        print()
        
        # Recommendation
        print("=" * 80)
        print("ANALYSIS & RECOMMENDATION")
        print("=" * 80)
        print()
        
        # Find the record with most activity
        most_active = max(records_analysis, key=lambda x: (
            x['audit_count'],
            x['condos_created'],
            x['users_created'],
            x['login_events']
        ))
        
        # Find the most recently created
        most_recent = max(records_analysis, key=lambda x: x['created_at'] or '')
        
        # Find records with no activity
        inactive_records = [r for r in records_analysis if r['audit_count'] == 0 and r['condos_created'] == 0]
        
        print(f"Most Active Record (by audit logs):")
        print(f"  ID: {most_active['id']}")
        print(f"  Audit Logs: {most_active['audit_count']}, Condos: {most_active['condos_created']}, Users: {most_active['users_created']}")
        print()
        
        print(f"Most Recently Created:")
        print(f"  ID: {most_recent['id']}")
        print(f"  Created: {most_recent['created_at']}")
        print()
        
        print(f"Records with NO activity: {len(inactive_records)}")
        for r in inactive_records:
            print(f"  - {r['id']} (created: {r['created_at'][:10] if r['created_at'] else 'N/A'})")
        print()
        
        # Determine recommendation
        if most_active['audit_count'] > 0:
            recommended_keep = most_active['id']
            reason = "highest activity (audit logs)"
        else:
            recommended_keep = most_recent['id']
            reason = "most recently created (no activity on any)"
        
        to_delete = [r['id'] for r in records_analysis if r['id'] != recommended_keep]
        
        print("-" * 80)
        print("RECOMMENDATION:")
        print("-" * 80)
        print()
        print(f"  KEEP:   {recommended_keep}")
        print(f"  Reason: {reason}")
        print()
        print(f"  DELETE ({len(to_delete)} records):")
        for del_id in to_delete:
            rec = next(r for r in records_analysis if r['id'] == del_id)
            print(f"    - {del_id}")
            print(f"      (audits: {rec['audit_count']}, condos: {rec['condos_created']}, users: {rec['users_created']})")
        print()
        
        print("=" * 80)
        print("IMPORTANT: Review the above carefully before proceeding with deletion.")
        print("Related audit logs and other entities may need reassignment.")
        print("=" * 80)
        
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(analyze_superadmin_duplicates())
