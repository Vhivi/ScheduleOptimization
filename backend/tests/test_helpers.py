import pytest
from app import (
    get_week_schedule,
    is_vacation_day,
    is_valid_date,
    is_weekend,
    split_by_month_or_period,
    split_into_weeks,
)


def test_is_valid_date_valid():
    """
    Test the is_valid_date function with valid date strings.

    This test case checks if the is_valid_date function correctly identifies
    valid dates, including a regular date, a date at the end of February in a
    non-leap year, and a leap year date.

    Asserts:
        - The function should return True for the date "2023-10-15".
        - The function should return True for the date "2022-02-28".
        - The function should return True for the date "2020-02-29" (leap year).
    """

    assert is_valid_date("2023-10-15") is True
    assert is_valid_date("2022-02-28") is True
    assert is_valid_date("2020-02-29") is True  # Leap year


def test_is_valid_date_invalid_format():
    """
    Test the is_valid_date function with invalid date formats.

    This test ensures that the is_valid_date function correctly identifies
    dates that do not match the expected format and returns False for them.

    Test cases:
    - "15-10-2023": Date with dashes instead of slashes.
    - "2023/10/15": Date with slashes but in the wrong order (YYYY/MM/DD).
    - "20231015": Date without any separators.

    Asserts:
    - The function should return False for each of the invalid date formats.
    """

    assert is_valid_date("15-10-2023") is False
    assert is_valid_date("2023/10/15") is False
    assert is_valid_date("20231015") is False


def test_is_valid_date_invalid_date():
    """
    Test the is_valid_date function with invalid dates.

    This test case checks the following invalid dates:
    - "2023-02-30": February 30th does not exist.
    - "2021-04-31": April has only 30 days.
    - "2019-02-29": 2019 is not a leap year, so February has only 28 days.

    The function is expected to return False for all these cases.
    """

    assert is_valid_date("2023-02-30") is False  # Invalid day
    assert is_valid_date("2021-04-31") is False  # Invalid day
    assert is_valid_date("2019-02-29") is False  # Not a leap year


def test_is_valid_date_empty_string():
    """
    Test the is_valid_date function with an empty string.

    This test ensures that the is_valid_date function returns False
    when provided with an empty string as input.
    """

    assert is_valid_date("") is False


def test_is_valid_date_none():
    """
    Test the is_valid_date function with a None input.

    This test ensures that the is_valid_date function returns False when
    the input is None, indicating that None is not considered a valid date.
    """

    assert is_valid_date(None) is False


def test_get_week_schedule():
    """
    Test the get_week_schedule function.

    This test verifies that the get_week_schedule function returns the correct
    schedule for a given week. The schedule should include all days from the
    start_date to the end_date in the expected format.

    Test cases:
    - start_date: "2023-10-01"
    - end_date: "2023-10-07"
    - expected_schedule: [...], a list of formatted date strings for each day of the week.

    Assertions:
    - The length of the result should be 7.
    - The result should match the expected_schedule.
    """

    start_date = "2023-10-01"
    end_date = "2023-10-07"
    expected_schedule = [
        "Dim. 01-10",
        "Lun. 02-10",
        "Mar. 03-10",
        "Mer. 04-10",
        "Jeu. 05-10",
        "Ven. 06-10",
        "Sam. 07-10",
    ]
    result = get_week_schedule(start_date, end_date)
    assert len(result) == 7
    assert result == expected_schedule


def test_get_week_schedule_single_day():
    """
    Test the get_week_schedule function for a single day.

    This test case checks if the function correctly handles the scenario where the
    start date and end date are the same, representing a single day. It verifies
    that the function returns the expected schedule for that day.

    Asserts:
        - The result of get_week_schedule(start_date, end_date) should match the
          expected_schedule, which is a list containing the formatted date string
          for the single day.
    """

    start_date = "2023-10-01"
    end_date = "2023-10-01"
    expected_schedule = ["Dim. 01-10"]
    result = get_week_schedule(start_date, end_date)
    assert result == expected_schedule


def test_get_week_schedule_invalid_date_format():
    """
    Test the get_week_schedule function with invalid date format.

    This test ensures that the get_week_schedule function raises a ValueError
    when provided with dates in an incorrect format (DD-MM-YYYY instead of the expected format).

    Raises:
        ValueError: If the date format is invalid.
    """

    start_date = "01-10-2023"
    end_date = "07-10-2023"
    with pytest.raises(ValueError):
        get_week_schedule(start_date, end_date)


