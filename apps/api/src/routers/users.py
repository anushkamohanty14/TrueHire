from fastapi import APIRouter, File, HTTPException, UploadFile
from typing import Any, Dict, Optional

from ..schemas.users import ResumeUploadResponse, UserProfileCreate, UserProfileResponse
from ..services.profile_service import ProfileService
from core.src.core.pipelines.phase2_user_input import merge_resume_skills, upload_resume
from core.src.core.pipelines.phase5_resume_processing import process_resume
from core.src.core.storage.mongo_store import MongoUserStore

router = APIRouter(prefix="/users", tags=["users"])
service = ProfileService()


@router.post("/profile", response_model=UserProfileResponse)
def create_profile(payload: UserProfileCreate) -> UserProfileResponse:
    normalized = service.create_profile(
        user_id=payload.user_id,
        manual_skills=payload.manual_skills,
        interest_tags=payload.interest_tags,
    )
    return UserProfileResponse(**normalized)


@router.get("/profile/{user_id}", response_model=UserProfileResponse)
def get_profile(user_id: str) -> UserProfileResponse:
    profile = service.get_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not found")
    return UserProfileResponse(**profile)


@router.post("/resume", response_model=ResumeUploadResponse)
async def upload_user_resume(user_id: str, file: UploadFile = File(...)) -> ResumeUploadResponse:
    content = await file.read()
    metadata = upload_resume(file.filename or "resume.bin", content, user_id)

    result = process_resume(metadata["saved_path"])
    metadata["extracted_skills"] = result.skills
    metadata["extraction_method"] = result.method
    metadata["education"] = result.education
    metadata["certifications"] = result.certifications
    metadata["experience_years"] = result.experience_years

    store = MongoUserStore()

    # Persist skills for backward compat with profile endpoint
    if result.skills:
        merge_resume_skills(user_id, result.skills)

    # Persist full extraction as latest_resume (overwrites previous)
    store.save_resume_extraction(
        user_id=user_id,
        file_name=file.filename or "resume.bin",
        skills=result.skills,
        education=result.education,
        certifications=result.certifications,
        experience_years=result.experience_years,
    )

    return ResumeUploadResponse(**metadata)


@router.get("/history/{user_id}")
def get_history(user_id: str, token: str = "") -> Dict[str, Any]:
    """Return the latest assessment + resume extraction for a user.

    Used by the History page and the LLM interview pipeline.
    """
    store = MongoUserStore()
    return store.get_user_snapshot(user_id)


@router.get("/interview-context/{user_id}")
def get_interview_context(user_id: str, token: str = "") -> Dict[str, Any]:
    """Return structured user data ready for LLM interview pipeline injection."""
    store = MongoUserStore()
    return store.get_interview_context(user_id)
