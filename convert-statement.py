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
from parser.dkb import (
    convert_cc_von_bis,
    convert_cc_zeitraum,
    convert_giro,
)
from parser.format import (
    CellParser,
    ConstantParser,
    CsvFormat,
    CsvRow,
    CsvTransactionParser,
    ExtractDateParser,
    ExtractParser,
    apply_date_parser,
    apply_parser,
)
from parser.helper import (
    at_least_0,
    derive_withdrawal,
)
from parser.shinsei import (
    convert_shinsei,
    convert_shinsei_en,
    convert_shinsei_new,
    convert_shinsei_new_en,
    convert_shinsei_new_v2,
)
from parser.smbc import (
    convert_smbc,
    convert_smbc_new,
)
from typing import (
    Iterable,
    List,
    Mapping,
    TypedDict,
)

import toml


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
