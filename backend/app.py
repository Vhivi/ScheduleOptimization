import json
import os
from datetime import datetime, timedelta
from copy import deepcopy

from flask import Flask, jsonify, request
from flask_cors import CORS
from jsonschema import Draft202012Validator
from solver.catalog import build_vacation_catalog, is_night_assignment, requires_next_day_rest
from solver.engine import generate_planning as generate_planning_engine

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
DEFAULT_CONFIG_PATH = os.path.join(BASE_DIR, "config.example.json")
CONFIG_SCHEMA_PATH = os.path.join(BASE_DIR, "config.schema.json")
_active_config = None
config = None


def _load_json_file(path):
    with open(path, "r", encoding="utf-8") as json_file:
        return json.load(json_file)


def load_config():
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(
            "Missing backend/config.json. Copy backend/config.example.json to "
            "backend/config.json and adjust it for your local environment."
        )
    return _load_json_file(CONFIG_PATH)


def load_default_config():
    return _load_json_file(DEFAULT_CONFIG_PATH)


def load_config_schema():
    return _load_json_file(CONFIG_SCHEMA_PATH)


def validate_runtime_config(candidate_config):
    validator = Draft202012Validator(load_config_schema())
    errors = []
    for error in validator.iter_errors(candidate_config):
        path = "/".join(str(part) for part in error.path) or "(root)"
        errors.append({"path": path, "message": error.message})

    vacations = candidate_config.get("vacations", [])
    vacation_durations = candidate_config.get("vacation_durations", {})
    if isinstance(vacations, list) and isinstance(vacation_durations, dict):
        for vacation in vacations:
            if vacation not in vacation_durations:
                errors.append(
                    {
                        "path": f"vacation_durations/{vacation}",
                        "message": (
                            f"Missing duration for configured vacation '{vacation}'."
                        ),
                    }
                )

    if not errors:
        try:
            build_vacation_catalog(candidate_config)
        except ValueError as exc:
            errors.append({"path": "half_vacations", "message": str(exc)})

    half_vacations = candidate_config.get("half_vacations", {})
    if isinstance(vacations, list) and isinstance(half_vacations, dict):
        for parent in half_vacations:
            if parent not in vacations:
                errors.append(
                    {
                        "path": f"half_vacations/{parent}",
                        "message": f"Unknown parent vacation '{parent}'.",
                    }
                )
            elif parent == "CDP":
                errors.append(
                    {
                        "path": "half_vacations/CDP",
                        "message": "CDP ne peut pas être découpé en demi-vacations.",
                    }
                )

    return errors


def save_config(config_data):
    temp_path = f"{CONFIG_PATH}.tmp"
    with open(temp_path, "w", encoding="utf-8") as config_file:
        json.dump(config_data, config_file, ensure_ascii=False, indent=2)
        config_file.write("\n")
    os.replace(temp_path, CONFIG_PATH)


def set_active_config(config_data):
    global _active_config, config
    _active_config = config_data
    config = config_data


def get_active_config():
    global _active_config, config
    if _active_config is None:
        try:
            _active_config = load_config()
        except FileNotFoundError:
            _active_config = load_default_config()
        config = _active_config
    return _active_config


FRENCH_WEEKDAY_ABBREVIATIONS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]


@app.route("/")
def home():
    return "Hello, Flask is up and running!"


@app.route("/config", methods=["GET"])
def get_config_route():
    return jsonify(get_active_config())


@app.route("/config/default", methods=["GET"])
def get_default_config_route():
    return jsonify(load_default_config())


@app.route("/config", methods=["PUT"])
def update_config_route():
    payload, payload_error = parse_json_object_payload()
    if payload_error is not None:
        return payload_error

    validation_errors = validate_runtime_config(payload)
    if validation_errors:
        return (
            jsonify(
                {
                    "error": "Invalid configuration payload",
                    "details": validation_errors,
                }
            ),
            400,
        )

    save_config(payload)
    set_active_config(payload)
    return jsonify(payload)


@app.route("/generate-planning", methods=["POST"])
def generate_planning_route():
    payload, payload_error = parse_json_object_payload()
    if payload_error is not None:
        return payload_error
    planning_or_error, status_code = _build_planning_payload(
        payload=payload, runtime_config=get_active_config()
    )
    if status_code != 200:
        return jsonify(planning_or_error), status_code
    return jsonify(planning_or_error)


