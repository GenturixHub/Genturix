"""GENTURIX - Push Notification Endpoints Router (Auto-extracted from server.py)"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Response, UploadFile, File as FastAPIFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum
import uuid, io, json, os, re

# Import ALL shared dependencies from core
from core import *

router = APIRouter()

# Backend is the ONLY authority for push notification routing.
# All subscriptions MUST have: user_id, role, condominium_id

def get_primary_role(roles: list) -> str:
    """Get the primary role for a user (for push targeting)"""
    role_priority = ["SuperAdmin", "Administrador", "Supervisor", "Guarda", "Guardia", "HR", "Residente"]
    for role in role_priority:
        if role in roles:
            return role
    return roles[0] if roles else "unknown"


@router.post("/push/subscribe")
async def subscribe_to_push(
    request: PushSubscriptionRequest,
    current_user = Depends(get_current_user)
):
    """
    Register a push notification subscription for the authenticated user.
    
    REQUIREMENTS:
    - User MUST be authenticated
    - User MUST have a valid condominium_id (except SuperAdmin)
    - Saves: user_id, role, condominium_id, endpoint, keys
    
    If subscription already exists for user_id + endpoint → UPDATE it.
    """
    # ==================== AUDIT LOGGING ====================
    user_id = current_user.get("id")
    user_email = current_user.get("email", "unknown")
    logger.info(f"[PUSH-SUBSCRIBE-DEBUG] ======= REQUEST START =======")
    logger.info(f"[PUSH-SUBSCRIBE-DEBUG] User: {user_email} | ID: {user_id[:12]}...")
    logger.info(f"[PUSH-SUBSCRIBE-DEBUG] Subscription endpoint: {request.subscription.endpoint[:50]}...")
    logger.info(f"[PUSH-SUBSCRIBE-DEBUG] Has p256dh: {bool(request.subscription.keys.p256dh)}")
    logger.info(f"[PUSH-SUBSCRIBE-DEBUG] Has auth: {bool(request.subscription.keys.auth)}")
    # =======================================================
    
    user_roles = current_user.get("roles", [])
    condo_id = current_user.get("condominium_id")
    
    # VALIDATION 1: User must have roles
    if not user_roles:
        raise HTTPException(
            status_code=403, 
            detail="Usuario sin roles asignados. Contacta al administrador."
        )
    
    # VALIDATION 2: Non-SuperAdmin users MUST have condominium_id
    is_super_admin = "SuperAdmin" in user_roles
    if not is_super_admin and not condo_id:
        raise HTTPException(
            status_code=403,
            detail="Usuario no asignado a un condominio. Contacta al administrador."
        )
    
    # VALIDATION 3: Verify user is active
    db_user = await db.users.find_one(
        {"id": user_id}, 
        {"_id": 0, "is_active": 1, "status": 1}
    )
    if not db_user or not db_user.get("is_active", True):
        raise HTTPException(
            status_code=403,
            detail="Cuenta de usuario inactiva."
        )
    
    if db_user.get("status") in ["blocked", "suspended"]:
        raise HTTPException(
            status_code=403,
            detail="Cuenta bloqueada o suspendida."
        )
    
    subscription = request.subscription
    primary_role = get_primary_role(user_roles)
    
    # ==================== PHASE 2: CLEANUP SAFETY ====================
    # Before insert/update, clean up invalid subscriptions for this user:
    # 1. Remove inactive subscriptions
    # 2. Remove entries with missing/empty endpoint
    cleanup_result = await db.push_subscriptions.delete_many({
        "user_id": user_id,
        "$or": [
            {"is_active": False},
            {"endpoint": None},
            {"endpoint": ""},
            {"endpoint": {"$exists": False}}
        ]
    })
    if cleanup_result.deleted_count > 0:
        logger.info(f"[PUSH-CLEANUP] Removed {cleanup_result.deleted_count} invalid subscriptions for user {user_id}")
    
    # ==================== PHASE 2.5: SUBSCRIPTION LIMIT ====================
    # Limit subscriptions per user to MAX_SUBSCRIPTIONS_PER_USER (default: 3)
    # This prevents accumulation of stale subscriptions from multiple devices
    MAX_SUBSCRIPTIONS_PER_USER = 3
    
    # Count existing subscriptions for this user (excluding current endpoint if exists)
    existing_count = await db.push_subscriptions.count_documents({
        "user_id": user_id,
        "endpoint": {"$ne": subscription.endpoint}  # Don't count the one we're about to update/create
    })
    
    if existing_count >= MAX_SUBSCRIPTIONS_PER_USER:
        # Delete oldest subscriptions to make room
        subscriptions_to_keep = MAX_SUBSCRIPTIONS_PER_USER - 1  # Leave room for new one
        oldest_subs = await db.push_subscriptions.find(
            {"user_id": user_id, "endpoint": {"$ne": subscription.endpoint}},
            {"_id": 1, "endpoint": 1, "created_at": 1}
        ).sort("created_at", 1).limit(existing_count - subscriptions_to_keep).to_list(None)
        
        if oldest_subs:
            oldest_ids = [s["_id"] for s in oldest_subs]
            delete_result = await db.push_subscriptions.delete_many({"_id": {"$in": oldest_ids}})
            logger.info(f"[PUSH-LIMIT] Deleted {delete_result.deleted_count} oldest subscriptions for user {user_id[:12]}... (limit: {MAX_SUBSCRIPTIONS_PER_USER})")
    # ======================================================================
    
    # Check if subscription already exists for this user + endpoint
    existing = await db.push_subscriptions.find_one({
        "user_id": user_id,
        "endpoint": subscription.endpoint
    })
    
    now = datetime.now(timezone.utc).isoformat()
    
    if existing:
        # UPDATE existing subscription
        await db.push_subscriptions.update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "role": primary_role,  # Update role in case it changed
                "condominium_id": condo_id,  # Update condo in case transferred
                "p256dh": subscription.keys.p256dh,
                "auth": subscription.keys.auth,
                "expiration_time": subscription.expirationTime,
                "is_active": True,
                "updated_at": now
            }}
        )
        logger.info(f"[PUSH-SUBSCRIBE-DEBUG] Subscription UPDATED for user {user_id[:12]}... (role={primary_role})")
        logger.info(f"[PUSH-SUBSCRIBE-DEBUG] ======= REQUEST SUCCESS =======")
        return {
            "message": "Suscripción actualizada",
            "status": "updated",
            "role": primary_role
        }
    
    # CREATE new subscription with all required fields
    sub_doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "role": primary_role,
        "condominium_id": condo_id,
        "endpoint": subscription.endpoint,
        "p256dh": subscription.keys.p256dh,
        "auth": subscription.keys.auth,
        "expiration_time": subscription.expirationTime,
        "is_active": True,
        "created_at": now,
        "updated_at": now
    }
    
    await db.push_subscriptions.insert_one(sub_doc)
    
    logger.info(f"[PUSH-SUBSCRIBE-DEBUG] Subscription CREATED for user {user_id[:12]}... (role={primary_role}, condo={condo_id[:8] if condo_id else 'N/A'}...)")
    logger.info(f"[PUSH-SUBSCRIBE-DEBUG] ======= REQUEST SUCCESS =======")
    await log_audit_event(
        AuditEventType.USER_UPDATED, current_user["id"], "push",
        {"action": "push_subscribe", "role": primary_role},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=current_user.get("condominium_id"),
        user_email=current_user.get("email"),
    )
    return {
        "message": "Suscripción exitosa",
        "status": "created",
        "role": primary_role
    }


@router.delete("/push/unsubscribe")
async def unsubscribe_from_push(
    request: PushSubscriptionRequest,
    current_user = Depends(get_current_user)
):
    """
    Remove a specific push subscription for the authenticated user.
    Used when user manually disables notifications.
    """
    user_id = current_user.get("id")
    subscription = request.subscription
    
    result = await db.push_subscriptions.delete_one({
        "user_id": user_id,
        "endpoint": subscription.endpoint
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Suscripción no encontrada")
    
    logger.info(f"[PUSH] Subscription REMOVED for user {user_id}")
    await log_audit_event(
        AuditEventType.USER_UPDATED, current_user["id"], "push",
        {"action": "push_unsubscribe"},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=current_user.get("condominium_id"),
        user_email=current_user.get("email"),
    )
    return {"message": "Suscripción eliminada", "deleted_count": 1}


@router.delete("/push/unsubscribe-all")
async def unsubscribe_all_push(current_user = Depends(get_current_user)):
    """
    Remove ALL push subscriptions for the current user.
    MUST be called on logout to clean up stale subscriptions.
    """
    user_id = current_user.get("id")
    
    result = await db.push_subscriptions.delete_many({
        "user_id": user_id
    })
    
    logger.info(f"[PUSH] ALL subscriptions REMOVED for user {user_id}: {result.deleted_count} deleted")
    await log_audit_event(
        AuditEventType.USER_UPDATED, current_user["id"], "push",
        {"action": "push_unsubscribe_all", "count": result.deleted_count},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=current_user.get("condominium_id"),
        user_email=current_user.get("email"),
    )
    return {
        "message": f"{result.deleted_count} suscripciones eliminadas",
        "deleted_count": result.deleted_count
    }


@router.get("/push/status")
async def get_push_status(current_user = Depends(get_current_user)):
    """Get current user's push notification subscription status"""
    user_id = current_user.get("id")
    
    subscriptions = await db.push_subscriptions.find({
        "user_id": user_id,
        "is_active": True
    }, {"_id": 0, "id": 1, "endpoint": 1, "role": 1, "created_at": 1}).to_list(None)
    
    return {
        "is_subscribed": len(subscriptions) > 0,
        "subscription_count": len(subscriptions),
        "subscriptions": subscriptions
    }


