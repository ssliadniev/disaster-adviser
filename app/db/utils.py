def row_to_dict(result) -> dict | None:
    """Convert SQLAlchemy result to a single dictionary or None"""
    row = result.mappings().first()
    return dict(row) if row else None


def rows_to_list(result) -> list[dict]:
    """Convert SQLAlchemy result to a list of dictionaries"""
    return [dict(row) for row in result.mappings().all()]
