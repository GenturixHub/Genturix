"""GENTURIX - Audit + Dashboard Router (Auto-extracted from server.py)"""
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

@router.get("/audit/logs")
async def get_audit_logs(
    module: Optional[str] = None,
    event_type: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user = Depends(require_module("audit"))
):
    """
    Get audit logs - TENANT ISOLATED.
    
    - SuperAdmin: sees ALL logs from all condominiums
    - Administrador: sees ONLY logs from their condominium
    - Other roles: access denied
    """
    roles = current_user.get("roles", [])
    
    # Verify role
    if not any(role in roles for role in ["Administrador", "SuperAdmin"]):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    query = {}
    
    # CRITICAL: Multi-tenant isolation
    # SuperAdmin sees all, others see ONLY their condominium
    if "SuperAdmin" not in roles:
        condo_id = current_user.get("condominium_id")
        if condo_id:
            query["condominium_id"] = condo_id
        else:
            # No condominium assigned - return empty
            return []
    
    if module:
        query["module"] = module
    if event_type:
        query["event_type"] = event_type
    if user_id:
        query["user_id"] = user_id
    
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(500)
    return logs

@router.get("/audit/stats")
async def get_audit_stats(current_user = Depends(require_module("audit"))):
    """
    Get audit statistics - TENANT ISOLATED.
    
    - SuperAdmin: sees global stats
    - Administrador: sees ONLY stats from their condominium
    """
    roles = current_user.get("roles", [])
    
    # Verify role
    if not any(role in roles for role in ["Administrador", "SuperAdmin"]):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    # Build tenant filter
    base_query = {}
    if "SuperAdmin" not in roles:
        condo_id = current_user.get("condominium_id")
        if condo_id:
            base_query["condominium_id"] = condo_id
        else:
            return {
                "total_events": 0,
                "today_events": 0,
                "login_failures": 0,
                "panic_events": 0
            }
    
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    
    total_events = await db.audit_logs.count_documents(base_query)
    today_events = await db.audit_logs.count_documents({**base_query, "timestamp": {"$gte": today_start}})
    login_failures = await db.audit_logs.count_documents({**base_query, "event_type": "login_failure"})
    panic_events = await db.audit_logs.count_documents({**base_query, "event_type": "panic_button"})
    
    return {
        "total_events": total_events,
        "today_events": today_events,
        "login_failures": login_failures,
        "panic_events": panic_events
    }