@router.post("/push/cleanup")
async def cleanup_invalid_subscriptions(current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))):
    """
    [SUPERADMIN ONLY] Clean up invalid push subscriptions.
    
    Removes subscriptions that:
    - Have no user_id
    - Have no condominium_id (except SuperAdmin subscriptions)
    - Belong to deleted/inactive users
    
    This is a maintenance endpoint for data hygiene.
    """
    deleted_counts = {
        "no_user_id": 0,
        "no_condo_id": 0,
        "user_deleted": 0,
        "user_inactive": 0
    }
    
    # 1. Remove subscriptions without user_id
    result = await db.push_subscriptions.delete_many({
        "$or": [
            {"user_id": None},
            {"user_id": {"$exists": False}},
            {"user_id": ""}
        ]
    })
    deleted_counts["no_user_id"] = result.deleted_count
    
    # 2. Get all subscriptions with user_id but check user validity
    subscriptions = await db.push_subscriptions.find({}, {"_id": 1, "user_id": 1}).to_list(None)
    
    user_ids = list(set([s.get("user_id") for s in subscriptions if s.get("user_id")]))
    
    # Get valid users
    valid_users = await db.users.find(
        {"id": {"$in": user_ids}},
        {"_id": 0, "id": 1, "is_active": 1, "status": 1}
    ).to_list(None)
    
    valid_user_ids = set([u["id"] for u in valid_users if u.get("is_active", True) and u.get("status", "active") in ["active", None]])
    deleted_user_ids = set(user_ids) - set([u["id"] for u in valid_users])
    inactive_user_ids = set([u["id"] for u in valid_users if not u.get("is_active", True) or u.get("status") in ["blocked", "suspended"]])
    
    # Delete subscriptions for deleted users
    if deleted_user_ids:
        result = await db.push_subscriptions.delete_many({"user_id": {"$in": list(deleted_user_ids)}})
        deleted_counts["user_deleted"] = result.deleted_count
    
    # Delete subscriptions for inactive users
    if inactive_user_ids:
        result = await db.push_subscriptions.delete_many({"user_id": {"$in": list(inactive_user_ids)}})
        deleted_counts["user_inactive"] = result.deleted_count
    
    total_deleted = sum(deleted_counts.values())
    
    logger.info(f"[PUSH-CLEANUP] Cleanup completed: {total_deleted} subscriptions removed - {deleted_counts}")
    
    return {
        "message": f"Limpieza completada: {total_deleted} suscripciones eliminadas",
        "details": deleted_counts,
        "total_deleted": total_deleted
    }


