"""GENTURIX - Asamblea Virtual Router (Auto-extracted from server.py)"""
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

# ══════════════════════════════════════════════════════════════
# ASAMBLEA VIRTUAL MODULE — Collections: assemblies, assembly_votes, assembly_attendance
# ══════════════════════════════════════════════════════════════

class AsambleaCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(None, max_length=5000)
    date: str = Field(..., max_length=30)
    modality: str = Field("presencial", pattern=r"^(presencial|virtual|hibrida)$")
    meeting_link: Optional[str] = Field(None, max_length=500)
    agenda_items: Optional[list] = None


class AgendaItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    is_votable: bool = False


class VoteCreate(BaseModel):
    agenda_item_id: str
    vote: str = Field(..., pattern=r"^(yes|no|abstain)$")


@router.post("/asamblea")
@limiter.limit(RATE_LIMIT_PUSH)
async def create_asamblea(
    payload: AsambleaCreate,
    request: Request,
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN)),
):
    """Admin creates a new assembly."""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        raise HTTPException(status_code=400, detail="No condominium associated")

    now = datetime.now(timezone.utc).isoformat()
    assembly_id = str(uuid.uuid4())

    doc = {
        "id": assembly_id,
        "condominium_id": condo_id,
        "title": sanitize_text(payload.title),
        "description": sanitize_text(payload.description) if payload.description else "",
        "date": sanitize_text(payload.date),
        "modality": payload.modality,
        "meeting_link": sanitize_text(payload.meeting_link) if payload.meeting_link else None,
        "status": "scheduled",
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now,
    }
    await db.assemblies.insert_one(doc)

    # Create agenda items if provided
    if payload.agenda_items:
        for idx, item in enumerate(payload.agenda_items):
            if isinstance(item, dict) and item.get("title"):
                agenda_doc = {
                    "id": str(uuid.uuid4()),
                    "assembly_id": assembly_id,
                    "condominium_id": condo_id,
                    "title": sanitize_text(item["title"]),
                    "description": sanitize_text(item.get("description", "")),
                    "is_votable": bool(item.get("is_votable", False)),
                    "order": idx,
                    "created_at": now,
                }
                await db.agenda_items.insert_one(agenda_doc)

    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "asamblea",
        {"action": "assembly_created", "assembly_id": assembly_id, "title": doc["title"]},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id, user_email=current_user.get("email"),
    )

    safe = {k: v for k, v in doc.items() if k != "_id"}
    return safe


@router.get("/asamblea")
async def list_asambleas(
    current_user=Depends(get_current_user),
):
    """List assemblies for the condominium."""
    condo_id = current_user.get("condominium_id")
    if not condo_id:
        return {"items": []}

    items = await db.assemblies.find(
        {"condominium_id": condo_id}, {"_id": 0}
    ).sort("date", -1).to_list(100)

    # Enrich with attendance count
    for item in items:
        att_count = await db.assembly_attendance.count_documents({"assembly_id": item["id"]})
        item["attendance_count"] = att_count

    return {"items": items}


@router.get("/asamblea/{assembly_id}")
async def get_asamblea_detail(
    assembly_id: str,
    current_user=Depends(get_current_user),
):
    """Get assembly detail with agenda, attendance, and vote results."""
    condo_id = current_user.get("condominium_id")

    assembly = await db.assemblies.find_one(
        {"id": assembly_id, "condominium_id": condo_id}, {"_id": 0}
    )
    if not assembly:
        raise HTTPException(status_code=404, detail="Asamblea no encontrada")

    # Get agenda items
    agenda = await db.agenda_items.find(
        {"assembly_id": assembly_id}, {"_id": 0}
    ).sort("order", 1).to_list(50)

    # Get attendance list
    attendance = await db.assembly_attendance.find(
        {"assembly_id": assembly_id}, {"_id": 0}
    ).to_list(500)

    # Get votes per agenda item
    for item in agenda:
        if item.get("is_votable"):
            vote_pipeline = [
                {"$match": {"agenda_item_id": item["id"]}},
                {"$group": {"_id": "$vote", "count": {"$sum": 1}}},
            ]
            vote_agg = await db.assembly_votes.aggregate(vote_pipeline).to_list(5)
            results = {"yes": 0, "no": 0, "abstain": 0, "total": 0}
            for v in vote_agg:
                if v["_id"] in results:
                    results[v["_id"]] = v["count"]
                    results["total"] += v["count"]
            item["vote_results"] = results

            # Check if current user has voted
            user_vote = await db.assembly_votes.find_one(
                {"agenda_item_id": item["id"], "user_id": current_user["id"]}, {"_id": 0, "vote": 1}
            )
            item["my_vote"] = user_vote["vote"] if user_vote else None

    # Check if user has confirmed attendance
    my_attendance = await db.assembly_attendance.find_one(
        {"assembly_id": assembly_id, "user_id": current_user["id"]}
    )

    assembly["agenda"] = agenda
    assembly["attendance"] = attendance
    assembly["attendance_count"] = len(attendance)
    assembly["my_attendance"] = bool(my_attendance)

    return assembly


