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
    asdict,
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
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Union,
)

import toml


CsvReaderInput = Dict[str, str]
CsvReaderInputMapping = Mapping[str, str]


@dataclass
class CsvTransactionParser:
    """Parse csv rows to transaction attributes."""

    date: Callable[[CsvReaderInput], datetime]
    num: Callable[[CsvReaderInput], str]
    description: Callable[[CsvReaderInput], str]
    memo: Callable[[CsvReaderInput], str]
    withdrawal: Callable[[Decimal], str]
    deposit: Callable[[Decimal], str]


@dataclass
class SimpleCsvTransactionParser:
    """Parse csv rows to transaction attributes, legacy."""

    method: Callable[[Dict[str, Any]], "Transaction"]


@dataclass
class CsvFormat:
    """Store format info for a CSV file."""

    parser: Union[CsvTransactionParser, SimpleCsvTransactionParser]
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


def make_ynab(
    rows: List[Transaction],
    create_negative_rows: bool = True,
) -> List[Dict[str, Any]]:
    """Make YNAB compatible dataframe."""
    sub_selection = []
    for row in rows:
        sub = asdict(row)
        if create_negative_rows:
            is_negative = sub["deposit"] < 0
            sub["withdrawal"] = abs(sub["deposit"]) if is_negative else 0
            sub["deposit"] = sub["deposit"] if not is_negative else 0
        sub_selection.append(sub)
    sub_selection.sort(key=lambda row: str(row["date"]))
    return sub_selection


def parse_dkb_row(row: Dict[str, Any]) -> Transaction:
    """Parse dates and numerical values in DKB data."""
    row["Wertstellung"] = datetime.strptime(
        row["Wertstellung"],
        "%d.%m.%Y",
    )
    if "Belegdatum" in row:
        row["Belegdatum"] = datetime.strptime(
            row["Belegdatum"],
            "%d.%m.%Y",
        )
    if "Buchungstag" in row:
        row["Buchungstag"] = datetime.strptime(
            row["Buchungstag"],
            "%d.%m.%Y",
        )
    row["Betrag (EUR)"] = Decimal(
        row["Betrag (EUR)"].replace(".", "").replace(",", ".")
    )
    del row[""]
    description = row.get("Auftraggeber / Begünstigter", None)
    if description is None:
        description = row["Beschreibung"]
    return Transaction(
        date=row.get("Belegdatum", None) or row["Wertstellung"],
        withdrawal=Decimal(0),
        deposit=row["Betrag (EUR)"],
        description=description,
        memo=row.get("Verwendungszweck", None),
        num="",
    )


convert_giro = CsvFormat(
    parser=SimpleCsvTransactionParser(parse_dkb_row),
    encoding="latin_1",
    delimiter=";",
    skip=6,
    create_negative_rows=True,
    path="dkb_giro",
)


convert_cc_von_bis = CsvFormat(
    parser=SimpleCsvTransactionParser(parse_dkb_row),
    delimiter=";",
    encoding="latin_1",
    skip=7,
    create_negative_rows=True,
    path="dkb_cc_von_bis",
)


convert_cc_zeitraum = CsvFormat(
    parser=SimpleCsvTransactionParser(parse_dkb_row),
    delimiter=";",
    encoding="latin_1",
    skip=6,
    create_negative_rows=True,
    path="dkb_cc_zeitraum",
)


def parse_shinsei_row(row: CsvReaderInput) -> Transaction:
    """Parse numerical values in Japanese Shinsei data."""
    return Transaction(
        date=datetime.strptime(row["取引日"], "%Y/%m/%d"),
        withdrawal=Decimal(row["お支払金額"] or 0),
        deposit=Decimal(row["お預り金額"] or 0),
        description=row["摘要"],
        memo="",
        num="",
    )


def parse_shinsei_en_row(row: CsvReaderInput) -> Transaction:
    """Parse numerical values in English Shinsei data."""
    return Transaction(
        date=datetime.strptime(row["Value Date"], "%Y/%m/%d"),
        withdrawal=Decimal(row["CR"] or 0),
        deposit=Decimal(row["DR"] or 0),
        description=row["Description"],
        memo="",
        num="",
    )


def parse_new_shinsei_row(row: CsvReaderInput) -> Transaction:
    """Parse numerical values in Japanese new Shinsei data."""
    return Transaction(
        date=datetime.strptime(row["取引日"], "%Y/%m/%d"),
        withdrawal=Decimal(row["出金金額"] or 0),
        deposit=Decimal(row["入金金額"] or 0),
        description=row["摘要"],
        memo="",
        num="",
    )


def parse_new_shinsei_en_row(row: CsvReaderInput) -> Transaction:
    """Parse numerical values in English new Shinsei data."""
    return Transaction(
        date=datetime.strptime(row["Value Date"], "%Y/%m/%d"),
        withdrawal=Decimal(row["Debit"] or 0),
        deposit=Decimal(row["Credit"] or 0),
        description=row["Description"],
        memo="",
        num="",
    )


