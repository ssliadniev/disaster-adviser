from dataclasses import dataclass
from typing import TypeVar, Generic, Callable
from functools import reduce

T = TypeVar("T")
E = TypeVar("E")
A = TypeVar("A")
B = TypeVar("B")


@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T


@dataclass(frozen=True)
class Err(Generic[E]):
    error: E


Result = Ok[T] | Err[E]


def compose(*fns: Callable) -> Callable:
    def _apply(value: A) -> B:
        return reduce(lambda acc, fn: fn(acc), fns, value)
    return _apply


def pipe(value, *fns):
    return reduce(lambda v, f: f(v), fns, value)