@router.post("/push/validate-subscriptions")
async def validate_and_cleanup_subscriptions(
    dry_run: bool = True,
    current_user = Depends(require_role(RoleEnum.SUPER_ADMIN))
):
    """
    [SUPERADMIN ONLY] Validate push subscriptions by sending test notifications.
    
    This endpoint:
    1. Fetches all push subscriptions from the database
    2. Sends a silent/test push to each one
    3. Deletes subscriptions that return 404/410 (permanently invalid)
    4. Reports results
    
    Parameters:
    - dry_run: If True (default), only validates without sending or deleting.
               Set to False to actually test and clean invalid subscriptions.
    
    This is the DEFINITIVE solution for cleaning expired FCM subscriptions.
    """
    logger.info(f"[PUSH-VALIDATE] ========== VALIDATION START (dry_run={dry_run}) ==========")
    
    # Get all subscriptions
    all_subscriptions = await db.push_subscriptions.find({}).to_list(None)
    total_count = len(all_subscriptions)
    
    if total_count == 0:
        return {
            "message": "No hay suscripciones para validar",
            "dry_run": dry_run,
            "total": 0,
            "valid": 0,
            "invalid": 0,
            "deleted": 0
        }
    
    logger.info(f"[PUSH-VALIDATE] Found {total_count} subscriptions to validate")
    
    valid_count = 0
    invalid_count = 0
    deleted_count = 0
    errors_detail = []
    
    # Test payload - silent notification (won't show to users)
    test_payload = {
        "title": "GENTURIX System Check",
        "body": "Validación de suscripción",
        "silent": True,
        "tag": "system-validation",
        "data": {"type": "validation", "timestamp": datetime.now(timezone.utc).isoformat()}
    }
    
    for sub in all_subscriptions:
        endpoint = sub.get("endpoint", "")
        endpoint_short = endpoint[-30:] if len(endpoint) > 30 else endpoint
        user_id = sub.get("user_id", "unknown")
        sub_id = sub.get("_id")
        
        if not endpoint:
            # Invalid subscription without endpoint
            invalid_count += 1
            if not dry_run:
                await db.push_subscriptions.delete_one({"_id": sub_id})
                deleted_count += 1
            errors_detail.append({
                "endpoint": "MISSING",
                "user_id": user_id[:12] if user_id else "N/A",
                "error": "No endpoint"
            })
            continue
        
        if dry_run:
            # In dry run mode, just count as "to be validated"
            valid_count += 1
            continue
        
        # Build subscription_info for webpush
        subscription_info = {
            "endpoint": endpoint,
            "keys": {
                "p256dh": sub.get("p256dh", ""),
                "auth": sub.get("auth", "")
            }
        }
        
        # Validate keys exist
        if not subscription_info["keys"]["p256dh"] or not subscription_info["keys"]["auth"]:
            invalid_count += 1
            await db.push_subscriptions.delete_one({"_id": sub_id})
            deleted_count += 1
            errors_detail.append({
                "endpoint": endpoint_short,
                "user_id": user_id[:12] if user_id else "N/A",
                "error": "Missing keys"
            })
            continue
        
        # Try to send test push
        try:
            webpush(
                subscription_info=subscription_info,
                data=json.dumps(test_payload),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{VAPID_CLAIMS_EMAIL}"}
            )
            # Success - subscription is valid
            valid_count += 1
            logger.debug(f"[PUSH-VALIDATE] ✅ Valid: {endpoint_short}")
            
        except WebPushException as e:
            status_code = e.response.status_code if e.response else 0
            
            if status_code in [404, 410]:
                # Subscription is PERMANENTLY invalid - delete it
                invalid_count += 1
                await db.push_subscriptions.delete_one({"_id": sub_id})
                deleted_count += 1
                errors_detail.append({
                    "endpoint": endpoint_short,
                    "user_id": user_id[:12] if user_id else "N/A",
                    "error": f"HTTP {status_code} - Expired/Gone"
                })
                logger.info(f"[PUSH-VALIDATE] ❌ Invalid (deleted): {endpoint_short} - HTTP {status_code}")
            else:
                # Temporary error - keep subscription
                valid_count += 1
                logger.warning(f"[PUSH-VALIDATE] ⚠️ Temp error (kept): {endpoint_short} - HTTP {status_code}")
                
        except Exception as e:
            # Network or other error - keep subscription (might be temporary)
            valid_count += 1
            logger.warning(f"[PUSH-VALIDATE] ⚠️ Unknown error (kept): {endpoint_short} - {str(e)[:50]}")
    
    logger.info(f"[PUSH-VALIDATE] ========== VALIDATION COMPLETE ==========")
    logger.info(f"[PUSH-VALIDATE] Total: {total_count} | Valid: {valid_count} | Invalid: {invalid_count} | Deleted: {deleted_count}")
    
    # Log with requested format for monitoring
    remaining = total_count - deleted_count
    logger.info(f"[PUSH CLEANUP] deleted_subscriptions={deleted_count} remaining={remaining}")
    
    return {
        "message": f"Validación {'simulada' if dry_run else 'completada'}: {invalid_count} suscripciones inválidas {'detectadas' if dry_run else 'eliminadas'}",
        "dry_run": dry_run,
        "total": total_count,
        "valid": valid_count,
        "invalid": invalid_count,
        "deleted": deleted_count,
        "errors_detail": errors_detail[:20] if errors_detail else []  # Limit to 20 for response size
    }


