"""GENTURIX - School Module Router (Auto-extracted from server.py)"""
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

# ==================== SCHOOL MODULE ====================
@router.post("/school/courses")
async def create_course(course: CourseCreate, request: Request, current_user = Depends(require_role("Administrador"))):
    course_doc = {
        "id": str(uuid.uuid4()),
        "title": course.title,
        "description": course.description,
        "duration_hours": course.duration_hours,
        "instructor": course.instructor,
        "category": course.category,
        "lessons": [],
        "enrolled_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.courses.insert_one(course_doc)
    await log_audit_event(
        AuditEventType.USER_UPDATED, current_user["id"], "school",
        {"action": "course_created", "course_name": course_data.name},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown"),
        condominium_id=current_user.get("condominium_id"),
        user_email=current_user.get("email"),
    )
    return course_doc

@router.get("/school/courses")
async def get_courses(current_user = Depends(get_current_user)):
    courses = await db.courses.find({}, {"_id": 0}).to_list(100)
    return courses

@router.get("/school/courses/{course_id}")
async def get_course(course_id: str, current_user = Depends(get_current_user)):
    course = await db.courses.find_one({"id": course_id}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@router.post("/school/enroll")
async def enroll_course(enrollment: EnrollmentCreate, request: Request, current_user = Depends(get_current_user)):
    course = await db.courses.find_one({"id": enrollment.course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    existing = await db.enrollments.find_one({
        "course_id": enrollment.course_id,
        "student_id": enrollment.student_id
    })
    if existing:
        raise HTTPException(status_code=409, detail="Already enrolled")
    
    enrollment_doc = {
        "id": str(uuid.uuid4()),
        "course_id": enrollment.course_id,
        "course_title": course["title"],
        "student_id": enrollment.student_id,
        "student_name": current_user["full_name"],
        "progress": 0,
        "completed_lessons": [],
        "enrolled_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "certificate_id": None
    }
    
    await db.enrollments.insert_one(enrollment_doc)
    await db.courses.update_one({"id": enrollment.course_id}, {"$inc": {"enrolled_count": 1}})
    
    await log_audit_event(
        AuditEventType.COURSE_ENROLLED,
        current_user["id"],
        "school",
        {"course_id": enrollment.course_id, "course_title": course["title"]},
        request.client.host if request.client else "unknown",
        request.headers.get("user-agent", "unknown")
    )
    
    return enrollment_doc

@router.get("/school/enrollments")
async def get_my_enrollments(current_user = Depends(get_current_user)):
    enrollments = await db.enrollments.find({"student_id": current_user["id"]}, {"_id": 0}).to_list(100)
    return enrollments

@router.get("/school/certificates")
async def get_certificates(current_user = Depends(get_current_user)):
    certificates = await db.certificates.find({"student_id": current_user["id"]}, {"_id": 0}).to_list(100)
    return certificates

@router.get("/school/student-progress/{student_id}")
async def get_student_progress(student_id: str, current_user = Depends(get_current_user)):
    if current_user["id"] != student_id and "Administrador" not in current_user["roles"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    enrollments = await db.enrollments.find({"student_id": student_id}, {"_id": 0}).to_list(100)
    certificates = await db.certificates.find({"student_id": student_id}, {"_id": 0}).to_list(100)
    
    return {
        "enrollments": enrollments,
        "certificates": certificates,
        "total_courses": len(enrollments),
        "completed_courses": len([e for e in enrollments if e.get("completed_at")]),
        "total_certificates": len(certificates)
    }

# ==================== PAYMENTS MODULE ====================
# GENTURIX PRICING MODEL: $1 per user per month
# Simple, accessible, massive adoption model

class UserSubscriptionCreate(BaseModel):
    user_count: int = 1

