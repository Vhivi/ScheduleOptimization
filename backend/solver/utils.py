from datetime import date, datetime, time, timedelta


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


def _parse_time_of_day(value: str) -> time:
    return datetime.strptime(value, "%H:%M").time()


def weekly_hour_contribution_tenths(day_date, metadata, fallback_duration, week_key):
    """Return assignment hours that belong to an ISO week, in tenths of hours."""
    if not day_date or not metadata or not metadata.start_time or not metadata.end_time:
        return fallback_duration if day_date and day_date.isocalendar()[:2] == week_key else 0

    start_time = _parse_time_of_day(metadata.start_time)
    end_time = _parse_time_of_day(metadata.end_time)
    start_at = datetime.combine(day_date.date(), start_time)
    end_at = datetime.combine(day_date.date(), end_time)
    if end_at <= start_at:
        end_at += timedelta(days=1)

    week_monday = date.fromisocalendar(week_key[0], week_key[1], 1)
    week_start = datetime.combine(week_monday, time.min)
    week_end = week_start + timedelta(days=7)

    overlap_start = max(start_at, week_start)
    overlap_end = min(end_at, week_end)
    if overlap_end <= overlap_start:
        return 0
    return int(round((overlap_end - overlap_start).total_seconds() / 360))