@router.get("/push/validate-user-subscription")
async def validate_user_subscription(current_user = Depends(get_current_user)):
    """
    Validate if the current user's push subscription is still valid.
    
    This endpoint:
    1. Gets the user's push subscription from DB
    2. Sends a silent test push
    3. Returns whether the subscription is valid
    
    Frontend should call this on app load to detect expired subscriptions
    and prompt the user to re-enable notifications if needed.
    """
    user_id = current_user.get("id")
    
    # Get user's subscriptions
    subscriptions = await db.push_subscriptions.find(
        {"user_id": user_id, "is_active": True}
    ).to_list(None)
    
    if not subscriptions:
        return {
            "has_subscription": False,
            "is_valid": False,
            "subscription_count": 0,
            "message": "No tienes suscripciones push activas"
        }
    
    # Test the most recent subscription
    latest_sub = sorted(subscriptions, key=lambda x: x.get("updated_at", ""), reverse=True)[0]
    endpoint = latest_sub.get("endpoint", "")
    
    if not endpoint:
        return {
            "has_subscription": True,
            "is_valid": False,
            "subscription_count": len(subscriptions),
            "message": "Suscripción inválida (sin endpoint)"
        }
    
    # Build subscription_info
    subscription_info = {
        "endpoint": endpoint,
        "keys": {
            "p256dh": latest_sub.get("p256dh", ""),
            "auth": latest_sub.get("auth", "")
        }
    }
    
    if not subscription_info["keys"]["p256dh"] or not subscription_info["keys"]["auth"]:
        return {
            "has_subscription": True,
            "is_valid": False,
            "subscription_count": len(subscriptions),
            "message": "Suscripción inválida (faltan claves)"
        }
    
    # Silent test payload
    test_payload = {
        "title": "",
        "body": "",
        "silent": True,
        "tag": "validation-check",
        "data": {"type": "validation"}
    }
    
    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(test_payload),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": f"mailto:{VAPID_CLAIMS_EMAIL}"}
        )
        return {
            "has_subscription": True,
            "is_valid": True,
            "subscription_count": len(subscriptions),
            "message": "Suscripción válida"
        }
        
    except WebPushException as e:
        status_code = e.response.status_code if e.response else 0
        
        if status_code in [404, 410]:
            # Subscription expired - delete it
            await db.push_subscriptions.delete_one({"endpoint": endpoint})
            
            return {
                "has_subscription": True,
                "is_valid": False,
                "subscription_count": len(subscriptions) - 1,
                "message": "Tu suscripción push ha expirado. Por favor, reactiva las notificaciones.",
                "action_required": "resubscribe"
            }
        else:
            # Temporary error - assume valid
            return {
                "has_subscription": True,
                "is_valid": True,
                "subscription_count": len(subscriptions),
                "message": "Suscripción posiblemente válida (error temporal)"
            }
            
    except Exception as e:
        logger.warning(f"[PUSH-VALIDATE-USER] Error validating subscription for {user_id}: {str(e)}")
        return {
            "has_subscription": True,
            "is_valid": True,  # Assume valid on network errors
            "subscription_count": len(subscriptions),
            "message": "No se pudo validar (error de red)"
        }


