"""LangGraph state şeması ve ilgili TypedDict'ler."""

from __future__ import annotations

from operator import add
from typing import Annotated, Literal, Optional, TypedDict

from pydantic import BaseModel, Field


class PlannedCall(TypedDict):
    tool: Literal["current_weather", "forecast", "hourly_forecast", "comfort", "venue_search", "uv_index"]
    args: dict


class Evaluation(TypedDict):
    approved: bool
    score: Optional[int]
    comment: str
    corrected: str


class WeatherWiseState(TypedDict, total=False):
    city: str
    preferences: str
    language: str
    weather: dict
    uv: dict
    weather_summary: str
    forecast: str
    forecast_hourly: dict
    comfort: str
    venues: dict[str, str]
    plan: list[PlannedCall]
    plan_done: bool
    recommendation: str
    itinerary: Optional[str]
    evaluation: Evaluation
    iteration: int
    history: Annotated[list[str], add]


class PlannerCall(BaseModel):
    tool: Literal["current_weather", "forecast", "hourly_forecast", "comfort", "venue_search", "uv_index"]
    args: dict = Field(default_factory=dict)


class PlannerOutput(BaseModel):
    calls: list[PlannerCall] = Field(default_factory=list)
    done: bool = False
    rationale: str = ""
