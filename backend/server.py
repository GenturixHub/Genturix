"""
GENTURIX - Modular Server Entry Point
Assembles all routers from the routers/ package into the FastAPI app.
All shared state (db, models, helpers) lives in core/__init__.py.
"""
# Import the app and all shared dependencies from core
from core import (
    app, api_router, db, logger, client,
    CORSMiddleware, FRONTEND_URL, ENVIRONMENT,
    RESEND_API_KEY, SENDER_EMAIL,
    init_billing_service, init_billing_scheduler, start_billing_scheduler, stop_billing_scheduler,
    set_users_db, set_users_logger,
)

# Import ALL router modules
from routers import (
    auth, push, profile, security, visitors, guard, hr, admin,
    reservations, school, payments, audit, users, invitations,
    settings, condominiums, superadmin, casos, asamblea, finanzas,
    documentos, notifications_v2,
)

# ══════════════════════════════════════════════════════════════
# INCLUDE ALL ROUTERS (order matches original server.py)
# ══════════════════════════════════════════════════════════════
ALL_ROUTERS = [
    auth.router,
    push.router,
    profile.router,
    security.router,
    visitors.router,
    guard.router,
    hr.router,
    admin.router,
    reservations.router,
    school.router,
    payments.router,
    audit.router,
    users.router,
    invitations.router,
    settings.router,
    condominiums.router,
    superadmin.router,
    casos.router,
    asamblea.router,
    finanzas.router,
    documentos.router,
    notifications_v2.router,
]

for r in ALL_ROUTERS:
    api_router.include_router(r)

# Include the main api_router into the app
app.include_router(api_router)


# ══════════════════════════════════════════════════════════════
# CORS CONFIGURATION (must be AFTER all routers are included)
# ══════════════════════════════════════════════════════════════
def get_cors_origins() -> list:
    production_origins = [
        "https://genturix.com",
        "https://www.genturix.com",
        "https://app.genturix.com",
        "https://genturix.vercel.app",
    ]
    if FRONTEND_URL:
        frontend = FRONTEND_URL.rstrip('/')
        if frontend not in production_origins:
            production_origins.append(frontend)
    if ENVIRONMENT == "production":
        if not production_origins:
            logger.error("[CORS] CRITICAL: No production origins configured!")
        logger.info(f"[CORS] Production mode - allowing origins: {production_origins}")
        return production_origins
    else:
        dev_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
        all_origins = list(set(production_origins + dev_origins))
        logger.info(f"[CORS] Development mode - allowing origins: {all_origins}")
        return all_origins

cors_origins = get_cors_origins()
logger.info(f"[CORS] Environment: {ENVIRONMENT}, Allowed origins: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=cors_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "Accept"],
)