def test_get_week_schedule_end_date_before_start_date():
    """
    Test the get_week_schedule function when the end date is before the start date.

    This test case verifies that the function returns an empty schedule when the
    end date is earlier than the start date.

    Expected behavior:
    - The function should return an empty list when the end date is before the start date.

    Test data:
    - start_date: "2023-10-07"
    - end_date: "2023-10-01"
    - expected_schedule: [], an empty list.

    Asserts:
    - The result of get_week_schedule(start_date, end_date) should be an empty list.
    """

    start_date = "2023-10-07"
    end_date = "2023-10-01"
    expected_schedule = []
    result = get_week_schedule(start_date, end_date)
    assert result == expected_schedule


def test_split_into_weeks_single_week():
    """
    Test the split_into_weeks function with a single week schedule.

    This test case checks if the function correctly handles a schedule that spans exactly one week.
    It verifies that the function returns a list containing one sublist with all the days of the week.

    Test data:
    - week_schedule: A list of strings representing the days of a single week.
    - expected_output: A list containing one sublist with the same days as week_schedule.

    Asserts:
    - The function's output should match the expected_output.
    """

    week_schedule = [
        "Lun. 01-01",
        "Mar. 02-01",
        "Mer. 03-01",
        "Jeu. 04-01",
        "Ven. 05-01",
        "Sam. 06-01",
        "Dim. 07-01",
    ]
    expected_output = [
        [
            "Lun. 01-01",
            "Mar. 02-01",
            "Mer. 03-01",
            "Jeu. 04-01",
            "Ven. 05-01",
            "Sam. 06-01",
            "Dim. 07-01",
        ]
    ]
    assert split_into_weeks(week_schedule) == expected_output


def test_split_into_weeks_multiple_weeks():
    """
    Test the split_into_weeks function with a schedule spanning multiple weeks.

    This test case checks if the function correctly splits a list of days into
    multiple weeks. The input schedule contains 14 days, and the expected output
    is a list of two lists, each containing 7 days.

    The input schedule:
        "Lun. 01-01", "Mar. 02-01", "Mer. 03-01", "Jeu. 04-01", "Ven. 05-01",
        "Sam. 06-01", "Dim. 07-01", "Lun. 08-01", "Mar. 09-01", "Mer. 10-01",
        "Jeu. 11-01", "Ven. 12-01", "Sam. 13-01", "Dim. 14-01"

    The expected output:
            "Lun. 01-01", "Mar. 02-01", "Mer. 03-01", "Jeu. 04-01", "Ven. 05-01",
            "Sam. 06-01", "Dim. 07-01"
            "Lun. 08-01", "Mar. 09-01", "Mer. 10-01", "Jeu. 11-01", "Ven. 12-01",
            "Sam. 13-01", "Dim. 14-01"

    Asserts that the split_into_weeks function returns the expected output.
    """

    week_schedule = [
        "Lun. 01-01",
        "Mar. 02-01",
        "Mer. 03-01",
        "Jeu. 04-01",
        "Ven. 05-01",
        "Sam. 06-01",
        "Dim. 07-01",
        "Lun. 08-01",
        "Mar. 09-01",
        "Mer. 10-01",
        "Jeu. 11-01",
        "Ven. 12-01",
        "Sam. 13-01",
        "Dim. 14-01",
    ]
    expected_output = [
        [
            "Lun. 01-01",
            "Mar. 02-01",
            "Mer. 03-01",
            "Jeu. 04-01",
            "Ven. 05-01",
            "Sam. 06-01",
            "Dim. 07-01",
        ],
        [
            "Lun. 08-01",
            "Mar. 09-01",
            "Mer. 10-01",
            "Jeu. 11-01",
            "Ven. 12-01",
            "Sam. 13-01",
            "Dim. 14-01",
        ],
    ]
    assert split_into_weeks(week_schedule) == expected_output


def test_split_into_weeks_partial_week():
    """
    Test the split_into_weeks function with a partial week schedule.

    This test checks if the function correctly handles a schedule that does not
    span a full week. The input schedule contains three days, and the expected
    output is a list containing a single list with these three days.

    Test case:
    - Input: ["Lun. 01-01", "Mar. 02-01", "Mer. 03-01"]
    - Expected output: [["Lun. 01-01", "Mar. 02-01", "Mer. 03-01"]]
    """

    week_schedule = ["Lun. 01-01", "Mar. 02-01", "Mer. 03-01"]
    expected_output = [["Lun. 01-01", "Mar. 02-01", "Mer. 03-01"]]
    assert split_into_weeks(week_schedule) == expected_output


