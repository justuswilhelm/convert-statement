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
    TypeVar,
)

import toml


T = TypeVar("T")
CsvRow = Mapping[str, str]


@dataclass
class CellParser(Generic[T]):
    """Parse a single cell in a csv row."""

    method: Callable[[CsvRow], T]


@dataclass
class CsvTransactionParser:
    """Parse csv rows to transaction attributes."""

    date: CellParser[datetime]
    num: CellParser[str]
    description: CellParser[str]
    memo: CellParser[str]
    withdrawal: CellParser[Decimal]
    deposit: CellParser[Decimal]


@dataclass
class CsvFormat:
    """Store format info for a CSV file."""

    parser: CsvTransactionParser
    encoding: str
    delimiter: str
    skip: int
    create_negative_rows: bool
    path: str


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Transaction:
    """A singular transaction."""

    date: datetime
    num: str
    description: str
    memo: str
    withdrawal: Decimal
    deposit: Decimal


giro_row_parser = CsvTransactionParser(
    date=CellParser(
        lambda row: datetime.strptime(row["Wertstellung"], "%d.%m.%Y")
    ),
    withdrawal=CellParser(lambda row: Decimal(0)),
    deposit=CellParser(
        lambda row: Decimal(
            row["Betrag (EUR)"].replace(".", "").replace(",", "."),
        )
    ),
    description=CellParser(lambda row: row["Auftraggeber / Begünstigter"]),
    memo=CellParser(lambda row: row["Verwendungszweck"]),
    num=CellParser(lambda row: ""),
)


cc_row_parser = CsvTransactionParser(
    date=CellParser(
        lambda row: datetime.strptime(row["Belegdatum"], "%d.%m.%Y")
    ),
    withdrawal=CellParser(lambda row: Decimal(0)),
    deposit=CellParser(
        lambda row: Decimal(
            row["Betrag (EUR)"].replace(".", "").replace(",", "."),
        )
    ),
    description=CellParser(lambda row: row["Beschreibung"]),
    memo=CellParser(lambda row: ""),
    num=CellParser(lambda row: ""),
)


convert_giro = CsvFormat(
    parser=giro_row_parser,
    encoding="latin_1",
    delimiter=";",
    skip=6,
    create_negative_rows=True,
    path="dkb_giro",
)


convert_cc_von_bis = CsvFormat(
    parser=cc_row_parser,
    delimiter=";",
    encoding="latin_1",
    skip=7,
    create_negative_rows=True,
    path="dkb_cc_von_bis",
)


convert_cc_zeitraum = CsvFormat(
    parser=cc_row_parser,
    delimiter=";",
    encoding="latin_1",
    skip=6,
    create_negative_rows=True,
    path="dkb_cc_zeitraum",
)


shinsei_row_parser = CsvTransactionParser(
    date=CellParser(lambda row: datetime.strptime(row["取引日"], "%Y/%m/%d")),
    withdrawal=CellParser(lambda row: Decimal(row["お支払金額"] or 0)),
    deposit=CellParser(lambda row: Decimal(row["お預り金額"] or 0)),
    description=CellParser(lambda row: row["摘要"]),
    memo=CellParser(lambda row: ""),
    num=CellParser(lambda row: ""),
)


shinsei_en_row_parser = CsvTransactionParser(
    date=CellParser(
        lambda row: datetime.strptime(row["Value Date"], "%Y/%m/%d")
    ),
    withdrawal=CellParser(lambda row: Decimal(row["CR"] or 0)),
    deposit=CellParser(lambda row: Decimal(row["DR"] or 0)),
    description=CellParser(lambda row: row["Description"]),
    memo=CellParser(lambda row: ""),
    num=CellParser(lambda row: ""),
)


new_shinsei_row_parser = CsvTransactionParser(
    date=CellParser(lambda row: datetime.strptime(row["取引日"], "%Y/%m/%d")),
    withdrawal=CellParser(lambda row: Decimal(row["出金金額"] or 0)),
    deposit=CellParser(lambda row: Decimal(row["入金金額"] or 0)),
    description=CellParser(lambda row: row["摘要"]),
    memo=CellParser(lambda row: ""),
    num=CellParser(lambda row: ""),
)


new_shinsei_en_row_parser = CsvTransactionParser(
    date=CellParser(
        lambda row: datetime.strptime(row["Value Date"], "%Y/%m/%d")
    ),
    withdrawal=CellParser(lambda row: Decimal(row["Debit"] or 0)),
    deposit=CellParser(lambda row: Decimal(row["Credit"] or 0)),
    description=CellParser(lambda row: row["Description"]),
    memo=CellParser(lambda row: ""),
    num=CellParser(lambda row: ""),
)


convert_shinsei = CsvFormat(
    parser=shinsei_row_parser,
    encoding="utf-16",
    delimiter="\t",
    skip=8,
    create_negative_rows=False,
    path="shinsei",
)


convert_shinsei_en = CsvFormat(
    parser=shinsei_en_row_parser,
    encoding="utf-16",
    delimiter="\t",
    skip=8,
    create_negative_rows=False,
    path="shinsei_en",
)