def _build_planning_payload(payload, runtime_config):
    # Retrieving data from the JSON file
    agents = runtime_config["agents"]
    vacations = runtime_config["vacations"]
    catalog = build_vacation_catalog(runtime_config)
    assignable_vacations = catalog["assignable_vacations"]
    vacation_durations = dict(runtime_config["vacation_durations"])
    for assignment, metadata in catalog["assignment_metadata"].items():
        vacation_durations[assignment] = metadata.duration / 10
    holidays = runtime_config["holidays"]
    unavailable = {}
    dayOff = {}
    training = {}
    restrictions = {}
    restriction_types_durations = runtime_config.get("restriction_types_durations", {})

    # Retrieve agent training days and store them in a dictionary {agent: [days]}.
    for agent in agents:
        if "training" in agent:
            training[agent["name"]] = agent["training"]
    # Retrieve agent unavailability days and store them in a dictionary {agent: [days]}.
        if "unavailable" in agent:
            unavailable[agent["name"]] = agent["unavailable"]
        # Check if the agent has leave days
        if "vacations" in agent:
            dayOff[agent["name"]] = []
            # Browse each leave day period
            for vac in agent["vacations"]:
                # Check if the leave period is a dictionary and contains the start and end keys
                if isinstance(vac, dict) and "start" in vac and "end" in vac:
                    # Store leave days in a dictionary {agent: [start, end]}
                    dayOff[agent["name"]].append([vac["start"], vac["end"]])
        # Retrieve agent restrictions and store them in a dictionary {agent: [days]}.
        if "restrictions" in agent:
            restrictions[agent["name"]] = agent["restrictions"]

    start_date, end_date, date_error = _validate_date_range_payload(payload)
    if date_error is not None:
        return date_error[0].get_json(), date_error[1]

    periods = split_date_range_by_month(start_date, end_date)
    full_planning = {agent["name"]: [] for agent in agents}
    initial_shifts = payload.get("initial_shifts", {})
    if not isinstance(initial_shifts, dict):
        return {"error": "initial_shifts must be an object"}, 400

    # Validate initial shifts
    valid_agents = [agent["name"] for agent in agents]
    valid_vacations = assignable_vacations
    for agent_name, shifts in initial_shifts.items():
        if not isinstance(shifts, list):
            return {"error": f"initial_shifts for {agent_name} must be a list"}, 400
        if agent_name not in valid_agents:
            return {"error": f"Invalid agent: {agent_name}"}, 400
        for shift in shifts:
            if (
                not isinstance(shift, (list, tuple))
                or len(shift) != 2
                or not isinstance(shift[0], str)
                or not isinstance(shift[1], str)
            ):
                return {
                    "error": "Each initial shift must be [day, vacation] with string values"
                }, 400
            _, vacation = shift
            if vacation not in valid_vacations:
                return {"error": f"Invalid vacation: {vacation}"}, 400

    for chunk_start, chunk_end in periods:
        # Convert the start and end dates into strings
        start_date_str = chunk_start.strftime("%Y-%m-%d")
        end_date_str = chunk_end.strftime("%Y-%m-%d")

        # Calculate the list of days from dates
        week_schedule = get_week_schedule(start_date_str, end_date_str)
        previous_week_schedule = get_previous_week_schedule(start_date_str)

        # Calling up the schedule generation function
        try:
            result = generate_planning(
                agents,
                vacations,
                week_schedule,
                dayOff,
                previous_week_schedule,
                initial_shifts,
                planning_start_date=start_date_str,
                runtime_config=runtime_config,
            )
        except ValueError as exc:
            return {"error": str(exc)}, 400

        # If the result is a dict with an info key, return a 400 error.
        if "info" in result:
            return result, 400

        # Accumulate the results of each period in the full planning
        for name, shifts in result.items():
            # Add the shifts to the full planning for each agent
            if name not in full_planning:
                full_planning[name] = []
            full_planning[name].extend(shifts)

        # Prepare initial_shifts for the next iteration
        # Recalculate the previous_week_schedule for the day following chunk_end
        next_start = chunk_end + timedelta(days=1)
        next_previous = get_previous_week_schedule(next_start.strftime("%Y-%m-%d"))

        new_intial_shifts = {}
        for name, shifts in full_planning.items():
            # Only keep shifts from the previous week
            selected = []
            for day, vacation in shifts:
                if day in next_previous:
                    selected.append((day, vacation))
            if selected:
                new_intial_shifts[name] = selected

        initial_shifts = new_intial_shifts

    # Once all segments have been calculated, return everything
    original_week_schedule = get_week_schedule(
        payload["start_date"], payload["end_date"]
    )
    return {
        "planning": full_planning,
        "vacation_durations": vacation_durations,
        "vacation_colors": runtime_config.get("vacation_colors", {}),
        "assignable_vacations": assignable_vacations,
        "week_schedule": original_week_schedule,
        "holidays": holidays,
        "unavailable": unavailable,
        "dayOff": dayOff,
        "training": training,
        "restrictions": restrictions,
        "restriction_types_durations": restriction_types_durations,
    }, 200


def is_valid_date(date_str):
    """
    Check if the given string is a valid date in the format YYYY-MM-DD
    or if the given string is valid date even if it has the right format.

    Args:
        date_str (str): The date string to validate.

    Returns:
        bool: True if the date string is valid, False otherwise.
    """

    # Check if the date string is not None and is a string
    # If not, return False
    # This test is necessary to avoid TypeError when calling the strptime method
    if date_str is None or not isinstance(date_str, str):
        return False

    # Check if the date string has the right format
    # If not, return False
    # This test is necessary to avoid ValueError when calling the strptime method
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def parse_json_object_payload():
    payload = request.get_json(silent=True)
    if payload is None:
        return None, (jsonify({"error": "Missing or invalid JSON payload"}), 400)
    if not isinstance(payload, dict):
        return None, (jsonify({"error": "JSON payload must be an object"}), 400)
    return payload, None


def _validate_date_range_payload(payload):
    if "start_date" not in payload or "end_date" not in payload:
        return None, None, (jsonify({"error": "Missing start_date or end_date"}), 400)
    if not is_valid_date(payload["start_date"]) or not is_valid_date(payload["end_date"]):
        return None, None, (jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400)
    start_date = datetime.strptime(payload["start_date"], "%Y-%m-%d")
    end_date = datetime.strptime(payload["end_date"], "%Y-%m-%d")
    if end_date < start_date:
        return None, None, (
            jsonify({"error": "end_date must be greater than or equal to start_date"}),
            400,
        )
    return start_date, end_date, None


