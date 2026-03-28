"""Pydantic request/response models."""

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    job_id: str
    filename: str
    duration: float
    resolution: str
    fps: float
    file_size_mb: float


class ReferenceUploadResponse(BaseModel):
    job_id: str
    reference_uploaded: bool


class GradeRequest(BaseModel):
    job_id: str
    mode: str = Field(pattern="^(preset|reference|smart)$")
    preset_name: str | None = None
    strength: float = Field(default=0.8, ge=0.0, le=1.0)
    use_auto_strength: bool = False
    multi_scene: bool = False
    auto_wb: bool = False
    output_format: str = Field(default="both", pattern="^(video|lut|both)$")


class GradeStartResponse(BaseModel):
    job_id: str
    status: str
    message: str


class GradeResult(BaseModel):
    graded_video_url: str | None = None
    lut_url: str | None = None
    preview_url: str | None = None
    comparison_url: str | None = None


class GradeStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int = 0
    current_step: str = ""
    elapsed_seconds: float = 0
    estimated_remaining: float | None = None
    result: GradeResult | None = None
    queue_position: int | None = None


class PresetInfo(BaseModel):
    name: str
    display_name: str
    description: str
    category: str
    preview_colors: list[str]


class PresetsListResponse(BaseModel):
    presets: list[PresetInfo]


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