@router.post("/asamblea/{assembly_id}/agenda")
async def add_agenda_item(
    assembly_id: str,
    payload: AgendaItemCreate,
    request: Request,
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN)),
):
    """Add an agenda item to an assembly."""
    condo_id = current_user.get("condominium_id")
    assembly = await db.assemblies.find_one({"id": assembly_id, "condominium_id": condo_id})
    if not assembly:
        raise HTTPException(status_code=404, detail="Asamblea no encontrada")

    count = await db.agenda_items.count_documents({"assembly_id": assembly_id})
    now = datetime.now(timezone.utc).isoformat()

    doc = {
        "id": str(uuid.uuid4()),
        "assembly_id": assembly_id,
        "condominium_id": condo_id,
        "title": sanitize_text(payload.title),
        "description": sanitize_text(payload.description) if payload.description else "",
        "is_votable": payload.is_votable,
        "order": count,
        "created_at": now,
    }
    await db.agenda_items.insert_one(doc)

    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "asamblea",
        {"action": "agenda_item_added", "assembly_id": assembly_id, "item_title": doc["title"]},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id, user_email=current_user.get("email"),
    )

    safe = {k: v for k, v in doc.items() if k != "_id"}
    return safe


@router.post("/asamblea/{assembly_id}/attend")
async def confirm_attendance(
    assembly_id: str,
    request: Request,
    current_user=Depends(get_current_user),
):
    """Resident confirms attendance to an assembly."""
    condo_id = current_user.get("condominium_id")
    assembly = await db.assemblies.find_one({"id": assembly_id, "condominium_id": condo_id})
    if not assembly:
        raise HTTPException(status_code=404, detail="Asamblea no encontrada")

    existing = await db.assembly_attendance.find_one(
        {"assembly_id": assembly_id, "user_id": current_user["id"]}
    )
    if existing:
        return {"status": "already_confirmed"}

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "assembly_id": assembly_id,
        "condominium_id": condo_id,
        "user_id": current_user["id"],
        "user_name": current_user.get("full_name", ""),
        "user_email": current_user.get("email", ""),
        "unit": current_user.get("apartment", ""),
        "confirmed_at": now,
    }
    await db.assembly_attendance.insert_one(doc)

    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "asamblea",
        {"action": "attendance_confirmed", "assembly_id": assembly_id},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id, user_email=current_user.get("email"),
    )

    return {"status": "confirmed"}