def _parse_manual_entries(manual_entries, runtime_config, start_date, end_date):
    if not isinstance(manual_entries, list):
        return None, None, None, (jsonify({"error": "manual_entries must be a list"}), 400)

    valid_agents = {agent["name"] for agent in runtime_config["agents"]}
    valid_vacations = set(build_vacation_catalog(runtime_config)["assignable_vacations"])
    valid_restriction_types = set(
        (runtime_config.get("restriction_types_durations") or {}).keys()
    )

    initial_shifts = {}
    status_entries = []
    warnings = []
    for entry in manual_entries:
        if not isinstance(entry, dict):
            return None, None, None, (jsonify({"error": "Each manual entry must be an object"}), 400)
        for field in ["agent", "date", "slot", "type", "value"]:
            if field not in entry:
                return None, None, None, (jsonify({"error": f"manual entry missing field '{field}'"}), 400)
        agent = entry["agent"]
        date = entry["date"]
        slot = entry["slot"]
        entry_type = entry["type"]
        value = entry["value"]
        if agent not in valid_agents:
            return None, None, None, (jsonify({"error": f"Invalid agent: {agent}"}), 400)
        if not is_valid_date(date):
            return None, None, None, (jsonify({"error": f"Invalid manual entry date: {date}"}), 400)
        entry_date = datetime.strptime(date, "%Y-%m-%d")
        if entry_date < start_date or entry_date > end_date:
            return None, None, None, (jsonify({"error": f"Manual entry date out of range: {date}"}), 400)
        if slot not in {"day", "night", "cdp"}:
            return None, None, None, (jsonify({"error": f"Invalid slot: {slot}"}), 400)
        if entry_type == "shift":
            if value not in valid_vacations:
                return None, None, None, (jsonify({"error": f"Invalid vacation: {value}"}), 400)
            day_label = format_day_label(entry_date)
            initial_shifts.setdefault(agent, []).append((day_label, value))
        elif entry_type == "status":
            if value in {"unavailable", "training", "vacations"}:
                pass  # These are valid status types
            elif value.startswith("restrictions:"):
                restriction_type = value.split(":", 1)[1]
                if restriction_type not in valid_restriction_types:
                    return None, None, None, (
                        jsonify({"error": f"Unkown restriction type: {restriction_type}"}),
                        400,
                    )
            elif value == "restriction":
                # kept for backward compatibility, warning emitted later
                pass
            else:
                return None, None, None, (jsonify({"error": f"Invalid status value: {value}"}), 400)
            status_entries.append(
                {
                    "agent": agent,
                    "date": date,
                    "slot": slot,
                    "value": value,
                }
            )
        else:
            return None, None, None, (jsonify({"error": f"Invalid entry type: {entry_type}"}), 400)

    return initial_shifts, status_entries, warnings, None


def _inject_manual_status_entries(runtime_config, status_entries):
    injected_config = deepcopy(runtime_config)
    agent_by_name = {agent["name"]: agent for agent in injected_config["agents"]}
    warnings = []
    for entry in status_entries:
        agent_name = entry["agent"]
        date = entry["date"]
        status_value = entry["value"]
        day_str = datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y")
        target = agent_by_name[agent_name]
        if status_value in {"unavailable", "training"}:
            target.setdefault(status_value, [])
            if day_str not in target[status_value]:
                target[status_value].append(day_str)
        elif status_value == "vacations":
            target.setdefault("vacations", [])
            target["vacations"].append({"start": day_str, "end": day_str})
        elif status_value == "restriction":
            warnings.append(
                {
                    "code": "STATUS_RESTRICTION_REQUIRES_SHIFT",
                    "agent": agent_name,
                    "date": date,
                    "slot": entry["slot"],
                    "message": "Restriction requires a shift name and was ignored.",
                    "source": "api_validation",
                }
            )
        elif status_value.startswith("restrictions:"):
            restriction_type = status_value.split(":", 1)[1]
            target.setdefault("restrictions", [])
            target["restrictions"].append({"date": day_str, "type": restriction_type})
    return injected_config, warnings

def _build_suggestions_from_context(manual_entries, warnings, unsat_reason=None, blocking_reasons=None):
    suggestions = []
    for warning in warnings:
        suggestion = {
            "agent": warning.get("agent"),
            "date": warning.get("date"),
            "slot": warning.get("slot", "day"),
            "reason_code": warning.get("code", "MANUAL_CONFLICT"),
            "message": warning.get("message", "Manual entry conflict."),
            "proposals": [{"action": "clear_cell"}],
        }
        suggestions.append(suggestion)

    if suggestions:
        return suggestions

    actionable_reasons = [
        reason
        for reason in (blocking_reasons or [])
        if reason.get("code") not in {"GLOBAL_UNSAT", "PREVALIDATION_WARNINGS_PRESENT"}
    ]
    if unsat_reason is not None and manual_entries and actionable_reasons:
        first = manual_entries[0]
        first_reason = actionable_reasons[0]
        suggestions.append(
            {
                "agent": first.get("agent"),
                "date": first.get("date"),
                "slot": first.get("slot", "day"),
                "reason_code": first_reason.get("code", "GLOBAL_UNSAT"),
                "message": first_reason.get("message", unsat_reason),
                "proposals": [{"action": "clear_cell"}],
            }
        )
    return suggestions


def _build_blocking_reasons_from_context(manual_entries, warnings, unsat_reason):
    reasons = [
        {"code": "GLOBAL_UNSAT", "message": unsat_reason, "count": 1}
    ]
    if warnings:
        reasons.append(
            {
                "code": "PREVALIDATION_WARNINGS_PRESENT",
                "message": "Des warnings de prévalidation ont été détectés.",
                "count": len(warnings),
            }
        )
    return reasons


def _date_matches_vacation_period(iso_date, vacation_periods):
    if not is_valid_date(iso_date):
        return False

    day_dt = datetime.strptime(iso_date, "%Y-%m-%d")
    for period in vacation_periods or []:
        if not isinstance(period, dict):
            continue
        start = period.get("start")
        end = period.get("end")
        if not start or not end:
            continue
        try:
            start_dt = datetime.strptime(start, "%d-%m-%Y")
            end_dt = datetime.strptime(end, "%d-%m-%Y")
        except ValueError:
            continue
        if start_dt <= day_dt <= end_dt:
            return True
    return False


