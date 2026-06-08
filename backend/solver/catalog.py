from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DEFAULT_NIGHT_SHIFT_NAMES = {"Nuit"}


@dataclass(frozen=True)
class AssignmentMetadata:
    name: str
    parent: str
    duration: int
    is_half: bool = False
    segment: str | None = None
    label: str | None = None
    penalty: int = 0
    is_night: bool = False
    requires_next_day_rest: bool = False
    start_time: str | None = None
    end_time: str | None = None


def _duration_to_tenths(value: Any, field_name: str) -> int:
    try:
        duration = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a positive number") from exc
    if duration <= 0:
        raise ValueError(f"{field_name} must be a positive number")
    return int(round(duration * 10))


def _is_enabled_half_config(half_config: dict[str, Any]) -> bool:
    return bool(half_config.get("enabled", True))


def build_vacation_catalog(config: dict[str, Any]) -> dict[str, Any]:
    """Build a normalized assignment catalog from user-facing vacation config."""
    coverage_vacations = list(config.get("vacations") or [])
    configured_durations = config.get("vacation_durations") or {}
    half_vacations = config.get("half_vacations") or {}
    vacation_metadata = config.get("vacation_metadata") or {}

    assignment_metadata: dict[str, AssignmentMetadata] = {}
    assignable_vacations: list[str] = []
    coverage_segments: dict[str, list[str]] = {}
    segment_covering_assignments: dict[tuple[str, str], list[str]] = {}
    half_vacation_names: set[str] = set()

    for parent in coverage_vacations:
        if parent not in configured_durations:
            raise ValueError(
                "Missing vacation_durations entries for configured vacations: "
                f"{parent}"
            )
        parent_duration = _duration_to_tenths(
            configured_durations[parent], f"vacation_durations[{parent}]"
        )
        parent_metadata = vacation_metadata.get(parent) or {}
        parent_is_night = bool(parent_metadata.get("is_night", parent in DEFAULT_NIGHT_SHIFT_NAMES))
        parent_requires_rest = bool(
            parent_metadata.get("requires_next_day_rest", parent_is_night)
        )
        assignment_metadata[parent] = AssignmentMetadata(
            name=parent,
            parent=parent,
            duration=parent_duration,
            is_half=False,
            label=parent_metadata.get("label", parent),
            is_night=parent_is_night,
            requires_next_day_rest=parent_requires_rest,
            start_time=parent_metadata.get("start_time"),
            end_time=parent_metadata.get("end_time"),
        )
        assignable_vacations.append(parent)

        parent_half_config = half_vacations.get(parent)
        if isinstance(parent_half_config, dict) and _is_enabled_half_config(parent_half_config):
            segments = parent_half_config.get("segments") or []
            if not segments:
                coverage_segments[parent] = [parent]
                segment_covering_assignments[(parent, parent)] = [parent]
                continue

            segment_names: list[str] = []
            segment_duration_sum = 0
            penalty = int(parent_half_config.get("penalty", 0))
            for index, segment in enumerate(segments):
                if not isinstance(segment, dict):
                    raise ValueError(f"half_vacations[{parent}].segments[{index}] must be an object")
                segment_name = segment.get("name")
                if not segment_name or not isinstance(segment_name, str):
                    raise ValueError(f"half_vacations[{parent}].segments[{index}].name is required")
                if segment_name in assignment_metadata:
                    raise ValueError(f"Duplicate assignable vacation name: {segment_name}")
                segment_duration = _duration_to_tenths(
                    segment.get("duration"),
                    f"half_vacations[{parent}].segments[{index}].duration",
                )
                segment_duration_sum += segment_duration
                segment_names.append(segment_name)
                half_vacation_names.add(segment_name)
                segment_is_night = bool(segment.get("is_night", parent_is_night))
                segment_requires_rest = bool(
                    segment.get("requires_next_day_rest", segment_is_night or parent_requires_rest)
                )
                assignment_metadata[segment_name] = AssignmentMetadata(
                    name=segment_name,
                    parent=parent,
                    duration=segment_duration,
                    is_half=True,
                    segment=segment_name,
                    label=segment.get("label", segment_name),
                    penalty=penalty,
                    is_night=segment_is_night,
                    requires_next_day_rest=segment_requires_rest,
                    start_time=segment.get("start_time", parent_metadata.get("start_time")),
                    end_time=segment.get("end_time", parent_metadata.get("end_time")),
                )
                assignable_vacations.append(segment_name)
                segment_covering_assignments[(parent, segment_name)] = [parent, segment_name]

            if segment_duration_sum != parent_duration:
                raise ValueError(
                    f"half_vacations[{parent}] segment durations must sum to "
                    f"vacation_durations[{parent}]"
                )
            coverage_segments[parent] = segment_names
        else:
            coverage_segments[parent] = [parent]
            segment_covering_assignments[(parent, parent)] = [parent]

    return {
        "coverage_vacations": coverage_vacations,
        "assignable_vacations": assignable_vacations,
        "assignment_metadata": assignment_metadata,
        "coverage_segments": coverage_segments,
        "segment_covering_assignments": segment_covering_assignments,
        "half_vacation_names": half_vacation_names,
    }


def _metadata_map(ctx_or_catalog):
    if isinstance(ctx_or_catalog, dict):
        return ctx_or_catalog.get("assignment_metadata", {})
    return getattr(ctx_or_catalog, "assignment_metadata", {})


def assignment_parent(ctx, assignment: str) -> str:
    metadata = _metadata_map(ctx).get(assignment)
    return metadata.parent if metadata else assignment


def is_half_assignment(ctx, assignment: str) -> bool:
    metadata = _metadata_map(ctx).get(assignment)
    return bool(metadata and metadata.is_half)


def is_night_assignment(ctx, assignment: str) -> bool:
    metadata = _metadata_map(ctx).get(assignment)
    return bool(metadata and metadata.is_night)


def requires_next_day_rest(ctx, assignment: str) -> bool:
    metadata = _metadata_map(ctx).get(assignment)
    return bool(metadata and metadata.requires_next_day_rest)


def assignment_matches_choice(ctx, assignment: str, choices: list[str] | set[str]) -> bool:
    if assignment in choices:
        return True
    metadata = _metadata_map(ctx).get(assignment)
    return bool(metadata and metadata.parent in choices)
