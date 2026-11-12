from typing import Literal
import math

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator

from app.services.experiment_service import (
    analyze_experiment, calculate_sample_size, create_experiment,
    generate_experiment_plan, list_experiments, update_experiment_status,
)

router = APIRouter(prefix="/api/experiments", tags=["Experiment Intelligence"])


class SampleSizeRequest(BaseModel):
    baseline_rate: float = Field(gt=0, lt=1)
    minimum_detectable_effect: float = Field(gt=0, lt=1)
    confidence_level: float = 0.95
    power: float = 0.80
    daily_eligible_users: int = Field(default=1000, ge=1)

    @field_validator("baseline_rate", "minimum_detectable_effect", "confidence_level", "power")
    @classmethod
    def finite_values(cls, value):
        if not math.isfinite(value):
            raise ValueError("Input values must be finite numbers.")
        return value


class ExperimentPlanRequest(BaseModel):
    opportunity: dict


class ExperimentCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    opportunity_id: str | None = None
    opportunity_title: str | None = None
    hypothesis: str = Field(min_length=10, max_length=2000)
    rationale: str = Field(default="", max_length=4000)
    primary_metric: str = Field(min_length=2, max_length=240)
    secondary_metrics: list[dict] = Field(default_factory=list)
    guardrails: list[dict] = Field(default_factory=list)
    baseline_rate: float = Field(gt=0, lt=1)
    minimum_detectable_effect: float = Field(gt=0, lt=1)
    confidence_level: float = 0.95
    power: float = 0.80
    daily_eligible_users: int = Field(default=1000, ge=1)
    status: Literal["draft", "running", "completed", "archived"] = "draft"

    @field_validator("baseline_rate", "minimum_detectable_effect", "confidence_level", "power")
    @classmethod
    def finite_create_values(cls, value):
        if not math.isfinite(value):
            raise ValueError("Input values must be finite numbers.")
        return value


class StatusRequest(BaseModel):
    status: Literal["draft", "running", "completed", "archived"]


class GuardrailResult(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    control_rate: float = Field(ge=0, le=1)
    variant_rate: float = Field(ge=0, le=1)
    max_increase: float = Field(default=0, ge=0, le=1)


class ExperimentAnalysisRequest(BaseModel):
    control_users: int = Field(gt=0)
    control_conversions: int = Field(ge=0)
    variant_users: int = Field(gt=0)
    variant_conversions: int = Field(ge=0)
    confidence_level: float = 0.95
    planned_sample_size_per_arm: int | None = Field(default=None, gt=0)
    guardrails: list[GuardrailResult] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_arm_counts(self):
        if self.control_conversions > self.control_users:
            raise ValueError("Control conversions cannot exceed control users.")
        if self.variant_conversions > self.variant_users:
            raise ValueError("Variant conversions cannot exceed variant users.")
        return self


@router.post("/sample-size")
def sample_size(payload: SampleSizeRequest):
    try:
        return calculate_sample_size(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/plan")
def experiment_plan(payload: ExperimentPlanRequest):
    return generate_experiment_plan(payload.opportunity)


@router.get("")
def experiments():
    return {"experiments": list_experiments()}


@router.post("")
def save_experiment(payload: ExperimentCreateRequest):
    try:
        return create_experiment(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/{experiment_id}/status")
def set_experiment_status(experiment_id: str, payload: StatusRequest):
    updated = update_experiment_status(experiment_id, payload.status)
    if updated is None:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    return updated


@router.post("/analyze")
def experiment_analysis(payload: ExperimentAnalysisRequest):
    data = payload.model_dump()
    try:
        return analyze_experiment(data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