def _agent_has_status_on_day(agent, iso_date):
    if not is_valid_date(iso_date):
        return False

    day_str = datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d-%m-%Y")
    if day_str in (agent.get("unavailable") or []):
        return True
    if day_str in (agent.get("training") or []):
        return True
    if _date_matches_vacation_period(iso_date, agent.get("vacations") or []):
        return True
    for restriction in agent.get("restrictions") or []:
        if isinstance(restriction, dict) and restriction.get("date") == day_str:
            return True
    return False


def _build_manual_shift_indexes(manual_entries):
    manual_shifts_by_agent_day = {}
    manual_counts_by_day_shift = {}
    dates_to_check = set()

    for entry in manual_entries:
        if entry.get("type") != "shift":
            continue
        iso_date = entry.get("date")
        agent_name = entry.get("agent")
        shift_value = entry.get("value")
        if not agent_name or not shift_value or not is_valid_date(iso_date):
            continue

        dates_to_check.add(iso_date)
        manual_shifts_by_agent_day.setdefault((agent_name, iso_date), []).append(shift_value)
        manual_counts_by_day_shift[(iso_date, shift_value)] = (
            manual_counts_by_day_shift.get((iso_date, shift_value), 0) + 1
        )

    return manual_shifts_by_agent_day, manual_counts_by_day_shift, dates_to_check


def _agent_can_cover_shift(agent, iso_date, vacation, manual_shifts_by_agent_day, runtime_config):
    agent_name = agent["name"]
    locked_shifts = manual_shifts_by_agent_day.get((agent_name, iso_date), [])
    if locked_shifts:
        return vacation in locked_shifts

    if _agent_has_status_on_day(agent, iso_date):
        return False
    restricted = set(agent.get("restriction") or [])
    if vacation in restricted:
        return False
    catalog = build_vacation_catalog(runtime_config)
    metadata = catalog["assignment_metadata"].get(vacation)
    if metadata and metadata.parent in restricted:
        return False
    return True

