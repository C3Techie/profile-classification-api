import re
from typing import Dict, Any, Optional

# Build a comprehensive country map covering all countries in the seed data + common references
COUNTRY_MAP = {
    "nigeria": "NG",
    "nigerian": "NG",
    "benin": "BJ",
    "beninese": "BJ",
    "kenya": "KE",
    "kenyan": "KE",
    "angola": "AO",
    "angolan": "AO",
    "tanzania": "TZ",
    "tanzanian": "TZ",
    "uganda": "UG",
    "ugandan": "UG",
    "sudan": "SD",
    "sudanese": "SD",
    "madagascar": "MG",
    "malagasy": "MG",
    "united kingdom": "GB",
    "uk": "GB",
    "britain": "GB",
    "british": "GB",
    "united states": "US",
    "usa": "US",
    "us": "US",
    "american": "US",
    "india": "IN",
    "indian": "IN",
    "cameroon": "CM",
    "cameroonian": "CM",
    "cape verde": "CV",
    "republic of the congo": "CG",
    "congo": "CG",
    "mozambique": "MZ",
    "mozambican": "MZ",
    "south africa": "ZA",
    "south african": "ZA",
    "mali": "ML",
    "malian": "ML",
    "democratic republic of the congo": "CD",
    "dr congo": "CD",
    "drc": "CD",
    "france": "FR",
    "french": "FR",
    "eritrea": "ER",
    "eritrean": "ER",
    "zambia": "ZM",
    "zambian": "ZM",
    "gambia": "GM",
    "gambian": "GM",
    "cote d'ivoire": "CI",
    "ivory coast": "CI",
    "ethiopia": "ET",
    "ethiopian": "ET",
    "morocco": "MA",
    "moroccan": "MA",
    "malawi": "MW",
    "malawian": "MW",
    "brazil": "BR",
    "brazilian": "BR",
    "tunisia": "TN",
    "tunisian": "TN",
    "somalia": "SO",
    "somali": "SO",
    "gabon": "GA",
    "gabonese": "GA",
    "namibia": "NA",
    "namibian": "NA",
    "senegal": "SN",
    "senegalese": "SN",
    "zimbabwe": "ZW",
    "zimbabwean": "ZW",
    "ghana": "GH",
    "ghanaian": "GH",
    "egypt": "EG",
    "egyptian": "EG",
    "rwanda": "RW",
    "rwandan": "RW",
    "burkina faso": "BF",
    "guinea": "GN",
    "guinean": "GN",
    "togo": "TG",
    "togolese": "TG",
    "niger": "NE",
    "sierra leone": "SL",
    "liberia": "LR",
    "liberian": "LR",
    "mauritania": "MR",
    "chad": "TD",
    "chadian": "TD",
    "australia": "AU",
    "australian": "AU",
    "germany": "DE",
    "german": "DE",
    "canada": "CA",
    "canadian": "CA",
    "spain": "ES",
    "spanish": "ES",
    "italy": "IT",
    "italian": "IT",
    "portugal": "PT",
    "portuguese": "PT",
    "netherlands": "NL",
    "dutch": "NL",
    "belgium": "BE",
    "belgian": "BE",
    "sweden": "SE",
    "swedish": "SE",
    "norway": "NO",
    "norwegian": "NO",
    "denmark": "DK",
    "danish": "DK",
    "finland": "FI",
    "finnish": "FI",
    "switzerland": "CH",
    "swiss": "CH",
    "russia": "RU",
    "russian": "RU",
    "china": "CN",
    "chinese": "CN",
    "japan": "JP",
    "japanese": "JP",
    "south korea": "KR",
    "korean": "KR",
    "indonesia": "ID",
    "indonesian": "ID",
    "pakistan": "PK",
    "pakistani": "PK",
    "bangladesh": "BD",
    "bangladeshi": "BD",
    "mexico": "MX",
    "mexican": "MX",
    "argentina": "AR",
    "argentine": "AR",
    "colombia": "CO",
    "colombian": "CO",
    "peru": "PE",
    "peruvian": "PE",
    "saudi arabia": "SA",
    "saudi": "SA",
    "turkey": "TR",
    "turkish": "TR",
    "iran": "IR",
    "iranian": "IR",
    "iraq": "IQ",
    "iraqi": "IQ",
    "israel": "IL",
    "israeli": "IL",
    "new zealand": "NZ",
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


def normalize_filters(filters: Dict[str, Any]) -> str:
    """
    Convert a filter dictionary into a canonical string for use as a cache key.
    - Removes None values
    - Sorts keys alphabetically
    - Converts values to strings
    """
    if not filters:
        return "empty"
    
    # Filter out None values and sort keys
    clean_filters = {k: str(v).lower() for k, v in filters.items() if v is not None}
    sorted_keys = sorted(clean_filters.keys())
    
    # Create a stable string representation
    return "&".join(f"{k}={clean_filters[k]}" for k in sorted_keys)