@router.post("/asamblea/{assembly_id}/vote")
async def cast_vote(
    assembly_id: str,
    payload: VoteCreate,
    request: Request,
    current_user=Depends(get_current_user),
):
    """Resident casts a vote on a votable agenda item."""
    condo_id = current_user.get("condominium_id")
    assembly = await db.assemblies.find_one({"id": assembly_id, "condominium_id": condo_id})
    if not assembly:
        raise HTTPException(status_code=404, detail="Asamblea no encontrada")

    # Verify agenda item is votable
    agenda_item = await db.agenda_items.find_one(
        {"id": payload.agenda_item_id, "assembly_id": assembly_id}, {"_id": 0}
    )
    if not agenda_item:
        raise HTTPException(status_code=404, detail="Punto de agenda no encontrado")
    if not agenda_item.get("is_votable"):
        raise HTTPException(status_code=400, detail="Este punto no es votable")

    # One vote per user per agenda item
    existing = await db.assembly_votes.find_one(
        {"agenda_item_id": payload.agenda_item_id, "user_id": current_user["id"]}
    )
    if existing:
        # Update existing vote
        await db.assembly_votes.update_one(
            {"agenda_item_id": payload.agenda_item_id, "user_id": current_user["id"]},
            {"$set": {"vote": payload.vote, "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        return {"status": "vote_updated", "vote": payload.vote}

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "assembly_id": assembly_id,
        "agenda_item_id": payload.agenda_item_id,
        "condominium_id": condo_id,
        "user_id": current_user["id"],
        "user_name": current_user.get("full_name", ""),
        "vote": payload.vote,
        "created_at": now,
    }
    await db.assembly_votes.insert_one(doc)

    await log_audit_event(
        AuditEventType.SECURITY_ALERT, current_user["id"], "asamblea",
        {"action": "vote_cast", "assembly_id": assembly_id, "item_id": payload.agenda_item_id, "vote": payload.vote},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id, user_email=current_user.get("email"),
    )

    return {"status": "vote_recorded", "vote": payload.vote}


@router.get("/asamblea/{assembly_id}/results")
async def get_assembly_results(
    assembly_id: str,
    current_user=Depends(get_current_user),
):
    """Get vote results for an assembly."""
    condo_id = current_user.get("condominium_id")
    assembly = await db.assemblies.find_one(
        {"id": assembly_id, "condominium_id": condo_id}, {"_id": 0, "id": 1, "title": 1, "date": 1}
    )
    if not assembly:
        raise HTTPException(status_code=404, detail="Asamblea no encontrada")

    agenda = await db.agenda_items.find(
        {"assembly_id": assembly_id, "is_votable": True}, {"_id": 0}
    ).sort("order", 1).to_list(50)

    results = []
    for item in agenda:
        pipeline = [
            {"$match": {"agenda_item_id": item["id"]}},
            {"$group": {"_id": "$vote", "count": {"$sum": 1}}},
        ]
        agg = await db.assembly_votes.aggregate(pipeline).to_list(5)
        votes = {"yes": 0, "no": 0, "abstain": 0}
        for v in agg:
            if v["_id"] in votes:
                votes[v["_id"]] = v["count"]
        results.append({
            "agenda_item_id": item["id"],
            "title": item["title"],
            "votes": votes,
            "total_votes": sum(votes.values()),
        })

    attendance_count = await db.assembly_attendance.count_documents({"assembly_id": assembly_id})

    return {
        "assembly": assembly,
        "results": results,
        "attendance_count": attendance_count,
    }


@router.post("/asamblea/{assembly_id}/generate-acta")
async def generate_acta(
    assembly_id: str,
    request: Request,
    token: Optional[str] = Query(None),
    current_user=Depends(get_current_user_optional),
):
    """Generate a PDF Acta for the assembly and save to Documents."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    user = current_user
    if not user and token:
        payload = verify_access_token(token)
        if payload:
            uid = payload.get("sub")
            user = await db.users.find_one({"id": uid}, {"_id": 0})
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=401, detail="Autenticacion requerida")
    user_roles = user.get("roles", [])
    if not any(r in user_roles for r in ["Administrador", "Supervisor", "SuperAdmin"]):
        raise HTTPException(status_code=403, detail="Permiso denegado")

    condo_id = user.get("condominium_id")
    assembly = await db.assemblies.find_one({"id": assembly_id, "condominium_id": condo_id}, {"_id": 0})
    if not assembly:
        raise HTTPException(status_code=404, detail="Asamblea no encontrada")

    condo = await db.condominiums.find_one({"id": condo_id}, {"_id": 0, "name": 1})
    condo_name = condo.get("name", "Condominio") if condo else "Condominio"

    agenda = await db.agenda_items.find({"assembly_id": assembly_id}, {"_id": 0}).sort("order", 1).to_list(50)
    attendance = await db.assembly_attendance.find({"assembly_id": assembly_id}, {"_id": 0}).to_list(500)

    # Get vote results
    for item in agenda:
        if item.get("is_votable"):
            pipeline = [{"$match": {"agenda_item_id": item["id"]}}, {"$group": {"_id": "$vote", "count": {"$sum": 1}}}]
            agg = await db.assembly_votes.aggregate(pipeline).to_list(5)
            votes = {"yes": 0, "no": 0, "abstain": 0}
            for v in agg:
                if v["_id"] in votes:
                    votes[v["_id"]] = v["count"]
            item["vote_results"] = votes

    # Build PDF
    buf = io.BytesIO()
    doc_pdf = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ActaTitle", parent=styles["Title"], fontSize=16, spaceAfter=6)
    subtitle = ParagraphStyle("ActaSub", parent=styles["Normal"], fontSize=10, textColor=colors.grey, spaceAfter=4)
    section_style = ParagraphStyle("ActaSec", parent=styles["Heading2"], fontSize=12, spaceAfter=6, spaceBefore=14)
    body_style = ParagraphStyle("ActaBody", parent=styles["Normal"], fontSize=9, spaceAfter=4)

    modality_label = {"presencial": "Presencial", "virtual": "Virtual", "hibrida": "Hibrida"}
    elements = []
    elements.append(Paragraph("Acta de Asamblea", title_style))
    elements.append(Paragraph(f"{condo_name}", subtitle))
    elements.append(Spacer(1, 8))

    info = [
        ["Titulo:", assembly["title"], "Fecha:", assembly["date"]],
        ["Modalidad:", modality_label.get(assembly["modality"], assembly["modality"]), "Asistentes:", str(len(attendance))],
    ]
    info_tbl = Table(info, colWidths=[70, 200, 70, 130])
    info_tbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_tbl)

    if assembly.get("description"):
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(assembly["description"], body_style))

    # Attendance
    elements.append(Paragraph("Asistencia", section_style))
    if attendance:
        att_data = [["Nombre", "Email", "Unidad"]]
        for a in attendance:
            att_data.append([a.get("user_name", ""), a.get("user_email", ""), a.get("unit", "-")])
        att_tbl = Table(att_data, colWidths=[160, 180, 80])
        att_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.25)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(att_tbl)
    else:
        elements.append(Paragraph("Sin asistencia registrada", body_style))

    # Agenda & Votes
    elements.append(Paragraph("Agenda y Resultados", section_style))
    for idx, item in enumerate(agenda):
        elements.append(Paragraph(f"{idx+1}. {item['title']}", ParagraphStyle("AgItem", parent=styles["Normal"], fontSize=10, fontName="Helvetica-Bold", spaceAfter=2, spaceBefore=6)))
        if item.get("description"):
            elements.append(Paragraph(item["description"], body_style))
        if item.get("is_votable") and item.get("vote_results"):
            vr = item["vote_results"]
            total = vr["yes"] + vr["no"] + vr["abstain"]
            vote_data = [["A favor", "En contra", "Abstencion", "Total"]]
            vote_data.append([str(vr["yes"]), str(vr["no"]), str(vr["abstain"]), str(total)])
            vote_tbl = Table(vote_data, colWidths=[80, 80, 80, 80])
            vote_tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.15, 0.3, 0.15)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]))
            elements.append(vote_tbl)
            winner = "A favor" if vr["yes"] > vr["no"] else "En contra" if vr["no"] > vr["yes"] else "Empate"
            elements.append(Paragraph(f"Resultado: {winner}", ParagraphStyle("Res", parent=body_style, textColor=colors.Color(0.2, 0.5, 0.2))))

    doc_pdf.build(elements)
    buf.seek(0)
    pdf_bytes = buf.read()

    # Save to storage and create document record
    safe_title = assembly["title"].replace(" ", "_")[:30]
    storage_path = f"{DOC_APP_NAME}/actas/{condo_id}/{assembly_id}.pdf"
    try:
        await _put_object(storage_path, pdf_bytes, "application/pdf")
    except Exception as e:
        logger.warning(f"[ASAMBLEA] Failed to save acta to storage: {e}")

    # Create document record
    now = datetime.now(timezone.utc).isoformat()
    doc_record = {
        "id": str(uuid.uuid4()),
        "condominium_id": condo_id,
        "name": f"Acta - {assembly['title']}",
        "description": f"Acta de la asamblea del {assembly['date']}",
        "file_url": storage_path,
        "file_type": "pdf",
        "file_size": len(pdf_bytes),
        "category": "acta",
        "visibility": "public",
        "allowed_roles": "Administrador,Residente",
        "uploaded_by": user["id"],
        "uploaded_by_name": user.get("full_name", "Admin"),
        "original_filename": f"acta_{safe_title}.pdf",
        "created_at": now,
        "updated_at": now,
    }
    await db.documents.insert_one(doc_record)

    await log_audit_event(
        AuditEventType.SECURITY_ALERT, user["id"], "asamblea",
        {"action": "acta_generated", "assembly_id": assembly_id},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=condo_id, user_email=user.get("email"),
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="acta_{safe_title}.pdf"'},
    )


@router.patch("/asamblea/{assembly_id}")
async def update_asamblea_status(
    assembly_id: str,
    status: str = Query(..., regex="^(scheduled|in_progress|completed|cancelled)$"),
    request: Request = None,
    current_user=Depends(require_role(RoleEnum.ADMINISTRADOR, RoleEnum.SUPER_ADMIN)),
):
    """Update assembly status."""
    condo_id = current_user.get("condominium_id")
    assembly = await db.assemblies.find_one({"id": assembly_id, "condominium_id": condo_id})
    if not assembly:
        raise HTTPException(status_code=404, detail="Asamblea no encontrada")

    now = datetime.now(timezone.utc).isoformat()
    await db.assemblies.update_one(
        {"id": assembly_id},
        {"$set": {"status": status, "updated_at": now}},
    )

    return {"status": "ok", "new_status": status}


