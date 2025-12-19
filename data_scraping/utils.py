import re
from urllib.parse import urlparse, parse_qs

def extract_numeric(text: str) -> int:
    """
    Extract digits from a string and return as int.
    Example: "1.234 tin" -> 1234
    """
    if text is None:
        return 0
    digits = re.findall(r"\d+", text.replace(".", "").replace(",", ""))
    return int("".join(digits)) if digits else 0

def extract_coordinates(embed_map_link: str):
    """
    Try to extract lat/lon from an iframe map URL.
    Works for common patterns like:
    - ...?q=21.03,105.78
    - ...&center=21.03,105.78
    - ...!3d21.03!4d105.78
    """
    if not embed_map_link:
        return None, None

    # pattern: !3dLAT!4dLON (google maps embed)
    m = re.search(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)", embed_map_link)
    if m:
        return float(m.group(1)), float(m.group(2))

    # query params
    try:
        parsed = urlparse(embed_map_link)
        qs = parse_qs(parsed.query)

        for key in ["q", "center", "ll"]:
            if key in qs and qs[key]:
                val = qs[key][0]
                if "," in val:
                    lat, lon = val.split(",", 1)
                    return float(lat), float(lon)
    except Exception:
        pass

    return None, None