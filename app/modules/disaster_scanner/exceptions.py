from typing import Optional


class FetchError(Exception):
    """
    Base class for fetch outcomes the driver knows how to reason about.
    """


class RetryableFetchError(FetchError):
    """
    Transient failure; the driver should wait and try again.
    """

    def __init__(self, message: str, *, retry_after: Optional[float | int] = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class PermanentFetchError(FetchError):
    """
    Failure that won't self-heal; propagate and stop the stream loudly.
    """