def _diagnose_manual_sequence_conflicts(manual_shifts_by_agent_day, runtime_config):
    reasons = []
    by_agent = {agent["name"]: agent for agent in runtime_config.get("agents", [])}
    details_by_code = {
        "MANUAL_CDP_WEEKLY_LIMIT_EXCEEDED": [],
        "MANUAL_SHIFT_AFTER_NIGHT": [],
        "MANUAL_NIGHT_BEFORE_UNAVAILABLE_OR_TRAINING": [],
        "MANUAL_SHIFT_AROUND_TRAINING_NOT_ALLOWED": [],
        "MANUAL_FULL_WEEKEND_COMPOSITION_CONFLICT": [],
    }
    counts_by_code = {code: 0 for code in details_by_code}
    catalog = build_vacation_catalog(runtime_config)

    weekly_counts = {}
    for (agent_name, iso_date), shifts in manual_shifts_by_agent_day.items():
        if agent_name not in by_agent or not is_valid_date(iso_date):
            continue
        week_key = (agent_name, datetime.strptime(iso_date, "%Y-%m-%d").isocalendar()[:2])
        weekly_counts.setdefault(week_key, {"CDP": 0})
        weekly_counts[week_key]["CDP"] += shifts.count("CDP")

    for (agent_name, week), counts in weekly_counts.items():
        if counts["CDP"] > 2:
            counts_by_code["MANUAL_CDP_WEEKLY_LIMIT_EXCEEDED"] += 1
            details_by_code["MANUAL_CDP_WEEKLY_LIMIT_EXCEEDED"].append(
                f"{agent_name} / semaine {week[1]}: {counts['CDP']} vacations CDP manuelles pour 2 maximum"
            )

    for (agent_name, iso_date), shifts in manual_shifts_by_agent_day.items():
        if agent_name not in by_agent or not is_valid_date(iso_date):
            continue
        agent = by_agent[agent_name]
        day_dt = datetime.strptime(iso_date, "%Y-%m-%d")
        previous_iso = (day_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        next_iso = (day_dt + timedelta(days=1)).strftime("%Y-%m-%d")
        next_day_str = (day_dt + timedelta(days=1)).strftime("%d-%m-%Y")

        rest_triggering_shifts = [
            shift for shift in shifts if requires_next_day_rest(catalog, shift)
        ]
        if rest_triggering_shifts:
            next_manual_shifts = manual_shifts_by_agent_day.get((agent_name, next_iso), [])
            if next_manual_shifts:
                counts_by_code["MANUAL_SHIFT_AFTER_NIGHT"] += 1
                details_by_code["MANUAL_SHIFT_AFTER_NIGHT"].append(
                    f"{agent_name} / {iso_date}: {', '.join(rest_triggering_shifts)} "
                    f"suivie de {', '.join(next_manual_shifts)} le {next_iso}"
                )
            if next_day_str in (agent.get("unavailable") or []) or next_day_str in (agent.get("training") or []):
                counts_by_code["MANUAL_NIGHT_BEFORE_UNAVAILABLE_OR_TRAINING"] += 1
                details_by_code["MANUAL_NIGHT_BEFORE_UNAVAILABLE_OR_TRAINING"].append(
                    f"{agent_name} / {iso_date}: affectation de nuit avant indisponibilité ou formation le {next_iso}"
                )

        if day_dt.weekday() == 5 and _agent_has_status_on_day(agent, next_iso):
            counts_by_code["MANUAL_FULL_WEEKEND_COMPOSITION_CONFLICT"] += 1
            details_by_code["MANUAL_FULL_WEEKEND_COMPOSITION_CONFLICT"].append(
                f"{agent_name}: vacation manuelle le samedi {iso_date}, mais dimanche {next_iso} bloqué"
            )
        if day_dt.weekday() == 6 and _agent_has_status_on_day(agent, previous_iso):
            counts_by_code["MANUAL_FULL_WEEKEND_COMPOSITION_CONFLICT"] += 1
            details_by_code["MANUAL_FULL_WEEKEND_COMPOSITION_CONFLICT"].append(
                f"{agent_name}: vacation manuelle le dimanche {iso_date}, mais samedi {previous_iso} bloqué"
            )

        if day_dt.strftime("%d-%m-%Y") in (agent.get("training") or []):
            previous_shifts = manual_shifts_by_agent_day.get((agent_name, previous_iso), [])
            next_shifts = manual_shifts_by_agent_day.get((agent_name, next_iso), [])
            forbidden_previous = [shift for shift in previous_shifts if shift != "CDP"]
            forbidden_next = [
                shift
                for shift in next_shifts
                if shift != "CDP" and not is_night_assignment(catalog, shift)
            ]
            if forbidden_previous or forbidden_next:
                counts_by_code["MANUAL_SHIFT_AROUND_TRAINING_NOT_ALLOWED"] += 1
                details_by_code["MANUAL_SHIFT_AROUND_TRAINING_NOT_ALLOWED"].append(
                    f"{agent_name} / formation {iso_date}: vacations incompatibles autour de la formation"
                )

    reason_messages = {
        "MANUAL_CDP_WEEKLY_LIMIT_EXCEEDED": "La limite de 2 vacations CDP par semaine est dépassée par des saisies manuelles.",
        "MANUAL_SHIFT_AFTER_NIGHT": "Une vacation manuelle est posée le lendemain d'une Nuit manuelle.",
        "MANUAL_NIGHT_BEFORE_UNAVAILABLE_OR_TRAINING": "Une Nuit manuelle est posée avant une indisponibilité ou une formation.",
        "MANUAL_SHIFT_AROUND_TRAINING_NOT_ALLOWED": "Une vacation manuelle ne respecte pas les règles de veille/lendemain de formation.",
        "MANUAL_FULL_WEEKEND_COMPOSITION_CONFLICT": "Une saisie manuelle empêche de respecter la règle de week-end complet.",
    }
    for code, count in counts_by_code.items():
        if count:
            reasons.append(
                {
                    "code": code,
                    "message": reason_messages[code],
                    "count": count,
                    "details": details_by_code[code][:5],
                }
            )

    return reasons


def _diagnose_staffing_capacity_conflicts(
    runtime_config, manual_shifts_by_agent_day, manual_counts_by_day_shift, dates_to_check
):
    reasons = []
    agents = runtime_config.get("agents", [])
    staffing_requirements = runtime_config.get("staffing_requirements", {})
    holidays = set(runtime_config.get("holidays", []))
    catalog = build_vacation_catalog(runtime_config)

    understaffed_shift_days = 0
    overstaffed_manual_shift_days = 0
    understaffed_details = []
    overstaffed_details = []

    for iso_date in sorted(dates_to_check):
        day_dt = datetime.strptime(iso_date, "%Y-%m-%d")
        day_token = day_dt.strftime("%d-%m")
        is_weekend = day_dt.weekday() >= 5
        for vacation in catalog["coverage_vacations"]:
            required_agents = staffing_requirements.get(vacation, 1)
            if vacation == "CDP" and (is_weekend or day_token in holidays):
                required_agents = 0

            for segment in catalog["coverage_segments"].get(vacation, [vacation]):
                covering_assignments = catalog["segment_covering_assignments"].get(
                    (vacation, segment), [vacation]
                )
                manual_count = sum(
                    manual_counts_by_day_shift.get((iso_date, assignment), 0)
                    for assignment in covering_assignments
                )
                if manual_count > required_agents:
                    overstaffed_manual_shift_days += 1
                    overstaffed_details.append(
                        f"{iso_date} / {vacation} / {segment}: "
                        f"{manual_count} manuel(s) pour {required_agents} requis"
                    )
                    continue

                eligible_count = sum(
                    1
                    for agent in agents
                    if any(
                        _agent_can_cover_shift(
                            agent,
                            iso_date,
                            assignment,
                            manual_shifts_by_agent_day,
                            runtime_config,
                        )
                        for assignment in covering_assignments
                    )
                )
                if eligible_count < required_agents:
                    understaffed_shift_days += 1
                    understaffed_details.append(
                        f"{iso_date} / {vacation} / {segment}: "
                        f"{eligible_count} agent(s) possible(s) pour {required_agents} requis"
                    )

    if overstaffed_manual_shift_days:
        reasons.append(
            {
                "code": "MANUAL_SHIFT_EXCEEDS_STAFFING_REQUIREMENT",
                "message": (
                    "Trop d'affectations manuelles sont posées sur au moins un "
                    "segment par rapport au besoin configuré."
                ),
                "count": overstaffed_manual_shift_days,
                "details": overstaffed_details[:5],
            }
        )
    if understaffed_shift_days:
        reasons.append(
            {
                "code": "STAFFING_REQUIREMENT_UNMET",
                "message": (
                    "Le besoin de couverture ne peut pas être atteint pour au moins "
                    "un segment avec les agents encore disponibles."
                ),
                "count": understaffed_shift_days,
                "details": understaffed_details[:5],
            }
        )

    return reasons


RELAXED_CONSTRAINT_DIAGNOSTICS = [
    {
        "constraint": "limit_one_shift_per_day",
        "label": "une seule vacation par agent et par jour",
        "detail": "Un agent aurait probablement besoin de couvrir plusieurs vacations le même jour.",
    },
    {
        "constraint": "require_at_least_one_shift_per_agent",
        "label": "au moins une vacation par agent",
        "detail": "Tous les agents ne peuvent peut-être pas recevoir au moins une vacation sur la période.",
    },
    {
        "constraint": "cover_daily_shifts",
        "label": "couverture quotidienne des besoins",
        "detail": "Le nombre d'agents requis par date/vacation semble incompatible avec les disponibilités restantes.",
    },
    {
        "constraint": "enforce_full_weekend_composition",
        "label": "week-end complet",
        "detail": "La règle samedi/dimanche travaillés ensemble semble bloquer une combinaison possible.",
    },
    {
        "constraint": "enforce_min_free_weekends_per_horizon",
        "label": "minimum de week-ends libres",
        "detail": "Le minimum de week-ends libres demandé semble trop contraignant sur cette période.",
    },
    {
        "constraint": "avoid_day_after_night",
        "label": "repos après une Nuit",
        "detail": "Une affectation le lendemain d'une Nuit semble nécessaire pour trouver une solution.",
    },
    {
        "constraint": "limit_cdp_per_week",
        "label": "limite CDP hebdomadaire",
        "detail": "La limite de vacations CDP par semaine semble bloquer la couverture.",
    },
    {
        "constraint": "block_unavailable_days",
        "label": "indisponibilités",
        "detail": "Relâcher les indisponibilités rendrait le planning faisable, ce qui indique un manque de capacité disponible.",
    },
    {
        "constraint": "block_training_days",
        "label": "formations",
        "detail": "Relâcher les jours de formation rendrait le planning faisable, ce qui indique un manque de capacité disponible.",
    },
    {
        "constraint": "block_leave_and_compute_paid_hours",
        "label": "congés",
        "detail": "Relâcher les congés rendrait le planning faisable, ce qui indique un manque de capacité disponible.",
    },
    {
        "constraint": "block_night_before_unavailable",
        "label": "Nuit avant indisponibilité",
        "detail": "Une Nuit avant une indisponibilité semble nécessaire pour trouver une solution.",
    },
    {
        "constraint": "block_night_before_training",
        "label": "Nuit avant formation",
        "detail": "Une Nuit avant une formation semble nécessaire pour trouver une solution.",
    },
    {
        "constraint": "limit_pre_post_training",
        "label": "veille/lendemain de formation",
        "detail": "Les règles autour des formations semblent empêcher une solution.",
    },
    {
        "constraint": "block_exclusion_days",
        "label": "jours d'exclusion",
        "detail": "Relâcher les jours d'exclusion rendrait le planning faisable.",
    },
    {
        "constraint": "block_monday_night_after_weekend_nights",
        "label": "Nuit du lundi après nuits de week-end",
        "detail": "La règle de Nuit du lundi après nuits de week-end semble bloquer une solution.",
    },
    {
        "constraint": "apply_agent_restrictions",
        "label": "restrictions agent",
        "detail": "Relâcher les restrictions agent rendrait le planning faisable.",
    },
]


def _probe_relaxed_hard_constraints(planning_payload, runtime_config):
    reasons = []

    for diagnostic in RELAXED_CONSTRAINT_DIAGNOSTICS:
        probe_config = deepcopy(runtime_config)
        probe_config["_disabled_hard_constraints_for_diagnostics"] = [diagnostic["constraint"]]
        solver_config = probe_config.setdefault("solver", {})
        try:
            current_timeout = int(solver_config.get("max_time_seconds", 3))
        except (TypeError, ValueError):
            current_timeout = 3
        solver_config["max_time_seconds"] = max(1, min(current_timeout, 3))

        _, probe_status = _build_planning_payload(
            payload=planning_payload,
            runtime_config=probe_config,
        )
        if probe_status == 200:
            reasons.append(
                {
                    "code": "RELAXED_CONSTRAINT_MAKES_FEASIBLE",
                    "message": (
                        "Une solution devient possible si la contrainte "
                        f"« {diagnostic['label']} » est relâchée. "
                        "C'est donc une piste de blocage prioritaire."
                    ),
                    "count": 1,
                    "details": [diagnostic["detail"]],
                }
            )

    return reasons[:5]


def _diagnose_manual_entry_conflicts(manual_entries, runtime_config):
    reasons = []
    by_agent = {agent["name"]: agent for agent in runtime_config.get("agents", [])}
    (
        manual_shifts_by_agent_day,
        manual_counts_by_day_shift,
        dates_to_check,
    ) = _build_manual_shift_indexes(manual_entries)

    seen_agent_day = set()
    duplicate_count = 0
    unavailable_conflicts = 0
    training_conflicts = 0
    restriction_conflicts = 0
    vacation_conflicts = 0

    for entry in manual_entries:
        if entry.get("type") != "shift":
            continue
        agent_name = entry.get("agent")
        iso_date = entry.get("date")
        shift_value = entry.get("value")
        if agent_name not in by_agent or not is_valid_date(iso_date):
            continue
        agent = by_agent[agent_name]
        day_str = datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d-%m-%Y")

        key = (agent_name, iso_date)
        if key in seen_agent_day:
            duplicate_count += 1
        else:
            seen_agent_day.add(key)

        if day_str in (agent.get("unavailable") or []):
            unavailable_conflicts += 1
        if day_str in (agent.get("training") or []):
            training_conflicts += 1
        if shift_value in (agent.get("restriction") or []):
            restriction_conflicts += 1
        if _date_matches_vacation_period(iso_date, agent.get("vacations") or []):
            vacation_conflicts += 1

    if duplicate_count:
        reasons.append(
            {
                "code": "MULTIPLE_MANUAL_SHIFTS_SAME_DAY",
                "message": "Plusieurs vacations manuelles ont été saisies pour un même agent et un même jour.",
                "count": duplicate_count,
            }
        )
    if unavailable_conflicts:
        reasons.append(
            {
                "code": "MANUAL_SHIFT_ON_UNAVAILABLE_DAY",
                "message": "Une vacation manuelle a été posée sur un jour d'indisponibilité.",
                "count": unavailable_conflicts,
            }
        )
    if training_conflicts:
        reasons.append(
            {
                "code": "MANUAL_SHIFT_ON_TRAINING_DAY",
                "message": "Une vacation manuelle a été posée sur un jour de formation.",
                "count": training_conflicts,
            }
        )
    if vacation_conflicts:
        reasons.append(
            {
                "code": "MANUAL_SHIFT_DURING_VACATION",
                "message": "Une vacation manuelle a été posée pendant une période de congé.",
                "count": vacation_conflicts,
            }
        )
    if restriction_conflicts:
        reasons.append(
            {
                "code": "MANUAL_SHIFT_MATCHES_AGENT_RESTRICTION",
                "message": "Une vacation manuelle correspond à une restriction agent.",
                "count": restriction_conflicts,
            }
        )

    reasons.extend(_diagnose_manual_sequence_conflicts(manual_shifts_by_agent_day, runtime_config))
    reasons.extend(
        _diagnose_staffing_capacity_conflicts(
            runtime_config,
            manual_shifts_by_agent_day,
            manual_counts_by_day_shift,
            dates_to_check,
        )
    )

    return reasons


@app.route("/previous-week-schedule", methods=["POST"])
def compute_previous_week_schedule():
    payload, payload_error = parse_json_object_payload()
    if payload_error is not None:
        return payload_error

    # Check if the start_date is present in the query
    if "start_date" not in payload:
        return jsonify({"error": "Missing start_date"}), 400
    # Check that the date is valid
    if not is_valid_date(payload["start_date"]):
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    start_date = payload["start_date"]
    previous_week_schedule = get_previous_week_schedule(start_date)

    runtime_config = get_active_config()
    agents = runtime_config["agents"]
    assignable_vacations = build_vacation_catalog(runtime_config)["assignable_vacations"]
    return jsonify({
        "previous_week_schedule": previous_week_schedule,
        "agents": agents,
        "assignable_vacations": assignable_vacations,
    })


@app.route("/optimize-existing-planning", methods=["POST"])
def optimize_existing_planning_route():
    payload, payload_error = parse_json_object_payload()
    if payload_error is not None:
        return payload_error

    runtime_config = get_active_config()
    start_date, end_date, date_error = _validate_date_range_payload(payload)
    if date_error is not None:
        return date_error

    initial_shifts, status_entries, warnings, entries_error = _parse_manual_entries(
        payload.get("manual_entries", []), runtime_config, start_date, end_date
    )
    if entries_error is not None:
        return entries_error
    effective_runtime_config, status_warnings = _inject_manual_status_entries(
        runtime_config, status_entries
    )
    warnings.extend(status_warnings)

    result, status_code = _build_planning_payload(
        payload={
            "start_date": payload["start_date"],
            "end_date": payload["end_date"],
            "initial_shifts": initial_shifts,
        },
        runtime_config=effective_runtime_config,
    )
    manual_entries = payload.get("manual_entries", [])
    if status_code != 200:
        unsat_reason = result.get("info") or result.get("error") or "No solution found."
        blocking_reasons = _build_blocking_reasons_from_context(
            manual_entries=manual_entries,
            warnings=warnings,
            unsat_reason=unsat_reason,
        )
        diagnostic_reasons = _diagnose_manual_entry_conflicts(
            manual_entries=manual_entries,
            runtime_config=effective_runtime_config,
        )
        if diagnostic_reasons:
            blocking_reasons.extend(diagnostic_reasons)
        else:
            relaxed_constraint_reasons = _probe_relaxed_hard_constraints(
                planning_payload={
                    "start_date": payload["start_date"],
                    "end_date": payload["end_date"],
                    "initial_shifts": initial_shifts,
                },
                runtime_config=effective_runtime_config,
            )
            if relaxed_constraint_reasons:
                blocking_reasons.extend(relaxed_constraint_reasons)
            elif manual_entries:
                blocking_reasons.append(
                    {
                        "code": "MANUAL_ASSIGNMENTS_IMPACT_UNKNOWN",
                        "message": (
                            "Aucune contradiction directe n'a été détectée sur les cellules manuelles. "
                            "Le blocage vient probablement d'une combinaison de contraintes globales."
                        ),
                        "count": len(manual_entries),
                    }
                )
        suggestions = _build_suggestions_from_context(
            manual_entries=manual_entries,
            warnings=warnings,
            unsat_reason=unsat_reason,
            blocking_reasons=blocking_reasons,
        )
        impacted_cells = [
            {
                "agent": entry.get("agent"),
                "date": entry.get("date"),
                "slot": entry.get("slot", "day"),
                "value": entry.get("value"),
            }
            for entry in manual_entries
        ]
        return (
            jsonify(
                {
                    "status": "unsat",
                    "error": unsat_reason,
                    "warnings": warnings,
                    "blocking_reasons": blocking_reasons,
                    "impacted_cells": impacted_cells,
                    "suggestions": suggestions,
                    "meta": {
                        "manual_cell_count": len(manual_entries),
                        "conflict_count": len(warnings),
                    },
                }
            ),
            status_code,
        )
    status = "warning" if warnings else "ok"
    suggestions = _build_suggestions_from_context(
        manual_entries=manual_entries,
        warnings=warnings,
    )
    result["status"] = status
    result["warnings"] = warnings
    result["suggestions"] = suggestions
    result["meta"] = {
        "manual_cell_count": len(manual_entries),
        "conflict_count": len(warnings),
    }
    return jsonify(result)


def get_previous_week_schedule(start_date_str):
    try:
        # Convert the string into a datetime object
        start_date = datetime.strptime(
            start_date_str, "%Y-%m-%d"
        )  # Format date / ISO 8601
    except ValueError as e:
        raise ValueError("Invalid date format. Use YYYY-MM-DD.") from e

    previous_week_start = start_date - timedelta(days=7)

    # Calculate the days of the previous week
    return [
        format_day_label(previous_week_start + timedelta(days=i))
        for i in range(7)
    ]  # Format: Shortened day + Date (e.g. Lun 25-12)


def get_week_schedule(start_date_str, end_date_str):
    # Convert strings into datetime objects
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")  # Format date / ISO 8601
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")  # Format date / ISO 8601

    # Calculate the days between the start date and the end date
    delta = end_date - start_date
    return [
        format_day_label(start_date + timedelta(days=i))
        for i in range(delta.days + 1)
    ]  # Format : Shortened day + Date (e.g. Lun 25-12)


def format_day_label(day_date):
    day_name = FRENCH_WEEKDAY_ABBREVIATIONS[day_date.weekday()]
    return f"{day_name}. {day_date.strftime('%d-%m')}"


def split_into_weeks(week_schedule):
    # Divide the list of days into calendar weeks (Monday to Sunday)
    weeks = []
    current_week = []

    for day in week_schedule:
        # Add the day to the current week
        current_week.append(day)

        # If the day is a Sunday or the last day of the schedule, end the week
        day_name = day.split(" ")[0]  # Extract the name of the day (e.g. Lun.)
        if day_name == "Dim." or day == week_schedule[-1]:  # Sunday or last day
            weeks.append(current_week)
            current_week = []

    return weeks


def split_by_month_or_period(week_schedule):
    # Divides week_schedule into monthly or single periods according to duration
    periods = []
    current_period = []
    previous_month = None

    for day in week_schedule:
        # Extract month (format: Lun 25-12)
        current_month = day.split(" ")[1].split("-")[1]  # Extract the month (e.g. 12)

        # If the month changes, start a new period
        if previous_month and current_month != previous_month:
            periods.append(current_period)
            current_period = []
        current_period.append(day)
        previous_month = current_month

    # Add the last period
    if current_period:
        periods.append(current_period)

    return periods


def _resolve_day_date_from_reference(day_part, reference_date):
    day_value = int(day_part.split("-")[0])
    month_value = int(day_part.split("-")[1])

    candidates = []
    for year in [reference_date.year - 1, reference_date.year, reference_date.year + 1]:
        try:
            candidates.append(datetime(year, month_value, day_value))
        except ValueError:
            continue

    if not candidates:
        return None

    return min(candidates, key=lambda candidate: abs((candidate - reference_date).days))


def is_vacation_day(agent_name, day, dayOff, planning_start_date=None):
    """Checks whether the day corresponds to leave for the agent,
    by checking all the periods defined in dayOff."""
    if agent_name in dayOff:
        day_part = day.split(" ")[1]  # Extract the date (e.g. 25-12)
        for period in dayOff[agent_name]:
            vacation_start, vacation_end = period  # Extract the start and end dates
            # Convert holiday dates and the day into datetime objects for comparison
            vacation_start_date = datetime.strptime(vacation_start, "%d-%m-%Y")
            vacation_end_date = datetime.strptime(vacation_end, "%d-%m-%Y")
            try:
                if planning_start_date is not None:
                    if isinstance(planning_start_date, str):
                        reference_date = datetime.strptime(planning_start_date, "%Y-%m-%d")
                    else:
                        reference_date = planning_start_date
                    day_date = _resolve_day_date_from_reference(day_part, reference_date)
                    if day_date is None:
                        continue
                else:
                    day_date = datetime.strptime(
                        f"{day_part}-{vacation_start_date.year}", "%d-%m-%Y"
                    )
            except ValueError:
                continue
            # Check if the day is between the holiday start and end dates
            if vacation_start_date <= day_date <= vacation_end_date:
                return True
    return False


def is_weekend(day):
    """Determines whether a day is Saturday or Sunday."""
    day_name = day.split(" ")[0].rstrip(".")  # Extract the name of the day (e.g. Lun.)
    return day_name in ["Sam", "Dim"]  # Check if it's Saturday or Sunday


def split_date_range_by_month(start: datetime, end: datetime) -> list:
    """
    Splits a datetime range into contiguous monthly periods.
    Each period starts from the current date and ends on the last day of that month (or the specified end date,
    whichever comes first).

    Args:
        start (datetime): The starting datetime of the range.
        end (datetime): The ending datetime of the range.

    Returns:
        List[Tuple[datetime, datetime]]: A list of tuples where each tuple represents the start and end datetimes
        of a monthly period. The function partitions the range such that each period covers the span from the current
        date to the last day of that month (or the specified end date, whichever comes first).

    Notes:
        - If the specified range spans multiple months, the function divides the range into one or more periods where
        each period corresponds to a full month segment, except possibly the last one.
        - The function assumes that start <= end.
    """
    periods = []
    current = start

    while current <= end:
        # first day of the following month
        if current.month == 12:
            next_month = datetime(current.year + 1, 1, 1)
        else:
            next_month = datetime(current.year, current.month + 1, 1)
        # last day of the current period
        last = min(end, next_month - timedelta(days=1))

        periods.append((current, last))
        current = last + timedelta(days=1)

    return periods


def generate_planning(
    agents,
    vacations,
    week_schedule,
    dayOff,
    previous_week_schedule,
    initial_shifts,
    planning_start_date=None,
    runtime_config=None,
):
    # Public facade kept stable for existing route and tests.
    effective_runtime_config = runtime_config or get_active_config()
    return generate_planning_engine(
        agents=agents,
        vacations=vacations,
        week_schedule=week_schedule,
        dayOff=dayOff,
        previous_week_schedule=previous_week_schedule,
        initial_shifts=initial_shifts,
        runtime_config=effective_runtime_config,
        planning_start_date=planning_start_date,
    )

set_active_config(get_active_config())

if __name__ == "__main__":
    app.run(debug=True)
