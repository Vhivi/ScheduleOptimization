import json
import os
from datetime import datetime, timedelta

from flask import Flask, jsonify, request
from flask_cors import CORS
from solver.engine import generate_planning as generate_planning_engine

app = Flask(__name__)
CORS(app)


@app.route("/config")
# Loading the configuration file
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            "Missing backend/config.json. Copy backend/config.example.json to "
            "backend/config.json and adjust it for your local environment."
        )
    with open(config_path, "r", encoding="utf-8") as config_file:
        return json.load(config_file)


config = load_config()
weekend_days = ["Sam", "Dim"]  # Shortened weekend days
holidays = config[
    "holidays"
]  # Public holidays to be updated each year, in particular for Easter Monday
FRENCH_WEEKDAY_ABBREVIATIONS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]


@app.route("/")
def home():
    return "Hello, Flask is up and running!"


@app.route("/generate-planning", methods=["POST"])
def generate_planning_route():
    payload, payload_error = parse_json_object_payload()
    if payload_error is not None:
        return payload_error

    # Retrieving data from the JSON file
    agents = config["agents"]
    vacations = config["vacations"]
    vacation_durations = config["vacation_durations"]
    holidays = config["holidays"]
    unavailable = {}
    dayOff = {}
    training = {}

    # Retrieve agent training days and store them in a dictionary {agent: [days]}.
    for agent in agents:
        if "training" in agent:
            training[agent["name"]] = agent["training"]

    # Retrieve agent unavailability days and store them in a dictionary {agent: [days]}.
    for agent in agents:
        if "unavailable" in agent:
            unavailable[agent["name"]] = agent["unavailable"]

    # Recovering employees' leave days
    for agent in agents:
        # Check if the agent has leave days
        if "vacations" in agent:
            dayOff[agent["name"]] = []
            # Browse each leave day period
            for vac in agent["vacations"]:
                # Check if the leave period is a dictionary and contains the start and end keys
                if isinstance(vac, dict) and "start" in vac and "end" in vac:
                    # Store leave days in a dictionary {agent: [start, end]}
                    dayOff[agent["name"]].append([vac["start"], vac["end"]])

    # Retrieve start and end dates
    # Check whether the dates are present in the payload
    if "start_date" not in payload or "end_date" not in payload:
        return jsonify({"error": "Missing start_date or end_date"}), 400
    
    # Check that the dates are valid
    if not is_valid_date(payload["start_date"]) or not is_valid_date(payload["end_date"]):
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    # Retrieve the complete schedule in several periods
    start_date = datetime.strptime(
        payload["start_date"], "%Y-%m-%d"
    )  # Format date / ISO 8601
    end_date = datetime.strptime(
        payload["end_date"], "%Y-%m-%d"
    )  # Format date / ISO 8601
    if end_date < start_date:
        return jsonify({"error": "end_date must be greater than or equal to start_date"}), 400

    periods = split_date_range_by_month(start_date, end_date)

    full_planning = {}
    for agent in agents:
        agent_name = agent["name"]
        full_planning[agent_name] = []

    # Retrieve initial shifts, if supplied otherwise default to an empty dictionary
    initial_shifts = payload.get("initial_shifts", {})
    if not isinstance(initial_shifts, dict):
        return jsonify({"error": "initial_shifts must be an object"}), 400

    # Validate initial shifts
    valid_agents = [agent["name"] for agent in agents]
    valid_vacations = vacations
    for agent_name, shifts in initial_shifts.items():
        if not isinstance(shifts, list):
            return jsonify({"error": f"initial_shifts for {agent_name} must be a list"}), 400
        if agent_name not in valid_agents:
            return jsonify({"error": f"Invalid agent: {agent_name}"}), 400
        for shift in shifts:
            if (
                not isinstance(shift, (list, tuple))
                or len(shift) != 2
                or not isinstance(shift[0], str)
                or not isinstance(shift[1], str)
            ):
                return (
                    jsonify(
                        {
                            "error": (
                                "Each initial shift must be [day, vacation] with string values"
                            )
                        }
                    ),
                    400,
                )
            _, vacation = shift
            if vacation not in valid_vacations:
                return jsonify({"error": f"Invalid vacation: {vacation}"}), 400

    for chunk_start, chunk_end in periods:
        # Convert the start and end dates into strings
        start_date_str = chunk_start.strftime("%Y-%m-%d")
        end_date_str = chunk_end.strftime("%Y-%m-%d")

        # Calculate the list of days from dates
        week_schedule = get_week_schedule(start_date_str, end_date_str)
        previous_week_schedule = get_previous_week_schedule(start_date_str)

        # Calling up the schedule generation function
        result = generate_planning(
            agents,
            vacations,
            week_schedule,
            dayOff,
            previous_week_schedule,
            initial_shifts,
        )

        # If the result is a dict with an info key, return a 400 error.
        if "info" in result:
            return jsonify(result), 400

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
    return jsonify(
        {
            "planning": full_planning,
            "vacation_durations": vacation_durations,
            "week_schedule": original_week_schedule,
            "holidays": holidays,
            "unavailable": unavailable,
            "dayOff": dayOff,
            "training": training,
        }
    )


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

    agents = config["agents"]
    return jsonify({"previous_week_schedule": previous_week_schedule, "agents": agents})


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


def is_vacation_day(agent_name, day, dayOff):
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
                day_date = datetime.strptime(
                    f"{day_part}-{vacation_start_date.year}", "%d-%m-%Y"
                )
            except ValueError:
                continue
            # Check if the day is between the holiday start and end dates
            if vacation_start_date <= day_date <= vacation_end_date and not is_weekend(
                day
            ):
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
    agents, vacations, week_schedule, dayOff, previous_week_schedule, initial_shifts
):
    # Public facade kept stable for existing route and tests.
    return generate_planning_engine(
        agents=agents,
        vacations=vacations,
        week_schedule=week_schedule,
        dayOff=dayOff,
        previous_week_schedule=previous_week_schedule,
        initial_shifts=initial_shifts,
        runtime_config=config,
    )

if __name__ == "__main__":
    app.run(debug=True)
