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
    List,
    Mapping,
)

import toml


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


def convert_giro(csv_path: str) -> List[Dict[str, Any]]:
    """Convert DKB giro account statement."""
    rows = read_csv(
        csv_path,
        parse_dkb_row,
        encoding="latin_1",
        delimiter=";",
        skip=6,
    )
    return make_ynab(rows)


def convert_cc(csv_path: str) -> List[Dict[str, Any]]:
    """Convert DKB credit card statement."""
    try:
        rows = read_csv(
            csv_path,
            parse_dkb_row,
            delimiter=";",
            encoding="latin_1",
            skip=6,
        )
    except KeyError:
        logging.warning("Encountered new DKB format in %s", csv_path)
        rows = read_csv(
            csv_path,
            parse_dkb_row,
            delimiter=";",
            encoding="latin_1",
            skip=7,
        )
    return make_ynab(rows)


def parse_shinsei_row(row: Dict[str, Any]) -> Transaction:
    """Parse numerical values in Shinsei data."""
    if "CR" in row:
        row["CR"] = int(row["CR"] or 0)
        row["DR"] = int(row["DR"] or 0)
    else:
        row["DR"] = int(row["お支払金額"] or 0)
        row["CR"] = int(row["お預り金額"] or 0)
        row["Value Date"] = row["取引日"]
        row["Description"] = row["摘要"]
    return Transaction(
        date=row["Value Date"],
        withdrawal=row["DR"],
        deposit=row["CR"],
        description=row["Description"],
        memo="",
        num="",
    )


def parse_new_shinsei_row(row: Dict[str, Any]) -> Transaction:
    """Parse numerical values in new Shinsei data."""
    try:
        row["DR"] = int(row["出金金額"] or 0)
        row["CR"] = int(row["入金金額"] or 0)
        row["Value Date"] = row["取引日"]
        row["Description"] = row["摘要"]
    # English Version!
    except KeyError:
        row["DR"] = int(row["Debit"] or 0)
        row["CR"] = int(row["Credit"] or 0)
    return Transaction(
        date=row["Value Date"],
        withdrawal=row["DR"],
        deposit=row["CR"],
        description=row["Description"],
        memo="",
        num="",
    )


def parse_new_shinsei_row_v2(row: Dict[str, Any]) -> Transaction:
    """Parse numerical values in new Shinsei v2 data."""
    try:
        row["DR"] = int(row["出金金額"] or 0)
        row["CR"] = int(row["入金金額"] or 0)
        row["Value Date"] = row["取引日"]
        row["Description"] = row["摘要"]
    # English Version!
    except KeyError:
        row["DR"] = int(row["Debit"] or 0)
        row["CR"] = int(row["Credit"] or 0)
    return Transaction(
        date=row["Value Date"],
        withdrawal=row["DR"],
        deposit=row["CR"],
        description=row["Description"],
        memo="",
        num="",
    )


def convert_shinsei(csv_path: str) -> List[Dict[str, Any]]:
    """Convert Shinsei checkings account statement."""
    rows = read_csv(
        csv_path,
        parse_shinsei_row,
        encoding="utf-16",
        delimiter="\t",
        skip=8,
    )
    return make_ynab(rows, create_negative_rows=False)


def convert_shinsei_new(csv_path: str) -> List[Dict[str, Any]]:
    """Convert new Shinsei checkings account statement."""
    rows = read_csv(
        csv_path,
        parse_new_shinsei_row,
        encoding="shift-jis",
        delimiter=",",
        skip=0,
    )
    return make_ynab(rows, create_negative_rows=False)


def convert_shinsei_new_v2(csv_path: str) -> List[Dict[str, Any]]:
    """Convert new Shinsei checkings account statement."""
    rows = read_csv(
        csv_path,
        parse_new_shinsei_row_v2,
        encoding="utf-8-sig",
        delimiter=",",
        skip=0,
    )
    return make_ynab(rows, create_negative_rows=False)


