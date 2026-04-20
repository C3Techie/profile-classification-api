import re
from typing import Dict, Any, Optional

# Build a comprehensive country map covering all countries in the seed data + common references
COUNTRY_MAP = {
    "nigeria": "NG",
    "benin": "BJ",
    "kenya": "KE",
    "angola": "AO",
    "tanzania": "TZ",
    "uganda": "UG",
    "sudan": "SD",
    "madagascar": "MG",
    "united kingdom": "GB",
    "uk": "GB",
    "britain": "GB",
    "great britain": "GB",
    "united states": "US",
    "usa": "US",
    "us": "US",
    "america": "US",
    "india": "IN",
    "cameroon": "CM",
    "cape verde": "CV",
    "republic of the congo": "CG",
    "congo": "CG",
    "mozambique": "MZ",
    "south africa": "ZA",
    "mali": "ML",
    "democratic republic of the congo": "CD",
    "dr congo": "CD",
    "drc": "CD",
    "france": "FR",
    "eritrea": "ER",
    "zambia": "ZM",
    "gambia": "GM",
    "the gambia": "GM",
    "cote d'ivoire": "CI",
    "ivory coast": "CI",
    "ethiopia": "ET",
    "morocco": "MA",
    "malawi": "MW",
    "brazil": "BR",
    "tunisia": "TN",
    "somalia": "SO",
    "gabon": "GA",
    "namibia": "NA",
    "senegal": "SN",
    "zimbabwe": "ZW",
    "ghana": "GH",
    "egypt": "EG",
    "rwanda": "RW",
    "burkina faso": "BF",
    "guinea": "GN",
    "western sahara": "EH",
    "togo": "TG",
    "niger": "NE",
    "sierra leone": "SL",
    "liberia": "LR",
    "mauritania": "MR",
    "chad": "TD",
    "central african republic": "CF",
    "australia": "AU",
    "germany": "DE",
    "canada": "CA",
    "spain": "ES",
    "italy": "IT",
    "portugal": "PT",
    "netherlands": "NL",
    "belgium": "BE",
    "sweden": "SE",
    "norway": "NO",
    "denmark": "DK",
    "finland": "FI",
    "switzerland": "CH",
    "russia": "RU",
    "china": "CN",
    "japan": "JP",
    "south korea": "KR",
    "korea": "KR",
    "indonesia": "ID",
    "pakistan": "PK",
    "bangladesh": "BD",
    "mexico": "MX",
    "argentina": "AR",
    "colombia": "CO",
    "peru": "PE",
    "saudi arabia": "SA",
    "turkey": "TR",
    "iran": "IR",
    "iraq": "IQ",
    "israel": "IL",
    "new zealand": "NZ",
    "zimbabwe": "ZW",
}

# Sort by length descending so multi-word names match first
SORTED_COUNTRY_NAMES = sorted(COUNTRY_MAP.keys(), key=len, reverse=True)


def parse_query(q: str) -> Optional[Dict[str, Any]]:
    """
    Rule-based natural language query parser.
    
    Supported mappings:
    - Gender: "male(s)" or "female(s)" (word-boundary matched)
    - Age ranges: "young" → 16-24, "above X" → min_age=X, "below X" → max_age=X
    - Age groups: "child/children", "teenager(s)", "adult(s)", "senior(s)"
    - Countries: "from [country name]" or just the country name in the query
    
    Returns a dict of filters, or None if query cannot be interpreted.
    """
    if not q or not q.strip():
        return None

    q_lower = q.lower().strip()
    filters = {}

    # 1. Gender parsing — use word boundaries to avoid "female" matching "male"
    has_male = bool(re.search(r'\bmales?\b', q_lower))
    has_female = bool(re.search(r'\bfemales?\b', q_lower))

    if has_male and has_female:
        # Both explicitly mentioned (e.g., "male and female"), don't filter by gender
        pass
    elif has_male:
        filters["gender"] = "male"
    elif has_female:
        filters["gender"] = "female"

    # 2. "young" keyword → age 16–24
    if re.search(r'\byoung\b', q_lower):
        filters["min_age"] = 16
        filters["max_age"] = 24

    # 3. Age groups — word boundaries
    if re.search(r'\bteenagers?\b', q_lower):
        filters["age_group"] = "teenager"
    elif re.search(r'\badults?\b', q_lower):
        filters["age_group"] = "adult"
    elif re.search(r'\bchildren\b|\bchild\b', q_lower):
        filters["age_group"] = "child"
    elif re.search(r'\bseniors?\b', q_lower):
        filters["age_group"] = "senior"

    # 4. Numeric age constraints: "above X", "over X", "older than X" / "below X", "under X", "younger than X"
    above_match = re.search(r'\b(?:above|over|older than)\s+(\d+)', q_lower)
    if above_match:
        filters["min_age"] = int(above_match.group(1))

    below_match = re.search(r'\b(?:below|under|younger than)\s+(\d+)', q_lower)
    if below_match:
        filters["max_age"] = int(below_match.group(1))

    # 5. Country parsing
    # Strategy: try "from [country_name]" first (multi-word), then fallback to anywhere in query
    country_found = None
    
    # Try "from [country]" — match longest country first
    for country_name in SORTED_COUNTRY_NAMES:
        pattern = r'\bfrom\s+' + re.escape(country_name) + r'\b'
        if re.search(pattern, q_lower):
            country_found = COUNTRY_MAP[country_name]
            break

    # Fallback: check if any country name appears anywhere in query
    if not country_found:
        for country_name in SORTED_COUNTRY_NAMES:
            pattern = r'\b' + re.escape(country_name) + r'\b'
            if re.search(pattern, q_lower):
                country_found = COUNTRY_MAP[country_name]
                break

    if country_found:
        filters["country_id"] = country_found

    # Return None if we couldn't interpret anything meaningful
    if not filters:
        return None

    return filters
