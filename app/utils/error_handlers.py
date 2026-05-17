from typing import Callable, Type, Dict, Tuple
from fastapi import HTTPException

ErrorMapping = Dict[Type[Exception], Tuple[int, Callable[[Exception], str]]]


def create_error_mapper(
    error_mappings: ErrorMapping,
) -> Callable[[Exception], HTTPException]:
    def mapper(exc: Exception) -> HTTPException:
        for error_type, (status_code, message_fn) in error_mappings.items():
            if isinstance(exc, error_type):
                return HTTPException(status_code=status_code, detail=message_fn(exc))
        raise exc

    return mapper
