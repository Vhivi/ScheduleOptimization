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
    assert is_valid_date("2023-10-15") is True
    assert is_valid_date("2022-02-28") is True
    assert is_valid_date("2020-02-29") is True  # Leap year


def test_is_valid_date_invalid_format():
    assert is_valid_date("15-10-2023") is False
    assert is_valid_date("2023/10/15") is False
    assert is_valid_date("20231015") is False


def test_is_valid_date_invalid_date():
    assert is_valid_date("2023-02-30") is False  # Invalid day
    assert is_valid_date("2021-04-31") is False  # Invalid day
    assert is_valid_date("2019-02-29") is False  # Not a leap year


def test_is_valid_date_empty_string():
    assert is_valid_date("") is False


def test_is_valid_date_none():
    assert is_valid_date(None) is False


def test_get_week_schedule():
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
    start_date = "2023-10-01"
    end_date = "2023-10-01"
    expected_schedule = ["Dim. 01-10"]
    result = get_week_schedule(start_date, end_date)
    assert result == expected_schedule


def test_get_week_schedule_invalid_date_format():
    start_date = "01-10-2023"
    end_date = "07-10-2023"
    with pytest.raises(ValueError):
        get_week_schedule(start_date, end_date)


def test_get_week_schedule_end_date_before_start_date():
    start_date = "2023-10-07"
    end_date = "2023-10-01"
    expected_schedule = []
    result = get_week_schedule(start_date, end_date)
    assert result == expected_schedule


def test_split_into_weeks_single_week():
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
    week_schedule = ["Lun. 01-01", "Mar. 02-01", "Mer. 03-01"]
    expected_output = [["Lun. 01-01", "Mar. 02-01", "Mer. 03-01"]]
    assert split_into_weeks(week_schedule) == expected_output


def test_split_into_weeks_empty_schedule():
    week_schedule = []
    expected_output = []
    assert split_into_weeks(week_schedule) == expected_output


def test_split_by_month_or_period_single_month():
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
    expected = [
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
    assert result == expected


def test_split_by_month_or_period_multiple_months():
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
    expected = [
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
    assert result == expected


def test_split_by_month_or_period_edge_case():
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
    expected = [
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
    assert result == expected


@pytest.fixture
def day_off():
    return {
        "Agent1": ["01-01-2023", "10-01-2023"],
        "Agent2": ["15-01-2023", "20-01-2023"],
    }


def test_is_vacation_day_true(day_off):
    assert is_vacation_day("Agent1", "Lun. 02-01", day_off)
    assert is_vacation_day("Agent2", "Mer. 18-01", day_off)


def test_is_vacation_day_false(day_off):
    assert not is_vacation_day("Agent1", "Lun. 11-01", day_off)
    assert not is_vacation_day("Agent2", "Dim. 22-01", day_off)


def test_is_vacation_day_weekend(day_off):
    assert not is_vacation_day("Agent1", "Sam. 07-01", day_off)
    assert not is_vacation_day("Agent2", "Dim. 15-01", day_off)


def test_is_vacation_day_not_in_dayOff(day_off):
    assert not is_vacation_day("Agent3", "Lun. 02-01", day_off)


def test_is_weekend_saturday():
    assert is_weekend("Sam. 01-01")


def test_is_weekend_sunday():
    assert is_weekend("Dim. 02-01")


def test_is_weekend_monday():
    assert not is_weekend("Lun. 03-01")


def test_is_weekend_tuesday():
    assert not is_weekend("Mar. 04-01")