@router.get("/audit/export")
async def export_audit_logs_pdf(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    event_type: Optional[str] = None,
    current_user = Depends(require_module("audit"))
):
    """
    Export audit logs as PDF file.
    - Requires Administrador or SuperAdmin role
    - Applies tenant filtering (multi-tenant safe)
    - Returns direct PDF download
    """
    # Verify role
    roles = current_user.get("roles", [])
    if not any(role in roles for role in ["Administrador", "SuperAdmin"]):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    # Build query - SuperAdmin sees all, others see their condo
    condo_id = current_user.get("condominium_id")
    query = {}
    
    # CRITICAL: Apply strict tenant filter
    # SuperAdmin sees all, others see ONLY their condo (no system logs)
    if "SuperAdmin" not in roles:
        if condo_id:
            query["condominium_id"] = condo_id
        else:
            # No condominium assigned - return empty PDF
            raise HTTPException(status_code=403, detail="No tiene condominio asignado")
    
    # Apply date filters (timestamp field is ISO string)
    if from_date:
        try:
            # Validate date format
            datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            query["timestamp"] = query.get("timestamp", {})
            query["timestamp"]["$gte"] = from_date
        except ValueError:
            pass
    
    if to_date:
        try:
            # Validate date format
            datetime.fromisoformat(to_date.replace('Z', '+00:00'))
            query["timestamp"] = query.get("timestamp", {})
            query["timestamp"]["$lte"] = to_date
        except ValueError:
            pass
    
    # Apply event type filter
    if event_type:
        query["event_type"] = event_type
    
    # DIAGNOSTIC LOG
    logger.info(f"[AUDIT-EXPORT] Query filter: {query}")
    
    # Fetch logs (max 1000 to avoid huge PDFs)
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(1000)
    
    # DIAGNOSTIC LOG
    logger.info(f"[AUDIT-EXPORT] Total logs encontrados: {len(logs)}")
    
    # Get condominium name for the header
    condo_name = "Todos los Condominios"
    if condo_id:
        condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "name": 1})
        if condo:
            condo_name = condo.get("name", "Condominio")
    elif "SuperAdmin" in roles:
        condo_name = "Todos los Condominios (SuperAdmin)"
    
    # Generate PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=6,
        alignment=TA_CENTER
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    # Build content
    elements = []
    
    # Title
    elements.append(Paragraph("GENTURIX - Reporte de Auditoría", title_style))
    
    # Subtitle with date and condo
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    subtitle_text = f"Condominio: {condo_name}<br/>Fecha de generación: {now_str}"
    if from_date or to_date:
        date_range = f"Período: {from_date or 'Inicio'} a {to_date or 'Ahora'}"
        subtitle_text += f"<br/>{date_range}"
    elements.append(Paragraph(subtitle_text, subtitle_style))
    
    elements.append(Spacer(1, 12))
    
    if logs:
        # Pre-fetch user names for all user_ids in logs
        user_ids = list(set(log.get("user_id") for log in logs if log.get("user_id")))
        users_map = {}
        if user_ids:
            users = await db.users.find(
                {"id": {"$in": user_ids}}, 
                {"_id": 0, "id": 1, "full_name": 1, "email": 1}
            ).to_list(None)
            users_map = {u["id"]: u.get("full_name") or u.get("email", "Usuario") for u in users}
        
        # Table header
        table_data = [["Fecha", "Usuario", "Evento", "Módulo", "IP"]]
        
        # Table rows
        for log in logs:
            # Format timestamp
            timestamp = log.get("timestamp", "")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    timestamp = dt.strftime("%Y-%m-%d %H:%M")
                except Exception as fmt_err:
                    logger.debug(f"[AUDIT] Timestamp format error: {fmt_err}")
                    timestamp = str(timestamp)[:16]
            
            # Get user name from pre-fetched map or fallback
            user_id = log.get("user_id", "")
            user_name = users_map.get(user_id, log.get("user_name", "Sistema"))
            if len(str(user_name)) > 25:
                user_name = str(user_name)[:22] + "..."
            
            # Event type
            event_type_val = log.get("event_type", "N/A")
            if len(str(event_type_val)) > 25:
                event_type_val = str(event_type_val)[:22] + "..."
            
            # Module/Resource
            module = log.get("module", log.get("resource_type", "N/A"))
            if len(str(module)) > 15:
                module = str(module)[:12] + "..."
            
            # IP Address
            ip_address = log.get("ip_address", "N/A")
            if len(str(ip_address)) > 15:
                ip_address = str(ip_address)[:12] + "..."
            
            table_data.append([
                timestamp,
                user_name,
                event_type_val,
                module,
                ip_address
            ])
        
        # Create table with adjusted column widths
        col_widths = [85, 110, 130, 70, 80]
        table = Table(table_data, colWidths=col_widths)
        
        # Table style
        table.setStyle(TableStyle([
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Body style
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#334155')),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F8FAFC'), colors.white]),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ]))
        
        elements.append(table)
        
        # Footer with count
        elements.append(Spacer(1, 20))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#64748B'),
            alignment=TA_LEFT
        )
        elements.append(Paragraph(f"Total de registros: {len(logs)}", footer_style))
        if len(logs) == 1000:
            elements.append(Paragraph("(Limitado a 1000 registros)", footer_style))
    else:
        # No records message
        no_data_style = ParagraphStyle(
            'NoData',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#94A3B8'),
            alignment=TA_CENTER,
            spaceBefore=50
        )
        elements.append(Paragraph("Sin registros de auditoría para los filtros seleccionados.", no_data_style))
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF bytes
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    # FINAL LOG
    logger.info(f"[AUDIT-EXPORT] PDF generado con {len(logs)} registros, tamaño: {len(pdf_bytes)} bytes")
    
    # Log the export action
    await log_audit_event(
        AuditEventType.SECURITY_ALERT,
        current_user["id"],
        "audit_logs",
        {"action": "export_pdf", "records_count": len(logs)},
        "system",
        "pdf_export"
    )
    
    # Return PDF file
    filename = f"audit-report-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

# ==================== DASHBOARD ====================
@router.get("/dashboard/stats")
async def get_dashboard_stats(current_user = Depends(get_current_user)):
    """Dashboard stats - scoped by condominium for Admin, global for SuperAdmin"""
    roles = current_user.get("roles", [])
    
    # Use tenant_filter for consistent scoping
    condo_filter = tenant_filter(current_user)
    
    # SuperAdmin sees global data (empty filter)
    if "SuperAdmin" in roles:
        stats = {
            "total_users": await db.users.count_documents({}),
            "active_guards": await db.guards.count_documents({"status": "active"}),
            "active_alerts": await db.panic_events.count_documents({"status": "active"}),
            "total_courses": await db.courses.count_documents({}),
            "pending_payments": await db.payment_transactions.count_documents({"payment_status": "pending"})
        }
    else:
        # Admin/others see only their condominium data
        stats = {
            "total_users": await db.users.count_documents(condo_filter),
            "active_guards": await db.guards.count_documents(tenant_filter(current_user, {"status": "active"})),
            "active_alerts": await db.panic_events.count_documents(tenant_filter(current_user, {"status": "active"})),
            "total_courses": await db.courses.count_documents(condo_filter),
            "pending_payments": await db.payment_transactions.count_documents(tenant_filter(current_user, {"payment_status": "pending"}))
        }
    return stats

@router.get("/dashboard/recent-activity")
async def get_recent_activity(current_user = Depends(get_current_user)):
    """
    Recent activity combining multiple sources:
    - Audit logs (logins, user changes)
    - Visitor entries (check-ins)
    - Panic events
    - Reservations
    Scoped by condominium for Admin, global for SuperAdmin
    """
    roles = current_user.get("roles", [])
    
    activities = []
    
    # Use tenant_filter for consistent scoping
    condo_query = tenant_filter(current_user)
    
    # 1. Audit logs (logins, user actions)
    audit_logs = await db.audit_logs.find(condo_query, {"_id": 0}).sort("timestamp", -1).to_list(10)
    for log in audit_logs:
        activities.append({
            "id": log.get("id"),
            "event_type": log.get("event_type"),
            "module": log.get("module"),
            "description": log.get("description") or log.get("event_type", "").replace("_", " ").title(),
            "user_name": log.get("user_name") or log.get("email"),
            "timestamp": log.get("timestamp"),
            "source": "audit"
        })
    
    # 2. Visitor entries (check-ins)
    entries = await db.visitor_entries.find(condo_query, {"_id": 0}).sort("entry_at", -1).to_list(10)
    for entry in entries:
        activities.append({
            "id": entry.get("id"),
            "event_type": "visitor_checkin",
            "module": "security",
            "description": f"{entry.get('visitor_name')} - Entrada de visitante",
            "user_name": entry.get("guard_name"),
            "timestamp": entry.get("entry_at"),
            "details": {
                "visitor_name": entry.get("visitor_name"),
                "authorization_type": entry.get("authorization_type"),
                "destination": entry.get("destination")
            },
            "source": "visitor"
        })
    
    # 3. Panic events (alerts)
    panic_events = await db.panic_events.find(condo_query, {"_id": 0}).sort("created_at", -1).to_list(5)
    for event in panic_events:
        activities.append({
            "id": event.get("id"),
            "event_type": "panic_alert",
            "module": "security",
            "description": f"Alerta: {event.get('panic_type_label', event.get('panic_type', 'Emergencia'))}",
            "user_name": event.get("user_name"),
            "timestamp": event.get("created_at"),
            "details": {
                "location": event.get("location"),
                "status": event.get("status")
            },
            "source": "panic"
        })
    
    # 4. Reservations
    reservations = await db.reservations.find(condo_query, {"_id": 0}).sort("created_at", -1).to_list(5)
    for res in reservations:
        activities.append({
            "id": res.get("id"),
            "event_type": "reservation_created",
            "module": "reservations",
            "description": f"Reservación: {res.get('area_name', 'Área común')}",
            "user_name": res.get("resident_name"),
            "timestamp": res.get("created_at"),
            "details": {
                "area_name": res.get("area_name"),
                "date": res.get("date"),
                "status": res.get("status")
            },
            "source": "reservation"
        })
    
    # Sort all by timestamp (most recent first)
    activities.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    
    return activities[:20]

# ==================== USERS MANAGEMENT ====================