convert_shinsei_new = CsvFormat(
    parser=new_shinsei_row_parser,
    encoding="shift-jis",
    delimiter=",",
    skip=0,
    create_negative_rows=False,
    path="shinsei_new",
)


convert_shinsei_new_en = CsvFormat(
    parser=new_shinsei_en_row_parser,
    encoding="shift-jis",
    delimiter=",",
    skip=0,
    create_negative_rows=False,
    path="shinsei_new_en",
)


convert_shinsei_new_v2 = CsvFormat(
    parser=new_shinsei_row_parser,
    encoding="utf-8-sig",
    delimiter=",",
    skip=0,
    create_negative_rows=False,
    path="shinsei_new_v2",
)


smbc_parser = CsvTransactionParser(
    date=CellParser(lambda row: datetime.strptime(row["年月日"], "%Y/%m/%d")),
    withdrawal=CellParser(lambda row: -Decimal(row["お引出し"] or 0)),
    deposit=CellParser(lambda row: Decimal(row["お預入れ"] or 0)),
    description=CellParser(lambda row: row["お取り扱い内容"]),
    memo=CellParser(lambda row: ""),
    num=CellParser(lambda row: ""),
)


smbc_new_parser = CsvTransactionParser(
    date=CellParser(lambda row: datetime.strptime(row["年月日"], "%Y/%m/%d")),
    withdrawal=CellParser(lambda row: Decimal(row["お引出し"] or 0)),
    deposit=CellParser(lambda row: Decimal(row["お預入れ"] or 0)),
    description=CellParser(lambda row: row["お取り扱い内容"]),
    memo=CellParser(lambda row: ""),
    num=CellParser(lambda row: ""),
)


convert_smbc = CsvFormat(
    parser=smbc_parser,
    encoding="shift-jis",
    delimiter=",",
    skip=0,
    create_negative_rows=False,
    path="smbc",
)


convert_smbc_new = CsvFormat(
    parser=smbc_new_parser,
    encoding="shift-jis",
    delimiter=",",
    skip=0,
    create_negative_rows=False,
    path="smbc_new",
)


rakuten_parser = CsvTransactionParser(
    date=CellParser(lambda row: datetime.strptime(row["取引日"], "%Y%m%d")),
    withdrawal=CellParser(lambda _: Decimal(0)),
    deposit=CellParser(lambda row: Decimal(row["入出金(円)"])),
    description=CellParser(lambda row: row["入出金先内容"]),
    memo=CellParser(lambda row: ""),
    num=CellParser(lambda row: ""),
)


convert_rakuten = CsvFormat(
    parser=rakuten_parser,
    encoding="shift-jis",
    delimiter=",",
    skip=0,
    create_negative_rows=True,
    path="rakuten",
)


def apply_parser(parser: CsvTransactionParser, row: CsvRow) -> Transaction:
    """Apply a parser to a CSV row."""
    return Transaction(
        date=parser.date.method(row),
        withdrawal=parser.withdrawal.method(row),
        deposit=parser.deposit.method(row),
        description=parser.description.method(row),
        memo=parser.memo.method(row),
        num=parser.num.method(row),
    )


def process_one_row(row: Transaction, create_negative_row: bool) -> CsvRow:
    """Process one row."""
    if create_negative_row:
        is_negative = row.deposit < 0
        withdrawal = abs(row.deposit) if is_negative else 0
        deposit = row.deposit if not is_negative else 0
    else:
        withdrawal = row.withdrawal
        deposit = row.deposit
    return {
        "date": str(row.date),
        "num": row.num,
        "description": row.description,
        "memo": row.memo,
        "withdrawal": str(withdrawal),
        "deposit": str(deposit),
    }


def read_csv(
    csv_path: str,
    parser: CsvTransactionParser,
    encoding: str,
    delimiter: str,
    skip: int,
    create_negative_rows: bool = True,
) -> List[CsvRow]:
    """Read a CSV file."""
    with open(csv_path, encoding=encoding) as fd:
        for _ in range(skip):
            fd.readline()
        reader = DictReader(fd, delimiter=delimiter)
        rows = [apply_parser(parser, row) for row in reader]
        return sorted(
            (process_one_row(r, create_negative_rows) for r in rows),
            key=lambda row: row["date"],
        )


def get_output_path(file_path: str, in_dir: str, out_dir: str) -> str:
    """Get an output path in the output directory."""
    return path.join(
        out_dir,
        path.relpath(file_path, in_dir),
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


fieldnames: List[str] = [f.name for f in fields(Transaction)]


def process_csv(csv_path: str, fmt: CsvFormat) -> List[CsvRow]:
    """Process one CSV and return csv rows."""
    return read_csv(
        csv_path,
        fmt.parser,
        encoding=fmt.encoding,
        delimiter=fmt.delimiter,
        skip=fmt.skip,
        create_negative_rows=fmt.create_negative_rows,
    )


def write_csv(out_path: str, output: List[CsvRow]) -> None:
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
        for fmt in formats:
            if fmt.path in csv_path:
                break
        else:
            raise ValueError("Unknown format for file '{}'".format(csv_path))
        logging.info("Handling file '%s' with %s", csv_path, fmt)

        output = process_csv(csv_path, fmt)

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
    with open(args.config) as fd:
        config = toml.load(fd)
    main(config)
