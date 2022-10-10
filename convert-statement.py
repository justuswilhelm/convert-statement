#!/usr/bin/env python3
"""Parse DKB, Shinsei, SMBC bank statements and make them YNAB compatible."""
import logging
from argparse import (
    ArgumentParser,
)
from csv import (
    DictReader,
    DictWriter,
)
from dataclasses import (
    dataclass,
    fields,
)
from datetime import (
    date,
    datetime,
)
from decimal import (
    Decimal,
)
from glob import (
    glob,
)
from os import (
    makedirs,
    path,
)
from typing import (
    Callable,
    Generic,
    Iterable,
    List,
    Mapping,
    TypedDict,
    TypeVar,
    Union,
)

import toml


T = TypeVar("T")
CsvRow = Mapping[str, str]


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


@dataclass
class Transaction:
    """A singular transaction."""

    date: date
    num: str
    description: str
    memo: str
    withdrawal: Decimal
    deposit: Decimal


TransactionDict = TypedDict(
    "TransactionDict",
    {
        "date": str,
        "num": str,
        "description": str,
        "memo": str,
        "withdrawal": str,
        "deposit": str,
    },
)


fieldnames: List[str] = [f.name for f in fields(Transaction)]


def derive_withdrawal(withdrawal: Decimal) -> Decimal:
    """Derive withdrawal values for when deposit is negative."""
    if withdrawal < 0:
        return abs(withdrawal)
    return Decimal(0)


def at_least_0(amount: Decimal) -> Decimal:
    """Make sure this value is at least 0."""
    return max(amount, Decimal(0))


# DKB
def betrag_eur(row: CsvRow) -> Decimal:
    """Extract Betrag (EUR)."""
    return Decimal(row["Betrag (EUR)"].replace(".", "").replace(",", "."))


giro_row_parser = CsvTransactionParser(
    date=ExtractDateParser("Wertstellung", "%d.%m.%Y"),
    withdrawal=CellParser(lambda row: derive_withdrawal(betrag_eur(row))),
    deposit=CellParser(lambda row: at_least_0(betrag_eur(row))),
    description=ExtractParser("Auftraggeber / Begünstigter", str),
    memo=ExtractParser("Verwendungszweck", str),
    num=ConstantParser(""),
)
cc_row_parser = CsvTransactionParser(
    date=ExtractDateParser("Belegdatum", "%d.%m.%Y"),
    withdrawal=CellParser(lambda row: derive_withdrawal(betrag_eur(row))),
    deposit=CellParser(lambda row: at_least_0(betrag_eur(row))),
    description=ExtractParser("Beschreibung", str),
    memo=ConstantParser(""),
    num=ConstantParser(""),
)
convert_giro = CsvFormat(
    parser=giro_row_parser,
    encoding="latin_1",
    delimiter=";",
    skip=6,
    path="dkb_giro",
)
convert_cc_von_bis = CsvFormat(
    parser=cc_row_parser,
    delimiter=";",
    encoding="latin_1",
    skip=7,
    path="dkb_cc_von_bis",
)
convert_cc_zeitraum = CsvFormat(
    parser=cc_row_parser,
    delimiter=";",
    encoding="latin_1",
    skip=6,
    path="dkb_cc_zeitraum",
)


# Shinsei
shinsei_row_parser = CsvTransactionParser(
    date=ExtractDateParser("取引日", "%Y/%m/%d"),
    withdrawal=CellParser(lambda row: Decimal(row["お支払金額"] or 0)),
    deposit=CellParser(lambda row: Decimal(row["お預り金額"] or 0)),
    description=ExtractParser("摘要", str),
    memo=ConstantParser(""),
    num=ConstantParser(""),
)
shinsei_en_row_parser = CsvTransactionParser(
    date=ExtractDateParser("Value Date", "%Y/%m/%d"),
    withdrawal=CellParser(lambda row: Decimal(row["CR"] or 0)),
    deposit=CellParser(lambda row: Decimal(row["DR"] or 0)),
    description=ExtractParser("Description", str),
    memo=ConstantParser(""),
    num=ConstantParser(""),
)
new_shinsei_row_parser = CsvTransactionParser(
    date=ExtractDateParser("取引日", "%Y/%m/%d"),
    withdrawal=CellParser(lambda row: Decimal(row["出金金額"] or 0)),
    deposit=CellParser(lambda row: Decimal(row["入金金額"] or 0)),
    description=ExtractParser("摘要", str),
    memo=ConstantParser(""),
    num=ConstantParser(""),
)
new_shinsei_en_row_parser = CsvTransactionParser(
    date=ExtractDateParser("Value Date", "%Y/%m/%d"),
    withdrawal=CellParser(lambda row: Decimal(row["Debit"] or 0)),
    deposit=CellParser(lambda row: Decimal(row["Credit"] or 0)),
    description=ExtractParser("Description", str),
    memo=ConstantParser(""),
    num=ConstantParser(""),
)
convert_shinsei = CsvFormat(
    parser=shinsei_row_parser,
    encoding="utf-16",
    delimiter="\t",
    skip=8,
    path="shinsei",
)
convert_shinsei_en = CsvFormat(
    parser=shinsei_en_row_parser,
    encoding="utf-16",
    delimiter="\t",
    skip=8,
    path="shinsei_en",
)
convert_shinsei_new = CsvFormat(
    parser=new_shinsei_row_parser,
    encoding="shift-jis",
    delimiter=",",
    skip=0,
    path="shinsei_new",
)
convert_shinsei_new_en = CsvFormat(
    parser=new_shinsei_en_row_parser,
    encoding="shift-jis",
    delimiter=",",
    skip=0,
    path="shinsei_new_en",
)
convert_shinsei_new_v2 = CsvFormat(
    parser=new_shinsei_row_parser,
    encoding="utf-8-sig",
    delimiter=",",
    skip=0,
    path="shinsei_new_v2",
)