def test_split_into_weeks_empty_schedule():
    """
    Test case for split_into_weeks function with an empty schedule.

    This test verifies that the split_into_weeks function correctly handles
    the case where the input schedule is an empty list. The expected output
    for an empty schedule is also an empty list.
    """

    week_schedule = []
    expected_output = []
    assert split_into_weeks(week_schedule) == expected_output


def test_split_by_month_or_period_single_month():
    """
    Test the split_by_month_or_period function with a single month schedule.

    This test case checks if the function correctly handles a schedule that
    spans only one month. The input schedule contains dates from January 1st
    to January 10th. The expected output is a list containing a single list
    with all the input dates.

    The function is expected to return the same list of dates grouped together
    as they all belong to the same month.

    Asserts:
        - The result of split_by_month_or_period(week_schedule) should match
          the expected output.
    """

    week_schedule = [
        "Lun. 01-01",
        "Mar. 02-01",
        "Mer. 03-01",
        "Jeu. 04-01",
        "Ven. 05-01",
        "Sam. 06-01",
        "Dim. 07-01",
        "Lun. 08-01",
        "Mar. 09-01",
        "Mer. 10-01",
    ]
    expected_output = [
        [
            "Lun. 01-01",
            "Mar. 02-01",
            "Mer. 03-01",
            "Jeu. 04-01",
            "Ven. 05-01",
            "Sam. 06-01",
            "Dim. 07-01",
            "Lun. 08-01",
            "Mar. 09-01",
            "Mer. 10-01",
        ]
    ]
    result = split_by_month_or_period(week_schedule)
    assert result == expected_output


def test_split_by_month_or_period_multiple_months():
    """
    Test the split_by_month_or_period function with a schedule that spans multiple months.

    This test case checks if the function correctly splits a weekly schedule into separate lists
    based on the month. The input schedule contains dates from the end of January and the beginning
    of February. The expected output is a list of two lists: one for the dates in January and one
    for the dates in February.

    The function should split the input list as follows:
    - The first list contains dates from January: ["Lun. 29-01", "Mar. 30-01", "Mer. 31-01"]
    - The second list contains dates from February: ["Jeu. 01-02", "Ven. 02-02", "Sam. 03-02", "Dim. 04-02", "Lun. 05-02", "Mar. 06-02", "Mer. 07-02"]

    Asserts:
        The result of split_by_month_or_period(week_schedule) should match the expected output.
    """

    week_schedule = [
        "Lun. 29-01",
        "Mar. 30-01",
        "Mer. 31-01",
        "Jeu. 01-02",
        "Ven. 02-02",
        "Sam. 03-02",
        "Dim. 04-02",
        "Lun. 05-02",
        "Mar. 06-02",
        "Mer. 07-02",
    ]
    expected_output = [
        ["Lun. 29-01", "Mar. 30-01", "Mer. 31-01"],
        [
            "Jeu. 01-02",
            "Ven. 02-02",
            "Sam. 03-02",
            "Dim. 04-02",
            "Lun. 05-02",
            "Mar. 06-02",
            "Mer. 07-02",
        ],
    ]
    result = split_by_month_or_period(week_schedule)
    assert result == expected_output


def test_split_by_month_or_period_edge_case():
    """
    Test the split_by_month_or_period function with an edge case where the schedule
    spans the end of one month and the beginning of the next month.

    The function should correctly split the schedule into two lists: one for the
    last day of the previous month and one for the days of the new month.

    The input schedule contains dates from December 31st to January 9th, and the
    expected output is a list of two lists: one containing the date from December
    and the other containing the dates from January.

    The test asserts that the result of the function matches the expected output.
    """

    week_schedule = [
        "Lun. 31-12",
        "Mar. 01-01",
        "Mer. 02-01",
        "Jeu. 03-01",
        "Ven. 04-01",
        "Sam. 05-01",
        "Dim. 06-01",
        "Lun. 07-01",
        "Mar. 08-01",
        "Mer. 09-01",
    ]
    expected_output = [
        ["Lun. 31-12"],
        [
            "Mar. 01-01",
            "Mer. 02-01",
            "Jeu. 03-01",
            "Ven. 04-01",
            "Sam. 05-01",
            "Dim. 06-01",
            "Lun. 07-01",
            "Mar. 08-01",
            "Mer. 09-01",
        ],
    ]
    result = split_by_month_or_period(week_schedule)
    assert result == expected_output


