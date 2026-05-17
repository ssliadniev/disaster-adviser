from app.contracts.disaster import DisasterCategory
from app.utils.functional import Ok, Err, Result, pipe


def validate_disaster_categories(update_data: dict) -> Result[dict, str]:
    if "disaster_categories" not in update_data:
        return Ok(update_data)

    valid_categories = set(DisasterCategory.get_all_values())
    user_categories = set(update_data["disaster_categories"])
    invalid_categories = user_categories - valid_categories

    if invalid_categories:
        return Err(
            f"Invalid disaster categories: {invalid_categories}. "
            f"Valid categories: {', '.join(sorted(valid_categories))}"
        )

    return Ok(update_data)


def validate_preferences(update_data: dict) -> Result[dict, str]:
    return pipe(
        update_data,
        validate_disaster_categories,
    )