def parse_smbc_row(row: Dict[str, Any]) -> Transaction:
    """Parse numerical values in a SMBC data row."""
    row["お引出し"] = -int(row["お引出し"] or 0)
    row["お預入れ"] = int(row["お預入れ"] or 0)
    return Transaction(
        date=row["年月日"],
        withdrawal=row["お引出し"],
        deposit=row["お預入れ"],
        description=row["お取り扱い内容"],
        memo="",
        num="",
    )


def parse_new_smbc_row(row: Dict[str, Any]) -> Transaction:
    """Parse numerical values in a SMBC data row."""
    row["お引出し"] = int(row["お引出し"] or 0)
    row["お預入れ"] = int(row["お預入れ"] or 0)
    return Transaction(
        date=row["年月日"],
        withdrawal=row["お引出し"],
        deposit=row["お預入れ"],
        description=row["お取り扱い内容"],
        memo="",
        num="",
    )


def parse_rakuten_row(row: Dict[str, Any]) -> Transaction:
    """Parse numerical values in a Rakuten data row."""
    row["取引日"] = datetime.strptime(row["取引日"], "%Y%m%d")
    row["入出金(円)"] = int(row["入出金(円)"])
    return Transaction(
        date=row["取引日"],
        withdrawal=Decimal(0),
        deposit=row["入出金(円)"],
        description=row["入出金先内容"],
        memo="",
        num="",
    )


def convert_rakuten(csv_path: str) -> List[Dict[str, Any]]:
    """Convert Rakuten checkings account statement."""
    rows = read_csv(
        csv_path,
        parse_rakuten_row,
        encoding="shift-jis",
        delimiter=",",
        skip=0,
    )
    return make_ynab(rows, create_negative_rows=True)


def read_csv(
    csv_path: str,
    row_fn: Callable[[Dict[str, str]], Transaction],
    encoding: str,
    delimiter: str,
    skip: int,
) -> List[Transaction]:
    """Read a CSV file."""
    with open(csv_path, encoding=encoding) as fd:
        for _ in range(skip):
            fd.readline()
        reader = DictReader(fd, delimiter=delimiter)
        return list(map(row_fn, reader))


def convert_smbc(csv_path: str) -> List[Dict[str, Any]]:
    """Convert SMBC checkings account statement."""
    rows = read_csv(
        csv_path,
        parse_smbc_row,
        encoding="shift-jis",
        delimiter=",",
        skip=0,
    )
    return make_ynab(rows, create_negative_rows=False)


def convert_smbc_new(csv_path: str) -> List[Dict[str, Any]]:
    """Convert SMBC checkings account statement."""
    rows = read_csv(
        csv_path,
        parse_new_smbc_row,
        encoding="shift-jis",
        delimiter=",",
        skip=0,
    )
    return make_ynab(rows, create_negative_rows=False)


def get_output_path(file_path: str, in_dir: str, out_dir: str) -> str:
    """Get an output path in the output directory."""
    return path.join(
        out_dir,
        path.relpath(file_path, in_dir),
    )


def main(kwargs: Mapping[str, str]) -> None:
    """Go through files in input folder and transform CSV files."""
    in_glob = path.join(kwargs["in_dir"], "*/*/*.csv")
    logging.debug("Looking for files matching glob '%s'", in_glob)

    for csv_path in glob(in_glob, recursive=True):
        mapping: Mapping[str, Callable[[str], List[Dict[str, Any]]]] = {
            # shinsei_new comes before shinsei, on purpose
            "shinsei_new_v2": convert_shinsei_new_v2,
            "shinsei_new": convert_shinsei_new,
            "shinsei": convert_shinsei,
            "dkb_cc": convert_cc,
            "dkb_giro": convert_giro,
            "rakuten": convert_rakuten,
            "smbc_new": convert_smbc_new,
            "smbc": convert_smbc,
        }
        for k, fn in mapping.items():
            if k in csv_path:
                break
        else:
            raise ValueError("Unknown format for file '{}'".format(csv_path))
        logging.info("Handling file '%s' with %s", csv_path, fn)
        output = fn(csv_path)

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
