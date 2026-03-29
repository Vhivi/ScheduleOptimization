from datetime import datetime


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