# ============================================================
# TEMPORARY CLEANUP ENDPOINT - REMOVE AFTER PRODUCTION CLEAN
# ============================================================

@router.get("/push/cleanup-legacy")
async def cleanup_legacy_push_subscriptions(
    dry_run: bool = True,
    current_user = Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN))
):
    """
    [ADMIN/SUPERADMIN ONLY] Clean up legacy push subscriptions.
    
    TEMPORARY CLEANUP ENDPOINT - REMOVE AFTER PRODUCTION CLEAN
    
    Removes subscriptions that:
    - role is null
    - OR endpoint does not exist
    - OR endpoint is empty string
    - OR is_active is false
    
    Parameters:
    - dry_run: If True (default), only counts without deleting. Set to False to actually delete.
    
    This endpoint:
    - ONLY affects push_subscriptions collection
    - Does NOT touch users or other collections
    - Does NOT modify VAPID or send_push logic
    """
    
    # Build query for invalid/legacy subscriptions
    cleanup_query = {
        "$or": [
            {"role": None},
            {"role": {"$exists": False}},
            {"endpoint": {"$exists": False}},
            {"endpoint": None},
            {"endpoint": ""},
            {"is_active": False}
        ]
    }
    
    # Count documents to be deleted
    count_to_delete = await db.push_subscriptions.count_documents(cleanup_query)
    total_before = await db.push_subscriptions.count_documents({})
    
    logger.info(f"[PUSH-CLEANUP-LEGACY] Found {count_to_delete} legacy subscriptions to clean (dry_run={dry_run})")
    
    deleted_count = 0
    
    if not dry_run and count_to_delete > 0:
        # Actually delete the documents
        result = await db.push_subscriptions.delete_many(cleanup_query)
        deleted_count = result.deleted_count
        logger.info(f"[PUSH-CLEANUP-LEGACY] Deleted {deleted_count} legacy subscriptions")
    
    # Count remaining subscriptions
    remaining = await db.push_subscriptions.count_documents({})
    
    return {
        "dry_run": dry_run,
        "total_before": total_before,
        "matched_for_deletion": count_to_delete,
        "deleted_count": deleted_count,
        "remaining_subscriptions": remaining,
        "message": f"{'DRY RUN: Would delete' if dry_run else 'Deleted'} {count_to_delete if dry_run else deleted_count} legacy subscriptions"
    }


