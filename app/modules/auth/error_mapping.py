from fastapi import status

from app.modules.auth.exceptions import (
    InvalidCredentialsError,
    EmailAlreadyExistsError,
    RegistrationError,
)
from app.utils.error_handlers import create_error_mapper


auth_error_mapper = create_error_mapper(
    {
        InvalidCredentialsError: (status.HTTP_401_UNAUTHORIZED, lambda e: str(e)),
        EmailAlreadyExistsError: (status.HTTP_400_BAD_REQUEST, lambda e: str(e)),
        RegistrationError: (status.HTTP_500_INTERNAL_SERVER_ERROR, lambda e: str(e)),
    }
)
