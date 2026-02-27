"""
Users Module - Business Logic Service
======================================

Core seat management and user counting functions.
Migrated from server.py in Phase 2A.

Dependencies:
- db: MongoDB database instance (injected via _db)
- logger: Application logger (injected via _logger)
"""

from datetime import datetime, timezone
from typing import Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase

# ==================== MODULE STATE ====================
# These are set by server.py during startup
_db: Optional[AsyncIOMotorDatabase] = None
_logger = None


def set_db(db: AsyncIOMotorDatabase) -> None:
    """Set the database instance. Called by server.py during startup."""
    global _db
    _db = db


def set_logger(logger) -> None:
    """Set the logger instance. Called by server.py during startup."""
    global _logger
    _logger = logger


def get_db() -> AsyncIOMotorDatabase:
    """Get the database instance."""
    if _db is None:
        raise RuntimeError("Users service database not initialized. Call set_db() first.")
    return _db


def get_logger():
    """Get the logger instance."""
    return _logger


# ==================== SEAT ENGINE CORE FUNCTIONS ====================

async def count_active_users(condominium_id: str) -> int:
    """
    Count all active users in a condominium, excluding SuperAdmin.
    Uses both 'status' field and legacy 'is_active' for backward compatibility.
    
    Args:
        condominium_id: The condominium identifier
        
    Returns:
        Number of active users (excluding SuperAdmin)
    """
    db = get_db()
    count = await db.users.count_documents({
        "condominium_id": condominium_id,
        "roles": {"$not": {"$in": ["SuperAdmin"]}},
        "$or": [
            {"status": "active"},
            {"status": {"$exists": False}, "is_active": True}  # Backward compatibility
        ]
    })
    return count


async def count_active_residents(condominium_id: str) -> int:
    """
    Count only active RESIDENTS in a condominium (for seat management).
    This is the number that should be compared against paid_seats.
    
    Args:
        condominium_id: The condominium identifier
        
    Returns:
        Number of active residents
    """
    db = get_db()
    count = await db.users.count_documents({
        "condominium_id": condominium_id,
        "roles": {"$in": ["Residente"]},
        "$or": [
            {"status": "active"},
            {"status": {"$exists": False}, "is_active": True}
        ]
    })
    return count


async def update_active_user_count(condominium_id: str) -> Optional[int]:
    """
    Update the active_users count in the condominium document.
    Called after user creation, deletion, or status changes.
    
    Args:
        condominium_id: The condominium identifier
        
    Returns:
        The updated count, or None if condominium_id is empty
    """
    if not condominium_id:
        return None
    
    db = get_db()
    logger = get_logger()
    
    active_count = await count_active_users(condominium_id)
    await db.condominiums.update_one(
        {"id": condominium_id},
        {"$set": {"active_users": active_count, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if logger:
        logger.info(f"Updated active_users count for condo {condominium_id}: {active_count}")
    
    return active_count


async def can_create_user(condominium_id: str, role: str = "Residente") -> Tuple[bool, str]:
    """
    SEAT PROTECTION: Check if a new user can be created in the condominium.
    
    Validates:
    1. Condominium exists and is active
    2. Billing status allows user creation
    3. Seat limit for residents
    
    Args:
        condominium_id: The condominium identifier
        role: The role of the user being created (default: "Residente")
        
    Returns:
        Tuple of (can_create: bool, error_message: str)
    """
    if not condominium_id:
        return False, "Se requiere condominium_id"
    
    db = get_db()
    logger = get_logger()
    
    condo = await db.condominiums.find_one({"id": condominium_id}, {"_id": 0})
    if not condo:
        return False, "Condominio no encontrado"
    
    if not condo.get("is_active", True):
        return False, "El condominio está inactivo"
    
    # Check if demo condominium
    is_demo = condo.get("environment") == "demo" or condo.get("is_demo")
    
    # BILLING STATUS CHECK (only for production condos)
    if not is_demo:
        billing_status = condo.get("billing_status", "active")
        # Blocked statuses - cannot create any users
        blocked_statuses = ["suspended", "cancelled"]
        if billing_status in blocked_statuses:
            return False, f"Condominio suspendido ({billing_status}). Contacte soporte para regularizar su pago."
        
        # Warning statuses - can create but with warning
        warning_statuses = ["past_due"]
        if billing_status in warning_statuses:
            if logger:
                logger.warning(f"[SEAT-PROTECTION] Creating user in past_due condo {condominium_id[:8]}...")
    
    # SEAT LIMIT CHECK (applies to residents in both demo and production)
    if role == "Residente":
        paid_seats = 10 if is_demo else condo.get("paid_seats", 10)
        active_residents = await count_active_residents(condominium_id)
        
        if active_residents >= paid_seats:
            if is_demo:
                return False, f"Límite de asientos DEMO alcanzado ({active_residents}/{paid_seats}). Cree un condominio de producción para más usuarios."
            else:
                return False, f"Límite de asientos alcanzado ({active_residents}/{paid_seats}). Solicite más asientos para continuar."
    
    return True, ""
