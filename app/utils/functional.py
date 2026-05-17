from dataclasses import dataclass
from functools import reduce
from typing import Callable, Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")
A = TypeVar("A")
B = TypeVar("B")
R = TypeVar("R")


@dataclass(frozen=True)
class Result(Generic[T, E]):
    def map(self, fn: Callable[[T], R]) -> "Result[R, E]":
        if isinstance(self, Err):
            return self
        return Ok(fn(self.value))

    def flat_map(self, fn: Callable[[T], "Result[R, E]"]) -> "Result[R, E]":
        if isinstance(self, Err):
            return self
        return fn(self.value)

    def get_or_else(self, default: R) -> T | R:
        return default if isinstance(self, Err) else self.value


@dataclass(frozen=True)
class Ok(Result[T, E]):
    value: T


@dataclass(frozen=True)
class Err(Result[T, E]):
    error: E


@dataclass(frozen=True)
class Maybe(Generic[T]):
    def map(self, fn: Callable[[T], R]) -> "Maybe[R]":
        if isinstance(self, Nothing):
            return self
        return Some(fn(self.value))

    def flat_map(self, fn: Callable[[T], "Maybe[R]"]) -> "Maybe[R]":
        if isinstance(self, Nothing):
            return self
        return fn(self.value)

    def filter(self, predicate: Callable[[T], bool]) -> "Maybe[T]":
        if isinstance(self, Nothing):
            return self
        return self if predicate(self.value) else Nothing()

    def get_or_else(self, default: R) -> T | R:
        return default if isinstance(self, Nothing) else self.value


@dataclass(frozen=True)
class Some(Maybe[T]):
    value: T


@dataclass(frozen=True)
class Nothing(Maybe[None]):
    pass


def compose(*fns: Callable) -> Callable:
    def _apply(value: A) -> B:
        return reduce(lambda acc, fn: fn(acc), fns, value)

    return _apply


def pipe(value, *fns):
    return reduce(lambda v, f: f(v), fns, value)


def maybe_of(value: T | None) -> Maybe[T]:
    return Nothing() if value is None else Some(value)
