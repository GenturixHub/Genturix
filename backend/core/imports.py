"""GENTURIX Core — All Imports"""
# Trigger redeploy - 2026-03-01 SECURITY PATCH
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Request, Body, Query, UploadFile, File as FastAPIFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
import secrets
import string
import json
import hashlib
import re
import io
import random
import httpx
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import List, Optional, Dict, Any, Tuple
import uuid
from datetime import datetime, timezone, timedelta
from time import time as get_time
from zoneinfo import ZoneInfo
import bcrypt
import jwt
from enum import Enum
from bson import ObjectId

# ==================== SECURITY IMPORTS (2026-03-01) ====================
import bleach  # XSS protection via input sanitization
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest
import stripe  # For webhook signature verification
import resend
from pywebpush import webpush, WebPushException
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# ==================== BILLING MODULE IMPORTS (PHASE 3 - FULLY MODULARIZED) ====================
# All billing models, service functions, and scheduler are now imported from the module
from modules.billing.models import (
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
    SeatUpgradeRequest as BillingSeatUpgradeRequest,
    SeatUpdateRequest,
    BillingPreviewRequest,
    BillingPreviewResponse,
    BillingInfoResponse,
    SeatUsageResponse,
    SeatReductionValidation,
)

# Import service functions from billing module
from modules.billing.service import (
    DEFAULT_GRACE_PERIOD_DAYS,
    BILLING_EMAIL_TEMPLATES,
    init_service as init_billing_service,
    log_billing_engine_event,
    send_billing_notification_email,
    update_condominium_billing_status,
)

# Import scheduler functions from billing module
from modules.billing.scheduler import (
    init_scheduler as init_billing_scheduler,
    process_billing_for_condominium,
    run_daily_billing_check,
    start_billing_scheduler,
    stop_billing_scheduler,
    get_scheduler_instance,
)

# Import core seat engine functions from users module
from modules.users.service import (
    set_db as set_users_db,
    set_logger as set_users_logger,
    count_active_users,
    count_active_residents,
    update_active_user_count,
    can_create_user,
)

# Import user models from users module
from modules.users.models import (
    CreateUserByAdmin,
    CreateEmployeeByHR,
    UserStatusUpdateV2,
)

# Import centralized email service
from services.email_service import (
    send_email,
    send_email_sync,
    is_email_configured,
    get_email_status,
    get_sender,
    get_welcome_email_html,
    get_password_reset_email_html,
    get_emergency_alert_email_html,
    get_notification_email_html,
    get_condominium_welcome_email_html,
    get_visitor_preregistration_email_html,
    get_user_credentials_email_html,
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

