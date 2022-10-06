#!/usr/bin/env python3
"""Parse DKB, Shinsei, SMBC bank statements and make them YNAB compatible."""
import logging
from csv import (
    DictReader,
    DictWriter,
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

import toml


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def make_ynab(rows, mapping, create_negative_rows=True):
    """Make YNAB compatible dataframe."""
    selected_keys = mapping.keys()
    sub_selection = []
    for row in rows:
        sub = {}
        for key, value in row.items():
            if key not in selected_keys:
                continue
            translated_key = mapping[key]
            sub[translated_key] = value
        if create_negative_rows:
            is_negative = sub["Inflow"] < 0
            sub["Outflow"] = abs(sub["Inflow"]) if is_negative else 0
            sub["Inflow"] = sub["Inflow"] if not is_negative else 0
        sub_selection.append(sub)
    sub_selection.sort(key=lambda row: row["Date"])
    return sub_selection


def parse_dkb_row(row):
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
    return row


def parse_shinsei_row(row):
    """Parse numerical values in Shinsei data."""
    if "CR" in row:
        row["CR"] = int(row["CR"] or 0)
        row["DR"] = int(row["DR"] or 0)
    else:
        row["DR"] = int(row["お支払金額"] or 0)
        row["CR"] = int(row["お預り金額"] or 0)
        row["Value Date"] = row["取引日"]
        row["Description"] = row["摘要"]
    return row


def parse_new_shinsei_row(row):
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
    return row


def parse_new_shinsei_row_v2(row):
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
    return row


def parse_smbc_row(row):
    """Parse numerical values in a SMBC data row."""
    row["お引出し"] = -int(row["お引出し"] or 0)
    row["お預入れ"] = int(row["お預入れ"] or 0)
    return row


def parse_new_smbc_row(row):
    """Parse numerical values in a SMBC data row."""
    row["お引出し"] = int(row["お引出し"] or 0)
    row["お預入れ"] = int(row["お預入れ"] or 0)
    return row


def parse_rakuten_row(row):
    """Parse numerical values in a Rakuten data row."""
    row["取引日"] = datetime.strptime(row["取引日"], "%Y%m%d")
    row["入出金(円)"] = int(row["入出金(円)"])
    return row


def read_csv(csv_path, row_fn, encoding, delimiter, skip):
    """Read a CSV file."""
    with open(csv_path, encoding=encoding) as fd:
        for _ in range(skip):
            fd.readline()
        reader = DictReader(fd, delimiter=delimiter)
        return list(map(row_fn, reader))


def convert_shinsei(csv_path):
    """Convert Shinsei checkings account statement."""
    fields = {
        "Value Date": "Date",
        "DR": "Outflow",
        "CR": "Inflow",
        "Description": "Memo",
    }
    rows = read_csv(
        csv_path,
        parse_shinsei_row,
        encoding="utf-16",
        delimiter="\t",
        skip=8,
    )
    return make_ynab(rows, fields, create_negative_rows=False)


def convert_shinsei_new(csv_path):
    """Convert new Shinsei checkings account statement."""
    fields = {
        "Value Date": "Date",
        "DR": "Outflow",
        "CR": "Inflow",
        "Description": "Memo",
    }
    rows = read_csv(
        csv_path,
        parse_new_shinsei_row,
        encoding="shift-jis",
        delimiter=",",
        skip=0,
    )
    return make_ynab(rows, fields, create_negative_rows=False)


def convert_shinsei_new_v2(csv_path):
    """Convert new Shinsei checkings account statement."""
    fields = {
        "Value Date": "Date",
        "DR": "Outflow",
        "CR": "Inflow",
        "Description": "Memo",
    }
    rows = read_csv(
        csv_path,
        parse_new_shinsei_row_v2,
        encoding="utf-8-sig",
        delimiter=",",
        skip=0,
    )
    return make_ynab(rows, fields, create_negative_rows=False)


def convert_smbc(csv_path):
    """Convert SMBC checkings account statement."""
    fields = {
        "年月日": "Date",
        "お引出し": "Outflow",
        "お預入れ": "Inflow",
        "お取り扱い内容": "Memo",
    }
    rows = read_csv(
        csv_path,
        parse_smbc_row,
        encoding="shift-jis",
        delimiter=",",
        skip=0,
    )
    return make_ynab(rows, fields, create_negative_rows=False)


def convert_smbc_new(csv_path):
    """Convert SMBC checkings account statement."""
    fields = {
        "年月日": "Date",
        "お引出し": "Outflow",
        "お預入れ": "Inflow",
        "お取り扱い内容": "Memo",
    }
    rows = read_csv(
        csv_path,
        parse_new_smbc_row,
        encoding="shift-jis",
        delimiter=",",
        skip=0,
    )
    return make_ynab(rows, fields, create_negative_rows=False)


def convert_rakuten(csv_path):
    """Convert Rakuten checkings account statement."""
    fields = {
        "取引日": "Date",
        "入出金(円)": "Inflow",
        "入出金先内容": "Memo",
    }
    rows = read_csv(
        csv_path,
        parse_rakuten_row,
        encoding="shift-jis",
        delimiter=",",
        skip=0,
    )
    return make_ynab(rows, fields, create_negative_rows=True)


def convert_giro(csv_path):
    """Convert DKB giro account statement."""
    giro_fields = {
        "Wertstellung": "Date",
        "Betrag (EUR)": "Inflow",
        "Verwendungszweck": "Memo",
        "Auftraggeber / Begünstigter": "Payee",
    }
    rows = read_csv(
        csv_path,
        parse_dkb_row,
        encoding="latin_1",
        delimiter=";",
        skip=6,
    )
    return make_ynab(rows, giro_fields)


def convert_cc(csv_path):
    """Convert DKB credit card statement."""
    cc_fields = {
        "Belegdatum": "Date",
        "Betrag (EUR)": "Inflow",
        "Beschreibung": "Memo",
    }
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
    rows = make_ynab(rows, cc_fields)
    for row in rows:
        row["Payee"] = row["Memo"]
    return rows


def get_output_path(file_path, in_dir, out_dir):
    """Get an output path in the output directory."""
    return path.join(
        out_dir,
        path.relpath(file_path, in_dir),
    )


def main(kwargs):
    """Go through files in input folder and transform CSV files."""
    in_glob = path.join(kwargs["in_dir"], "*/*/*.csv")
    logging.debug("Looking for files matching glob '%s'", in_glob)

    for csv_path in glob(in_glob, recursive=True):
        mapping = {
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
        with open(out_path, "w") as fd:
            writer = DictWriter(fd, fieldnames=output[0].keys())
            writer.writeheader()
            for row in output:
                writer.writerow(row)
    logging.info("Finished")


if __name__ == "__main__":
    with open("config.toml") as fd:
        config = toml.load(fd)
    main(config)
