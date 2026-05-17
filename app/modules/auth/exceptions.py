class InvalidCredentialsError(Exception):
    """Raised when login credentials are invalid"""
    pass


class EmailAlreadyExistsError(Exception):
    """Raised when attempting to register with existing email"""
    pass


class RegistrationError(Exception):
    """Raised when user registration fails"""
    pass