# SMBC
smbc_parser = CsvTransactionParser(
    date=ExtractDateParser("年月日", "%Y/%m/%d"),
    withdrawal=CellParser(lambda row: -Decimal(row["お引出し"] or 0)),
    deposit=CellParser(lambda row: Decimal(row["お預入れ"] or 0)),
    description=ExtractParser("お取り扱い内容", str),
    memo=ConstantParser(""),
    num=ConstantParser(""),
)
smbc_new_parser = CsvTransactionParser(
    date=ExtractDateParser("年月日", "%Y/%m/%d"),
    withdrawal=CellParser(lambda row: Decimal(row["お引出し"] or 0)),
    deposit=CellParser(lambda row: Decimal(row["お預入れ"] or 0)),
    description=ExtractParser("お取り扱い内容", str),
    memo=ConstantParser(""),
    num=ConstantParser(""),
)
convert_smbc = CsvFormat(
    parser=smbc_parser,
    encoding="shift-jis",
    delimiter=",",
    skip=0,
    path="smbc",
)
convert_smbc_new = CsvFormat(
    parser=smbc_new_parser,
    encoding="shift-jis",
    delimiter=",",
    skip=0,
    path="smbc_new",
)


# Rakuten
def 入出金(row: CsvRow) -> Decimal:
    """Extract withdrawal / deposit from Rakuten row."""
    return Decimal(row["入出金(円)"])


rakuten_parser = CsvTransactionParser(
    date=ExtractDateParser("取引日", "%Y%m%d"),
    withdrawal=CellParser(lambda row: derive_withdrawal(入出金(row))),
    deposit=CellParser(lambda row: at_least_0(入出金(row))),
    description=ExtractParser("入出金先内容", str),
    memo=ConstantParser(""),
    num=ConstantParser(""),
)
convert_rakuten = CsvFormat(
    parser=rakuten_parser,
    encoding="shift-jis",
    delimiter=",",
    skip=0,
    path="rakuten",
)


formats: Iterable[CsvFormat] = (
    # shinsei_new comes before shinsei, on purpose
    convert_shinsei_new_v2,
    convert_shinsei_new_en,
    convert_shinsei_new,
    convert_shinsei_en,
    convert_shinsei,
    convert_cc_zeitraum,
    convert_cc_von_bis,
    convert_giro,
    convert_rakuten,
    convert_smbc_new,
    convert_smbc,
)


format_mapping = {format.path: format for format in formats}


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


def read_csv(csv_path: str, fmt: CsvFormat) -> List[TransactionDict]:
    """Read a CSV file."""

    def sorting_key(row: TransactionDict) -> str:
        return row["date"]

    with open(csv_path, encoding=fmt.encoding) as fd:
        for _ in range(fmt.skip):
            fd.readline()
        reader = DictReader(fd, delimiter=fmt.delimiter)
        rows: List[CsvRow] = [row for row in reader]
    parser = fmt.parser
    transaction_rows: Iterable[Transaction] = (
        Transaction(
            date=apply_date_parser(row, parser.date),
            withdrawal=apply_parser(row, parser.withdrawal),
            deposit=apply_parser(row, parser.deposit),
            description=apply_parser(row, parser.description),
            memo=apply_parser(row, parser.memo),
            num=apply_parser(row, parser.num),
        )
        for row in rows
    )
    dict_rows: Iterable[TransactionDict] = (
        {
            "date": row.date.isoformat(),
            "num": row.num,
            "description": row.description,
            "memo": row.memo,
            "withdrawal": str(row.withdrawal),
            "deposit": str(row.deposit),
        }
        for row in transaction_rows
    )
    return sorted(dict_rows, key=sorting_key)


def get_output_path(file_path: str, in_dir: str, out_dir: str) -> str:
    """Get an output path in the output directory."""
    return path.join(
        out_dir,
        path.relpath(file_path, in_dir),
    )


def get_format_dir(file_path: str) -> str:
    """Get the base format dir name."""
    return path.basename(path.dirname(path.dirname(file_path)))


def write_csv(out_path: str, output: List[TransactionDict]) -> None:
    """
    Write rows to a csv.

    Ensure path to csv exists.
    """
    makedirs(path.dirname(out_path), exist_ok=True)
    logging.info("Writing results to '%s'", out_path)
    with open(out_path, "w") as fd:
        writer = DictWriter(fd, fieldnames=fieldnames)
        writer.writeheader()
        for row in output:
            writer.writerow(row)


def main(kwargs: Mapping[str, str]) -> None:
    """Go through files in input folder and transform CSV files."""
    in_glob = path.join(kwargs["in_dir"], "*/*/*.csv")
    logging.debug("Looking for files matching glob '%s'", in_glob)

    for csv_path in glob(in_glob, recursive=True):
        format_dir = get_format_dir(csv_path)
        try:
            fmt = format_mapping[format_dir]
        except KeyError as e:
            raise ValueError(
                "Unknown format for file '{}'".format(csv_path)
            ) from e
        logging.info("Handling file '%s' with %s", csv_path, fmt)

        output = read_csv(csv_path, fmt)

        out_path = get_output_path(
            csv_path,
            kwargs["in_dir"],
            kwargs["out_dir"],
        )
        write_csv(out_path, output)
    logging.info("Finished")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--config", default="config.toml")
    args = parser.parse_args()
    config_path: str = args.config
    with open(config_path) as fd:
        config: Mapping[str, str] = toml.load(fd)
    main(config)