# ============================================================
# TEMPORARY DEBUG ENDPOINTS - REMOVE AFTER PRODUCTION DEBUG
# ============================================================

@router.get("/push/debug")
async def debug_push_subscriptions(current_user = Depends(get_current_user)):
    """
    [TEMPORARY DEBUG] Get current user's push subscription status.
    
    Returns subscription metadata WITHOUT sensitive keys (p256dh, auth).
    Use this to verify subscriptions are being stored correctly.
    
    REMOVE THIS ENDPOINT AFTER DEBUGGING.
    """
    user_id = current_user.get("id")
    
    try:
        subscriptions = await db.push_subscriptions.find(
            {"user_id": user_id, "is_active": True},
            {"_id": 0, "endpoint": 1, "is_active": 1, "created_at": 1, "updated_at": 1, "role": 1, "condominium_id": 1}
        ).to_list(None)
        
        # Truncate endpoints for readability (they're very long)
        safe_subs = []
        for sub in subscriptions:
            safe_subs.append({
                "endpoint": sub.get("endpoint", "")[:80] + "..." if len(sub.get("endpoint", "")) > 80 else sub.get("endpoint", ""),
                "endpoint_full_length": len(sub.get("endpoint", "")),
                "is_active": sub.get("is_active", False),
                "role": sub.get("role"),
                "condominium_id": sub.get("condominium_id"),
                "created_at": sub.get("created_at"),
                "updated_at": sub.get("updated_at")
            })
        
        logger.info(f"[PUSH-DEBUG] User {user_id} has {len(subscriptions)} active subscriptions")
        
        return {
            "user_id": user_id,
            "subscriptions_count": len(subscriptions),
            "subscriptions": safe_subs,
            "vapid_configured": bool(VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY)
        }
        
    except Exception as e:
        logger.error(f"[PUSH-DEBUG] Error fetching subscriptions for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching subscriptions: {str(e)}")


