from pydantic import BaseModel, Field


class UserProfileCreate(BaseModel):
    user_id: str = Field(min_length=1)
    manual_skills: list[str] = Field(default_factory=list)
    interest_tags: list[str] = Field(default_factory=list)


class UserProfileResponse(UserProfileCreate):
    phase1_job_suggestions: list[str] = Field(default_factory=list)


class ResumeUploadResponse(BaseModel):
    user_id: str
    file_name: str
    saved_path: str
    size_bytes: int
    extracted_skills: list[str] = Field(default_factory=list)
    extraction_method: str = "none"   # "rules" | "error" | "none"
    education: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    experience_years: float | None = None
