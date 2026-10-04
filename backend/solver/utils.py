from datetime import date, datetime, time, timedelta


def external_assignment_type_durations(config):
    """Return canonical external-assignment durations with legacy fallback."""
    return config.get(
        "external_assignment_types_durations",
        config.get("restriction_types_durations", {}),
    )


def split_into_weeks(week_schedule):
    """
    Splits a list of days into separate weeks.

    This function takes a list of days in the format "Day. dd-mm" and splits it into
    separate lists, each representing a week. The splitting is done based on the day of
    the week, with each week ending on Sunday and starting on Monday.

    :param week_schedule: A list of days in the format "Day. dd-mm".
    :type week_schedule: list[str]
    :return: A list of lists, each representing a week
    :rtype: list[list[str]]
    """
    weeks = []
    current_week = []

    for day in week_schedule:
        current_week.append(day)
        day_name = day.split(" ")[0]
        if day_name == "Dim." or day == week_schedule[-1]:
            weeks.append(current_week)
            current_week = []

    return weeks


def split_by_month_or_period(week_schedule):
    """
    Splits a list of days into separate periods based on the month.

    This function takes a list of days in the format "Day. dd-mm" and splits it into
    separate lists, each representing a period. The splitting is done based on the month,
    with each period containing all the days of a single month.

    :param week_schedule: A list of days in the format "Day. dd-mm"
    :type week_schedule: list[str]
    :return: A list of lists, each representing a period
    :rtype: list[list[str]]
    """
    periods = []
    current_period = []
    previous_month = None

    for day in week_schedule:
        current_month = day.split(" ")[1].split("-")[1]
        if previous_month and current_month != previous_month:
            periods.append(current_period)
            current_period = []
        current_period.append(day)
        previous_month = current_month

    if current_period:
        periods.append(current_period)

    return periods


def day_token(date_full: str) -> str:
    """
    Returns a shortened version of the given date string.

    The shortened version is in the format "dd-mm" and is obtained by parsing the given
    date string in the format "dd-mm-yyyy" and reformatting it.

    :param date_full: A date string in the format "dd-mm-yyyy"
    :type date_full: str
    :return: A shortened version of the given date string
    :rtype: str
    """
    return datetime.strptime(date_full, "%d-%m-%Y").strftime("%d-%m")


def find_training_leave_overlap(agent: dict) -> str | None:
    """Return the first training date included in a leave period."""
    training_dates = sorted(
        datetime.strptime(value, "%d-%m-%Y")
        for value in agent.get("training", [])
    )
    for period in agent.get("vacations", []):
        if not isinstance(period, dict) or "start" not in period or "end" not in period:
            continue
        start = datetime.strptime(period["start"], "%d-%m-%Y")
        end = datetime.strptime(period["end"], "%d-%m-%Y")
        for training_date in training_dates:
            if start <= training_date <= end:
                return training_date.strftime("%d-%m-%Y")
    return None


def _parse_time_of_day(value: str) -> time:
    return datetime.strptime(value, "%H:%M").time()


def datetime_interval(day_date: datetime, start_time: str, end_time: str):
    """Return a dated interval, carrying overnight work into the next day."""
    start_at = datetime.combine(day_date.date(), _parse_time_of_day(start_time))
    end_at = datetime.combine(day_date.date(), _parse_time_of_day(end_time))
    if end_at <= start_at:
        end_at += timedelta(days=1)
    return start_at, end_at


WEEKDAY_NAMES = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def assignment_overlaps_weekdays(day_date, metadata, weekdays) -> bool:
    """Return whether an assignment overlaps one of the selected weekdays."""
    if not weekdays:
        return False

    is_night = bool(metadata and metadata.is_night)
    start_time = getattr(metadata, "start_time", None) or (
        "19:00" if is_night else "07:00"
    )
    end_time = getattr(metadata, "end_time", None) or (
        "07:00" if is_night else "19:00"
    )
    start_at, end_at = datetime_interval(day_date, start_time, end_time)
    last_date = (end_at - timedelta(microseconds=1)).date()
    current_date = start_at.date()
    avoided = set(weekdays)

    while current_date <= last_date:
        if WEEKDAY_NAMES[current_date.weekday()] in avoided:
            return True
        current_date += timedelta(days=1)
    return False


def violates_day_night_rest(
    previous_interval,
    previous_is_night: bool,
    next_interval,
    next_is_night: bool,
) -> bool:
    """Apply the shared 24h day-to-night and 48h night-to-day rule."""
    previous_start, previous_end = previous_interval
    next_start, _ = next_interval
    if next_start <= previous_start or previous_is_night == next_is_night:
        return False
    required_rest = timedelta(hours=48 if previous_is_night else 24)
    return next_start - previous_end < required_rest


def interval_hour_contribution_tenths(
    day_date, metadata, fallback_duration, interval_start, interval_end
):
    """Return assignment hours overlapping a datetime interval, in tenths."""
    if not day_date or not metadata or not metadata.start_time or not metadata.end_time:
        return (
            fallback_duration
            if day_date and interval_start.date() <= day_date.date() < interval_end.date()
            else 0
        )

    start_at, end_at = datetime_interval(
        day_date, metadata.start_time, metadata.end_time
    )
    overlap_start = max(start_at, interval_start)
    overlap_end = min(end_at, interval_end)
    if overlap_end <= overlap_start:
        return 0
    return int(round((overlap_end - overlap_start).total_seconds() / 360))


def weekly_hour_contribution_tenths(day_date, metadata, fallback_duration, week_key):
    """Return assignment hours that belong to an ISO week, in tenths of hours."""
    week_monday = date.fromisocalendar(week_key[0], week_key[1], 1)
    week_start = datetime.combine(week_monday, time.min)
    return interval_hour_contribution_tenths(
        day_date,
        metadata,
        fallback_duration,
        week_start,
        week_start + timedelta(days=7),
    )