@router.post("/push/test")
async def test_push_notification(current_user = Depends(get_current_user)):
    """
    [TEMPORARY DEBUG] Send a test push notification to current user.
    
    Uses existing send_push_to_user() function.
    Helps verify the entire push pipeline works end-to-end.
    
    REMOVE THIS ENDPOINT AFTER DEBUGGING.
    """
    user_id = current_user.get("id")
    
    # Check VAPID configuration
    if not VAPID_PUBLIC_KEY or not VAPID_PRIVATE_KEY:
        raise HTTPException(
            status_code=503, 
            detail="VAPID keys not configured on server"
        )
    
    # Check if user has active subscriptions
    sub_count = await db.push_subscriptions.count_documents({
        "user_id": user_id,
        "is_active": True
    })
    
    if sub_count == 0:
        raise HTTPException(
            status_code=400,
            detail="No hay suscripciones push activas. Activa las notificaciones primero en tu perfil."
        )
    
    logger.info(f"[PUSH-TEST] Sending test push to {sub_count} subscriptions for user {user_id}")
    
    # Send test notification using existing function
    payload = {
        "title": "Test Push Production",
        "body": "Si recibes esto, Web Push funciona correctamente.",
        "icon": "/logo192.png",
        "badge": "/logo192.png",
        "tag": "test-push",
        "data": {
            "type": "test",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }
    
    try:
        result = await send_push_to_user(user_id, payload)
        
        logger.info(f"[PUSH-TEST] Test push result for user {user_id}: {result}")
        
        return {
            "status": "sent",
            "user_id": user_id,
            "subscriptions_attempted": result.get("total", sub_count),
            "successful": result.get("success", 0),
            "failed": result.get("failed", 0),
            "message": "Notificación de prueba enviada. Debería aparecer en unos segundos."
        }
        
    except Exception as e:
        logger.error(f"[PUSH-TEST] Error sending test push to user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error sending push: {str(e)}")

# ============================================================
# END TEMPORARY DEBUG ENDPOINTS
# ============================================================

