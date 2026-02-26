"""
BILLING MODULE
==============
Modular billing system for Genturix.
Extracted from server.py for better maintainability.

This module contains:
- models.py: Pydantic models and enums
- service.py: Core billing logic functions
- scheduler.py: APScheduler configuration
- router.py: API endpoints (TODO: migrate from server.py)
"""

from .models import (
    BillingStatus,
    BillingCycle,
    BillingProvider,
    BillingEventType,
    SeatUpgradeRequestStatus,
    ConfirmPaymentRequest,
    ConfirmPaymentResponse,
    PaymentHistoryResponse,
    SeatUpgradeRequestModel,
    SeatUpgradeRequestResponse,
    SeatUpgradeRequest,
    SeatUpdateRequest,
    BillingPreviewRequest,
    BillingPreviewResponse,
    BillingInfoResponse,
    SeatUsageResponse,
    SeatReductionValidation
)

from .service import (
    DEFAULT_GRACE_PERIOD_DAYS,
    BILLING_EMAIL_TEMPLATES,
    init_service,
    send_billing_notification_email,
    check_and_log_email_sent,
    log_email_sent,
    log_billing_engine_event,
    update_condominium_billing_status
)

from .scheduler import (
    init_scheduler,
    process_billing_for_condominium,
    run_daily_billing_check,
    start_billing_scheduler,
    stop_billing_scheduler,
    get_scheduler_instance
)

__all__ = [
    # Models
    'BillingStatus',
    'BillingCycle',
    'BillingProvider',
    'BillingEventType',
    'SeatUpgradeRequestStatus',
    'ConfirmPaymentRequest',
    'ConfirmPaymentResponse',
    'PaymentHistoryResponse',
    'SeatUpgradeRequestModel',
    'SeatUpgradeRequestResponse',
    'SeatUpgradeRequest',
    'SeatUpdateRequest',
    'BillingPreviewRequest',
    'BillingPreviewResponse',
    'BillingInfoResponse',
    'SeatUsageResponse',
    'SeatReductionValidation',
    # Service
    'DEFAULT_GRACE_PERIOD_DAYS',
    'BILLING_EMAIL_TEMPLATES',
    'init_service',
    'send_billing_notification_email',
    'check_and_log_email_sent',
    'log_email_sent',
    'log_billing_engine_event',
    'update_condominium_billing_status',
    # Scheduler
    'init_scheduler',
    'process_billing_for_condominium',
    'run_daily_billing_check',
    'start_billing_scheduler',
    'stop_billing_scheduler',
    'get_scheduler_instance'
]
