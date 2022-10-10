"""Contain parser description types."""
from dataclasses import (
    dataclass,
)
from datetime import (
    date,
    datetime,
)
from decimal import (
    Decimal,
)
from typing import (
    Callable,
    Generic,
    Mapping,
    TypeVar,
    Union,
)


CsvRow = Mapping[str, str]
T = TypeVar("T")


@dataclass
class ExtractParser(Generic[T]):
    """Extract a field from a cell in a row."""

    field: str
    topython: Callable[[str], T]


@dataclass
class ExtractDateParser:
    """Extract a date from a cell in a row."""

    field: str
    fmt: str


@dataclass
class ConstantParser(Generic[T]):
    """Return a constant value for a csv cell."""

    value: T


@dataclass
class CellParser(Generic[T]):
    """Parse a single cell in a csv row."""

    method: Callable[[CsvRow], T]


Parsable = Union[ExtractParser[T], ConstantParser[T], CellParser[T]]
DateParsable = Union[ExtractDateParser, CellParser[date]]


@dataclass
class CsvTransactionParser:
    """Parse csv rows to transaction attributes."""

    date: DateParsable
    num: Parsable[str]
    description: Parsable[str]
    memo: Parsable[str]
    withdrawal: Parsable[Decimal]
    deposit: Parsable[Decimal]


@dataclass
class CsvFormat:
    """Store format info for a CSV file."""

    parser: CsvTransactionParser
    encoding: str
    delimiter: str
    skip: int
    path: str


def apply_parser(row: CsvRow, parser: Parsable[T]) -> T:
    """Apply a parser."""
    if isinstance(parser, CellParser):
        return parser.method(row)
    elif isinstance(parser, ConstantParser):
        return parser.value
    elif isinstance(parser, ExtractParser):
        return parser.topython(row[parser.field])


def apply_date_parser(row: CsvRow, parser: DateParsable) -> date:
    """Apply a parser."""
    if isinstance(parser, CellParser):
        return parser.method(row)
    elif isinstance(parser, ExtractDateParser):
        # If we forget .date() here, mypy will bug out
        # https://github.com/python/typeshed/issues/4802
        # https://github.com/python/mypy/issues/9015
        return datetime.strptime(row[parser.field], parser.fmt).date()
