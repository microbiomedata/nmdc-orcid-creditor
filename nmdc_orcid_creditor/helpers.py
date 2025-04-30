from typing import Optional
import re

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
