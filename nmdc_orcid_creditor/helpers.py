from typing import Optional, Tuple
import re
from datetime import datetime
import logging


logger = logging.getLogger("uvicorn")


def extract_put_code_from_location_header(location_header: str) -> Optional[str]:
    r"""
    Extracts the affiliation's "put-code" from the specified string;
    which we will have received as the value of the "location" header
    in the response to an ORCID API request we used to create an affiliation.

    Reference: https://info.orcid.org/hands-on-with-the-orcid-api/3-write-to-an-orcid-record-post/ (search for "put-code")

    >>> extract_put_code_from_location_header("https://api.orcid.org/v3.0/0000-0000-0000-000X/service/12345")  # production API example
    '12345'
    >>> extract_put_code_from_location_header("https://api.sandbox.orcid.org/v3.0/0000-0000-0000-000X/service/12345")  # sandbox API example
    '12345'
    >>> extract_put_code_from_location_header("http://api.sandbox.orcid.org/v3.0/0000-0000-0000-000X/service/12345")  # plain HTTP
    '12345'
    >>> extract_put_code_from_location_header("https://api.orcid.org/v3.0/0000-0000-0000-000X/service/") is None  # no numbers at end
    True
    >>> extract_put_code_from_location_header("") is None  # empty
    True
    """

    the_put_code = None

    # If the location header matches the pattern, extract the "put-code".
    pattern = r"^https?://.*orcid\.org.*/(\d+)$"
    match_obj = re.match(pattern, location_header)
    if match_obj:
        the_put_code = match_obj.group(1)

    return the_put_code


def extract_year_month_day_from_datetime_string(date_str: str) -> Tuple[str, str, str]:
    r"""
    Extracts year, month, and day strings from the specified datetime string and returns
    them as a 3-item tuple. If the specified datetime string is not in ISO 8601 format,
    the function will raise a `ValueError` exception.

    Note: In Python 3.11, the `datetime.fromisoformat` function became tolerant of
          more input formats. For example, it became tolerant of the "Z" suffix.

    Real-world example (uses real string received from `nmdc-orcid-creditor-proxy`):
    Reference: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date#date_time_string_format
    >>> extract_year_month_day_from_datetime_string("2023-01-23T08:00:00.000Z")
    ('2023', '01', '23')

    Other valid input examples:
    >>> extract_year_month_day_from_datetime_string("2023-01-23")
    ('2023', '01', '23')
    >>> extract_year_month_day_from_datetime_string("2023-01-23T12:00:00Z")
    ('2023', '01', '23')
    >>> extract_year_month_day_from_datetime_string("2023-01-23T12:00:00+00:00")
    ('2023', '01', '23')
    >>> extract_year_month_day_from_datetime_string("2023-01-23T12:00:00.123456Z")
    ('2023', '01', '23')
    >>> extract_year_month_day_from_datetime_string("2023-01-23T12:00:00.123456+00:00")
    ('2023', '01', '23')

    Invalid input examples:
    >>> extract_year_month_day_from_datetime_string("")
    Traceback (most recent call last):
    ...
    ValueError: Invalid isoformat string: ''
    """
    year, month, day = ("", "", "")

    # Reference: https://docs.python.org/3/library/datetime.html#datetime.datetime.fromisoformat
    datetime_obj = datetime.fromisoformat(date_str)

    # Reference: https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes
    year = datetime_obj.strftime("%Y")
    month = datetime_obj.strftime("%m")
    day = datetime_obj.strftime("%d")

    return year, month, day