@pytest.fixture
def day_off():
    """
    Fixture that provides a dictionary of agents and their respective days off.

    Returns:
        dict: A dictionary where keys are agent names and values are lists of strings
            representing the days off for each agent in the format "DD-MM-YYYY".
    """

    return {
        "Agent1": ["01-01-2023", "10-01-2023"],
        "Agent2": ["15-01-2023", "20-01-2023"],
    }


def test_is_vacation_day_true(day_off):
    """
    Tests the is_vacation_day function to verify that it correctly identifies vacation days.

    Args:
        day_off (dict): A dictionary containing the vacation days for different agents.

    Asserts:
        The function asserts that the is_vacation_day function returns True for the specified agents and dates.
    """

    assert is_vacation_day("Agent1", "Lun. 02-01", day_off)
    assert is_vacation_day("Agent2", "Mer. 18-01", day_off)


def test_is_vacation_day_false(day_off):
    """
    Test the is_vacation_day function to ensure it returns False for given inputs.

    Args:
        day_off (dict): A dictionary containing the days off for agents.

    Asserts:
        The function is_vacation_day should return False for the given agent and date combinations.
    """

    assert not is_vacation_day("Agent1", "Lun. 11-01", day_off)
    assert not is_vacation_day("Agent2", "Dim. 22-01", day_off)


def test_is_vacation_day_weekend(day_off):
    """
    Test the is_vacation_day function to ensure that weekends are not considered vacation days.

    Args:
        day_off (dict): A dictionary containing the days off for agents.

    Asserts:
        The function asserts that "Sam. 07-01" and "Dim. 15-01" are not vacation days for "Agent1" and "Agent2" respectively.
    """

    assert not is_vacation_day("Agent1", "Sam. 07-01", day_off)
    assert not is_vacation_day("Agent2", "Dim. 15-01", day_off)


def test_is_vacation_day_not_in_dayOff(day_off):
    """
    Test to ensure that a given day is not marked as a vacation day.

    Args:
        day_off (dict): A dictionary containing the days off for agents.

    Asserts:
        The function is_vacation_day should return False when the specified day is not in the list of days off.
    """

    assert not is_vacation_day("Agent3", "Lun. 02-01", day_off)


def test_is_weekend_saturday():
    """
    Test case for the function is_weekend to check if a given date string
    represents a Saturday.

    The date string format is assumed to be "Day. DD-MM", where "Day" is a
    three-letter abbreviation of the day in French (e.g., "Sam." for Saturday).

    This test specifically checks if the function correctly identifies
    "Sam. 01-01" as a weekend day.

    Raises:
        AssertionError: If the function is_weekend returns False
                        for the input "Sam. 01-01".
    """

    assert is_weekend("Sam. 01-01")


def test_is_weekend_sunday():
    """
    Test case for the function is_weekend to check if a given date string
    represents a Sunday.

    The date string format is assumed to be "Day. DD-MM", where "Day" is a
    three-letter abbreviation of the day in French (e.g., "Dim." for Sunday).

    This test specifically checks if the function correctly identifies
    "Dim. 02-01" as a weekend day.

    Raises:
        AssertionError: If the function is_weekend returns False
                        for the input "Dim. 02-01".
    """

    assert is_weekend("Dim. 02-01")


def test_is_weekend_monday():
    """
    Test case for the function is_weekend to check if a given date string
    represents a Monday.

    The date string format is assumed to be "Day. DD-MM", where "Day" is a
    three-letter abbreviation of the day in French (e.g., "Lun." for Monday).

    This test specifically checks if the function correctly identifies
    "Lun. 03-01" as a weekend day.

    Raises:
        AssertionError: If the function is_weekend returns False
                        for the input "Lun. 03-01".
    """

    assert not is_weekend("Lun. 03-01")


def test_is_weekend_tuesday():
    """
    Test case for the function is_weekend to check if a given date string
    represents a Tuesday.

    The date string format is assumed to be "Day. DD-MM", where "Day" is a
    three-letter abbreviation of the day in French (e.g., "Mar." for Tuesday).

    This test specifically checks if the function correctly identifies
    "Mar. 04-01" as a weekend day.

    Raises:
        AssertionError: If the function is_weekend returns False
                        for the input "Mar. 04-01".
    """

    assert not is_weekend("Mar. 04-01")
