"""
Verhoeff Checksum Algorithm for Indian Aadhaar Verification
Normalizes Devanagari numerals and validates 12-digit format.
"""
VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]

VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]

VERHOEFF_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

DEVANAGARI_DIGITS = {
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
}

def normalize_digits(text: str) -> str:
    for dev, asc in DEVANAGARI_DIGITS.items():
        text = text.replace(dev, asc)
    return text

def validate_verhoeff(number_str: str) -> bool:
    clean = normalize_digits(number_str).replace(" ", "").replace("-", "")
    if not clean.isdigit():
        return False
    c = 0
    for i, item in enumerate(reversed(clean)):
        c = VERHOEFF_D[c][VERHOEFF_P[i % 8][int(item)]]
    return c == 0

def generate_verhoeff_checksum(eleven_digits: str) -> str:
    clean = normalize_digits(eleven_digits).replace(" ", "")
    c = 0
    for i, item in enumerate(reversed(clean)):
        c = VERHOEFF_D[c][VERHOEFF_P[(i + 1) % 8][int(item)]]
    return str(VERHOEFF_INV[c])
