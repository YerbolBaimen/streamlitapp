import ast
import numpy as np
import pandas as pd

def parse_str_list(cell):
    """Parse a cell that should represent a list of strings.

    Handles:
    - real Python lists / tuples / sets / numpy arrays
    - stringified lists like "['A', 'B']"
    - simple comma-separated strings like "A, B, C"
    """
    # 1) Already a list-like structure
    if isinstance(cell, (list, tuple, set)):
        return [str(x).strip(" '\"") for x in cell]
    if isinstance(cell, np.ndarray):
        return [str(x).strip(" '\"") for x in cell.tolist()]

    # 2) Null-ish values
    if cell is None:
        return []
    try:
        # only works for scalars, so it's inside try/except
        if pd.isna(cell):
            return []
    except TypeError:
        # non-scalar, fall through and handle as string
        pass

    # 3) Treat everything else as text
    text = str(cell).strip()
    if not text:
        return []

    # Try literal_eval if it looks like a Python list
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, list):
                return [str(x).strip(" '\"") for x in parsed]
        except Exception:
            pass

    # Fallback: comma-separated string
    return [item.strip() for item in text.split(",") if item.strip()]
