import io

import pandas as pd


def load_dataframe_from_bytes(file_extension: str, content: bytes) -> pd.DataFrame:
    if file_extension == ".csv":
        return pd.read_csv(io.BytesIO(content))
    if file_extension in {".xlsx", ".xls"}:
        return pd.read_excel(io.BytesIO(content))
    raise ValueError("Unsupported file format. Use CSV or Excel.")

