"""
BILLING SCHEDULER MODULE
========================
APScheduler configuration and daily billing check logic.
Extracted from server.py without logic changes.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .service import (
    DEFAULT_GRACE_PERIOD_DAYS,
    send_billing_notification_email,
    check_and_log_email_sent,
    log_email_sent,
    log_billing_engine_event
)

# These will be set by the main app on initialization
db = None
logger = logging.getLogger(__name__)

# Global scheduler instance
billing_scheduler: Optional[AsyncIOScheduler] = None


def init_scheduler(database, log):
    """Initialize scheduler with dependencies from main app."""
    global db, logger
    db = database
    logger = log


async def process_billing_for_condominium(condo: dict, now: datetime, today_str: str) -> dict:
    """
    Process billing status for a single condominium.
    
    SUPPORTS PARTIAL PAYMENTS:
    - Checks balance_due field to determine if fully paid
    - Only transitions to active if balance_due <= 0
    - Maintains past_due if partial payments exist but balance > 0
    
    Returns a dict with processing results.
    """
    condo_id = condo.get("id")
    condo_name = condo.get("name", "Unknown")
    current_status = condo.get("billing_status", "active")
    next_billing_date_str = condo.get("next_billing_date")
    grace_period = condo.get("grace_period_days", DEFAULT_GRACE_PERIOD_DAYS)
    billing_email = condo.get("billing_email") or condo.get("admin_email") or condo.get("contact_email")
    next_invoice_amount = condo.get("next_invoice_amount", 0)
    paid_seats = condo.get("paid_seats", 10)
    balance_due = condo.get("balance_due", next_invoice_amount)  # Default to full invoice if not set
    total_paid_cycle = condo.get("total_paid_current_cycle", 0)
    
    result = {
        "condominium_id": condo_id,
        "name": condo_name,
        "previous_status": current_status,
        "new_status": current_status,
        "invoice_amount": next_invoice_amount,
        "total_paid_cycle": total_paid_cycle,
        "balance_due": balance_due,
        "action_taken": None,
        "email_sent": None,
        "error": None
    }
    
    # Skip if no billing date set
    if not next_billing_date_str:
        result["action_taken"] = "skipped_no_billing_date"
        return result
    
    # Parse billing date
    try:
        next_billing_date = datetime.fromisoformat(next_billing_date_str.replace("Z", "+00:00"))
        if next_billing_date.tzinfo is None:
            next_billing_date = next_billing_date.replace(tzinfo=timezone.utc)
    except Exception as e:
        result["error"] = f"Invalid billing date: {e}"
        return result
    
    # Calculate days until/since due
    days_diff = (now - next_billing_date).days
    days_until_due = -days_diff  # Positive if in future, negative if past
    
    due_date_formatted = next_billing_date.strftime("%d/%m/%Y")
    
    # ===== EMAIL REMINDERS (before due date) =====
    if current_status == "active":
        # 3 days before reminder
        if days_until_due == 3:
            if not await check_and_log_email_sent(condo_id, "reminder_3_days", today_str):
                if await send_billing_notification_email(
                    "reminder_3_days", billing_email, condo_name, 
                    next_invoice_amount, due_date_formatted, paid_seats
                ):
                    await log_email_sent(condo_id, "reminder_3_days", billing_email, today_str)
                    result["email_sent"] = "reminder_3_days"
        
        # Due today reminder
        elif days_until_due == 0:
            if not await check_and_log_email_sent(condo_id, "reminder_due_today", today_str):
                if await send_billing_notification_email(
                    "reminder_due_today", billing_email, condo_name,
                    next_invoice_amount, due_date_formatted, paid_seats
                ):
                    await log_email_sent(condo_id, "reminder_due_today", billing_email, today_str)
                    result["email_sent"] = "reminder_due_today"
    
    # ===== STATUS TRANSITIONS (after due date) =====
    if days_diff > 0:  # Past due date
        days_overdue = days_diff
        
        # Check if there's still balance due (partial payment scenario)
        has_balance_due = balance_due > 0
        
        if days_overdue <= grace_period:
            # Within grace period -> past_due (only if has balance)
            if has_balance_due and current_status not in ["past_due", "suspended"]:
                # Transition to past_due
                await db.condominiums.update_one(
                    {"id": condo_id},
                    {"$set": {
                        "billing_status": "past_due",
                        "updated_at": now.isoformat()
                    }}
                )
                result["new_status"] = "past_due"
                result["action_taken"] = "transitioned_to_past_due"
                
                # Log event
                await log_billing_engine_event(
                    event_type="auto_status_change",
                    condominium_id=condo_id,
                    data={
                        "from": current_status,
                        "to": "past_due",
                        "days_overdue": days_overdue,
                        "grace_period": grace_period,
                        "balance_due": balance_due,
                        "total_paid_cycle": total_paid_cycle,
                        "reason": "automatic_scheduler"
                    },
                    triggered_by="billing_scheduler",
                    previous_state={"billing_status": current_status, "balance_due": balance_due},
                    new_state={"billing_status": "past_due"}
                )
                
                # Send past_due email
                if not await check_and_log_email_sent(condo_id, "status_past_due", today_str):
                    if await send_billing_notification_email(
                        "status_past_due", billing_email, condo_name,
                        balance_due,  # Show remaining balance, not full invoice
                        due_date_formatted, paid_seats,
                        days_overdue, grace_period
                    ):
                        await log_email_sent(condo_id, "status_past_due", billing_email, today_str)
                        result["email_sent"] = "status_past_due"
            elif not has_balance_due:
                result["action_taken"] = "skipped_fully_paid"
        
        else:
            # Beyond grace period -> suspended (only if has balance)
            if has_balance_due and current_status != "suspended":
                # Transition to suspended
                await db.condominiums.update_one(
                    {"id": condo_id},
                    {"$set": {
                        "billing_status": "suspended",
                        "updated_at": now.isoformat()
                    }}
                )
                result["new_status"] = "suspended"
                result["action_taken"] = "transitioned_to_suspended"
                
                # Log event
                await log_billing_engine_event(
                    event_type="auto_status_change",
                    condominium_id=condo_id,
                    data={
                        "from": current_status,
                        "to": "suspended",
                        "days_overdue": days_overdue,
                        "grace_period": grace_period,
                        "balance_due": balance_due,
                        "total_paid_cycle": total_paid_cycle,
                        "reason": "automatic_scheduler_grace_exceeded"
                    },
                    triggered_by="billing_scheduler",
                    previous_state={"billing_status": current_status, "balance_due": balance_due},
                    new_state={"billing_status": "suspended"}
                )
                
                # Send suspended email
                if not await check_and_log_email_sent(condo_id, "status_suspended", today_str):
                    if await send_billing_notification_email(
                        "status_suspended", billing_email, condo_name,
                        balance_due,  # Show remaining balance
                        due_date_formatted, paid_seats,
                        days_overdue, grace_period
                    ):
                        await log_email_sent(condo_id, "status_suspended", billing_email, today_str)
                        result["email_sent"] = "status_suspended"
            elif not has_balance_due:
                result["action_taken"] = "skipped_fully_paid"
    
    return result


async def run_daily_billing_check():
    """
    Daily billing check job - runs at 2AM.
    Evaluates all active condominiums and transitions status as needed.
    """
    logger.info("[BILLING-SCHEDULER] Starting daily billing check...")
    
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    
    # Find condominiums to evaluate
    # Exclude: demo, already cancelled, and those without billing dates
    query = {
        "is_demo": {"$ne": True},
        "environment": {"$ne": "demo"},
        "billing_status": {"$in": ["active", "past_due", "upgrade_pending", "pending_payment"]},
        "next_billing_date": {"$ne": None}
    }
    
    condos = await db.condominiums.find(query, {"_id": 0}).to_list(5000)
    
    results = {
        "run_date": today_str,
        "run_time": now.isoformat(),
        "total_evaluated": len(condos),
        "transitioned_to_past_due": 0,
        "transitioned_to_suspended": 0,
        "emails_sent": 0,
        "errors": 0,
        "details": []
    }
    
    for condo in condos:
        try:
            result = await process_billing_for_condominium(condo, now, today_str)
            
            if result.get("action_taken") == "transitioned_to_past_due":
                results["transitioned_to_past_due"] += 1
            elif result.get("action_taken") == "transitioned_to_suspended":
                results["transitioned_to_suspended"] += 1
            
            if result.get("email_sent"):
                results["emails_sent"] += 1
            
            if result.get("error"):
                results["errors"] += 1
            
            results["details"].append(result)
            
        except Exception as e:
            logger.error(f"[BILLING-SCHEDULER] Error processing {condo.get('id')}: {e}")
            results["errors"] += 1
    
    # Log the run
    await db.billing_scheduler_runs.insert_one({
        "run_date": today_str,
        "run_time": now.isoformat(),
        "total_evaluated": results["total_evaluated"],
        "transitioned_to_past_due": results["transitioned_to_past_due"],
        "transitioned_to_suspended": results["transitioned_to_suspended"],
        "emails_sent": results["emails_sent"],
        "errors": results["errors"],
        "created_at": now.isoformat()
    })
    
    logger.info(
        f"[BILLING-SCHEDULER] Completed: {results['total_evaluated']} evaluated, "
        f"{results['transitioned_to_past_due']} -> past_due, "
        f"{results['transitioned_to_suspended']} -> suspended, "
        f"{results['emails_sent']} emails sent, {results['errors']} errors"
    )
    
    return results


def start_billing_scheduler():
    """Initialize and start the billing scheduler."""
    global billing_scheduler
    
    if billing_scheduler is not None:
        logger.warning("[BILLING-SCHEDULER] Scheduler already running")
        return
    
    billing_scheduler = AsyncIOScheduler(timezone="America/Costa_Rica")
    
    # Schedule daily job at 2AM Costa Rica time
    billing_scheduler.add_job(
        run_daily_billing_check,
        CronTrigger(hour=2, minute=0),
        id="daily_billing_check",
        name="Daily Billing Status Check",
        replace_existing=True
    )
    
    billing_scheduler.start()
    logger.info("[BILLING-SCHEDULER] Started - daily check scheduled for 2:00 AM Costa Rica time")


def stop_billing_scheduler():
    """Stop the billing scheduler."""
    global billing_scheduler
    
    if billing_scheduler:
        billing_scheduler.shutdown()
        billing_scheduler = None
        logger.info("[BILLING-SCHEDULER] Stopped")


def get_scheduler_instance():
    """Get the scheduler instance for status checks."""
    return billing_scheduler