def parse_new_shinsei_row_v2(row: CsvReaderInput) -> Transaction:
    """Parse numerical values in new Shinsei v2 data."""
    try:
        withdrawal = Decimal(row["出金金額"] or 0)
        deposit = Decimal(row["入金金額"] or 0)
        date = row["取引日"]
        description = row["摘要"]
    # English Version!
    except KeyError:
        withdrawal = Decimal(row["Debit"] or 0)
        deposit = Decimal(row["Credit"] or 0)
        date = row["Value Date"]
        description = row["Description"]
    return Transaction(
        date=datetime.strptime(date, "%Y/%m/%d"),
        withdrawal=withdrawal,
        deposit=deposit,
        description=description,
        memo="",
        num="",
    )


convert_shinsei = CsvFormat(
    parser=SimpleCsvTransactionParser(parse_shinsei_row),
    encoding="utf-16",
    delimiter="\t",
    skip=8,
    create_negative_rows=False,
    path="shinsei",
)


convert_shinsei_en = CsvFormat(
    parser=SimpleCsvTransactionParser(parse_shinsei_en_row),
    encoding="utf-16",
    delimiter="\t",
    skip=8,
    create_negative_rows=False,
    path="shinsei_en",
)


convert_shinsei_new = CsvFormat(
    parser=SimpleCsvTransactionParser(parse_new_shinsei_row),
    encoding="shift-jis",
    delimiter=",",
    skip=0,
    create_negative_rows=False,
    path="shinsei_new",
)


convert_shinsei_new_en = CsvFormat(
    parser=SimpleCsvTransactionParser(parse_new_shinsei_en_row),
    encoding="shift-jis",
    delimiter=",",
    skip=0,
    create_negative_rows=False,
    path="shinsei_new_en",
)


convert_shinsei_new_v2 = CsvFormat(
    parser=SimpleCsvTransactionParser(parse_new_shinsei_row_v2),
    encoding="utf-8-sig",
    delimiter=",",
    skip=0,
    create_negative_rows=False,
    path="shinsei_new_v2",
)


def parse_smbc_row(row: CsvReaderInputMapping) -> Transaction:
    """Parse numerical values in a SMBC data row."""
    return Transaction(
        date=datetime.strptime(row["年月日"], "%Y/%m/%d"),
        withdrawal=-Decimal(row["お引出し"] or 0),
        deposit=Decimal(row["お預入れ"] or 0),
        description=row["お取り扱い内容"],
        memo="",
        num="",
    )


def parse_new_smbc_row(row: CsvReaderInputMapping) -> Transaction:
    """Parse numerical values in a SMBC data row."""
    return Transaction(
        date=datetime.strptime(row["年月日"], "%Y/%m/%d"),
        withdrawal=Decimal(row["お引出し"] or 0),
        deposit=Decimal(row["お預入れ"] or 0),
        description=row["お取り扱い内容"],
        memo="",
        num="",
    )


convert_smbc = CsvFormat(
    parser=SimpleCsvTransactionParser(parse_smbc_row),
    encoding="shift-jis",
    delimiter=",",
    skip=0,
    create_negative_rows=False,
    path="smbc",
)


convert_smbc_new = CsvFormat(
    parser=SimpleCsvTransactionParser(parse_new_smbc_row),
    encoding="shift-jis",
    delimiter=",",
    skip=0,
    create_negative_rows=False,
    path="smbc_new",
)


def parse_rakuten_row(row: CsvReaderInputMapping) -> Transaction:
    """Parse numerical values in a Rakuten data row."""
    return Transaction(
        date=datetime.strptime(row["取引日"], "%Y%m%d"),
        withdrawal=Decimal(0),
        deposit=Decimal(row["入出金(円)"]),
        description=row["入出金先内容"],
        memo="",
        num="",
    )


convert_rakuten = CsvFormat(
    parser=SimpleCsvTransactionParser(parse_rakuten_row),
    encoding="shift-jis",
    delimiter=",",
    skip=0,
    create_negative_rows=True,
    path="rakuten",
)


def read_csv(
    csv_path: str,
    simple_parser: SimpleCsvTransactionParser,
    encoding: str,
    delimiter: str,
    skip: int,
) -> List[Transaction]:
    """Read a CSV file."""
    with open(csv_path, encoding=encoding) as fd:
        for _ in range(skip):
            fd.readline()
        reader = DictReader(fd, delimiter=delimiter)
        return list(map(simple_parser.method, reader))


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

        if isinstance(fmt.parser, SimpleCsvTransactionParser):
            rows = read_csv(
                csv_path,
                fmt.parser,
                encoding=fmt.encoding,
                delimiter=fmt.delimiter,
                skip=fmt.skip,
            )
        else:
            rows = []
            logging.error("%s not supported", fmt.parser)
        output = make_ynab(
            rows,
            create_negative_rows=fmt.create_negative_rows,
        )

        out_path = get_output_path(
            csv_path,
            kwargs["in_dir"],
            kwargs["out_dir"],
        )
        makedirs(path.dirname(out_path), exist_ok=True)
        logging.info("Writing results to '%s'", out_path)
        fieldnames = [f.name for f in fields(Transaction)]
        with open(out_path, "w") as fd:
            writer = DictWriter(fd, fieldnames=fieldnames)
            writer.writeheader()
            for row in output:
                writer.writerow(row)
    logging.info("Finished")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--config", default="config.toml")
    args = parser.parse_args()
    with open(args.config) as fd:
        config = toml.load(fd)
    main(config)