# ══════════════════════════════════════════════════════════════
# MONGODB INDEX INITIALIZATION
# ══════════════════════════════════════════════════════════════
async def initialize_indexes():
    async def safe_create_index(collection, keys, **kwargs):
        try:
            index_name = await collection.create_index(keys, **kwargs)
            return True, index_name
        except Exception as e:
            error_code = getattr(e, 'code', None)
            if error_code == 85:
                return True, "already exists"
            elif error_code == 11000:
                return False, "duplicate key error"
            return False, str(e)

    indexes_to_create = [
        (db.users, "email", {"unique": True, "background": True}),
        (db.users, "condominium_id", {"background": True}),
        (db.billing_payments, [("condominium_id", 1), ("created_at", -1)], {"background": True}),
        (db.billing_events, [("condominium_id", 1), ("created_at", -1)], {"background": True}),
        (db.condominiums, "billing_status", {"background": True}),
        (db.condominiums, "id", {"unique": True, "background": True}),
        (db.seat_upgrade_requests, [("condominium_id", 1), ("status", 1)], {"background": True}),
        (db.billing_scheduler_runs, "run_date", {"background": True}),
        (db.billing_email_log, [("condominium_id", 1), ("email_type", 1), ("sent_date", 1)], {"background": True}),
        (db.guards, "condominium_id", {"background": True}),
        (db.shifts, [("condominium_id", 1), ("guard_id", 1)], {"background": True}),
        (db.shifts, [("condominium_id", 1), ("start_time", -1)], {"background": True}),
        (db.push_subscriptions, [("user_id", 1), ("endpoint", 1)], {"unique": True, "background": True}),
        (db.push_subscriptions, "condominium_id", {"background": True}),
        (db.audit_logs, "user_id", {"background": True}),
        (db.audit_logs, "created_at", {"background": True, "expireAfterSeconds": 60*60*24*90}),
        (db.reservations, "condominium_id", {"background": True}),
        (db.reservations, "start_time", {"background": True}),
        (db.visitor_authorizations, "condominium_id", {"background": True}),
        (db.visitor_authorizations, "created_by", {"background": True}),
        (db.visitor_entries, "condominium_id", {"background": True}),
        (db.casos, "condominium_id", {"background": True}),
        (db.casos, "created_by", {"background": True}),
        (db.casos, "status", {"background": True}),
        (db.casos, "created_at", {"background": True}),
        (db.caso_comments, "caso_id", {"background": True}),
        (db.documents, "condominium_id", {"background": True}),
        (db.documents, "category", {"background": True}),
        (db.documents, "created_at", {"background": True}),
        (db.charges_catalog, "condominium_id", {"background": True}),
        (db.payment_records, "condominium_id", {"background": True}),
        (db.payment_records, "unit_id", {"background": True}),
        (db.payment_records, "status", {"background": True}),
        (db.payment_records, "period", {"background": True}),
        (db.unit_accounts, "condominium_id", {"background": True}),
        (db.unit_accounts, "unit_id", {"background": True}),
    ]

    success_count = 0
    for collection, keys, options in indexes_to_create:
        collection_name = collection.name
        success, result = await safe_create_index(collection, keys, **options)
        if success:
            logger.info(f"[DB-INDEX] {collection_name}.{keys}: {result}")
            success_count += 1
        else:
            logger.warning(f"[DB-INDEX] {collection_name}.{keys}: FAILED - {result}")
    logger.info(f"[DB-INDEX] Initialization complete: {success_count}/{len(indexes_to_create)} indexes ready")


# ══════════════════════════════════════════════════════════════
# STARTUP / SHUTDOWN
# ══════════════════════════════════════════════════════════════
@app.on_event("startup")
async def startup_event():
    try:
        await db.command("ping")
        logger.info("[STARTUP] MongoDB connection successful")
    except Exception as e:
        logger.error(f"[STARTUP] MongoDB connection FAILED: {e}")
        logger.warning("[STARTUP] App will start but DB features will be unavailable")
        return

    try:
        await initialize_indexes()
    except Exception as e:
        logger.error(f"[STARTUP] Index initialization failed: {e}")

    try:
        # ensure_global_pricing_config is in the payments module
        from routers.payments import ensure_global_pricing_config, YEARLY_DISCOUNT_PERCENT
        await ensure_global_pricing_config()
    except Exception as e:
        logger.error(f"[STARTUP] Global pricing config failed: {e}")

    try:
        from routers.payments import YEARLY_DISCOUNT_PERCENT as yd
        init_billing_service(
            database=db,
            resend_key=RESEND_API_KEY,
            sender_email=SENDER_EMAIL,
            yearly_discount=yd,
            log=logger
        )
        init_billing_scheduler(database=db, log=logger)
        logger.info("[STARTUP] Billing module initialized successfully")
    except Exception as e:
        logger.error(f"[STARTUP] Billing module initialization failed: {e}")

    try:
        set_users_db(db)
        set_users_logger(logger)
        logger.info("[STARTUP] Users module initialized successfully")
    except Exception as e:
        logger.error(f"[STARTUP] Users module initialization failed: {e}")

    try:
        start_billing_scheduler()
        logger.info("[STARTUP] Billing scheduler started successfully")
    except Exception as e:
        logger.error(f"[STARTUP] Billing scheduler failed to start: {e}")

    try:
        from routers.documentos import _init_doc_storage
        await _init_doc_storage()
        logger.info("[STARTUP] Document storage initialized successfully")
    except Exception as e:
        logger.warning(f"[STARTUP] Document storage init deferred: {e}")


@app.on_event("shutdown")
async def shutdown_db_client():
    stop_billing_scheduler()
    client.close()


# ══════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════
import uvicorn
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
