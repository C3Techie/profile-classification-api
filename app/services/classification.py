import asyncio
import httpx
from typing import Dict, Any
from app.core.config import settings

class ExternalAPIError(Exception):
    def __init__(self, api_name: str):
        self.api_name = api_name

# Reverse map for country names
COUNTRY_CODE_MAP = {
    "NG": "Nigeria",
    "BJ": "Benin",
    "KE": "Kenya",
    "AO": "Angola",
    "TZ": "Tanzania",
    "UG": "Uganda",
    "SD": "Sudan",
    "MG": "Madagascar",
    "GB": "United Kingdom",
    "US": "United States",
    "IN": "India",
    "CM": "Cameroon",
    "CV": "Cape Verde",
    "CG": "Republic of the Congo",
    "MZ": "Mozambique",
    "ZA": "South Africa",
    "ML": "Mali",
    "CD": "DR Congo",
    "FR": "France",
    "ER": "Eritrea",
    "ZM": "Zambia",
    "GM": "Gambia",
    "CI": "Côte d'Ivoire",
    "ET": "Ethiopia",
    "MA": "Morocco",
    "MW": "Malawi",
    "BR": "Brazil",
    "TN": "Tunisia",
    "SO": "Somalia",
    "GA": "Gabon",
    "NA": "Namibia",
    "SN": "Senegal",
}

def get_country_name(code: str) -> str:
    return COUNTRY_CODE_MAP.get(code.upper(), code.upper())

def get_age_group(age: int) -> str:
    if age <= 12: return "child"
    if age <= 19: return "teenager"
    if age <= 59: return "adult"
    return "senior"

async def fetch_classification_data(name: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Concurrent calls utilisant les URLs de configuration
        urls = [
            f"{settings.GENDERIZE_URL}?name={name}",
            f"{settings.AGIFY_URL}?name={name}",
            f"{settings.NATIONALIZE_URL}?name={name}"
        ]
        
        tasks = [client.get(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Parse Genderize
        g_res = results[0]
        if isinstance(g_res, Exception) or g_res.status_code != 200:
            raise ExternalAPIError("Genderize")
        g_data = g_res.json()
        if not g_data.get("gender") or g_data.get("count", 0) == 0:
            raise ExternalAPIError("Genderize")
            
        # Parse Agify
        a_res = results[1]
        if isinstance(a_res, Exception) or a_res.status_code != 200:
            raise ExternalAPIError("Agify")
        a_data = a_res.json()
        if a_data.get("age") is None:
            raise ExternalAPIError("Agify")
            
        # Parse Nationalize
        n_res = results[2]
        if isinstance(n_res, Exception) or n_res.status_code != 200:
            raise ExternalAPIError("Nationalize")
        n_data = n_res.json()
        countries = n_data.get("country", [])
        if not countries:
            raise ExternalAPIError("Nationalize")
            
        # Pick top country
        top_country = max(countries, key=lambda x: x["probability"])
        country_code = top_country["country_id"]
        
        return {
            "gender": g_data["gender"],
            "gender_probability": g_data["probability"],
            "age": a_data["age"],
            "age_group": get_age_group(a_data["age"]),
            "country_id": country_code,
            "country_name": get_country_name(country_code),
            "country_probability": top_country["probability"]
        }
