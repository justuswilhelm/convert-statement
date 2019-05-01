#!/usr/bin/env python3
from argparse import ArgumentParser
from csv import DictReader
from datetime import datetime
from decimal import Decimal
from glob import glob
from os import makedirs, path

import pandas as pd


def make_ynab(df, mapping, create_negative_rows=True):
    df = df[list(mapping.keys())]
    df = df.rename(mapping, axis=1)
    df = df.set_index('Date')
    df = df.sort_index()
    if create_negative_rows:
        negative_rows = df.Inflow < 0
        df['Outflow'] = df.Inflow.mask(~negative_rows, 0).abs()
        df.Inflow = df.Inflow.mask(negative_rows, 0)
    return df


def parse_dkb_row(row):
    row['Wertstellung'] = datetime.strptime(
        row['Wertstellung'],
        "%d.%m.%Y",
    )
    row['Betrag (EUR)'] = Decimal(
        row['Betrag (EUR)'].replace(
            '.', ''
        ).replace(',', '.')
    )
    del row['']
    return row


def parse_shinsei_row(row):
    if 'CR' in row:
        row['CR'] = int(row['CR'] or 0)
        row['DR'] = int(row['DR'] or 0)
    else:
        row['DR'] = int(row['お支払金額'] or 0)
        row['CR'] = int(row['お預り金額'] or 0)
        row['Value Date'] = row['取引日']
        row['Description'] = row['摘要']
    return row


def read_csv(csv_path, row_fn, encoding='latin_1', skip=6, delimiter=';'):
    with open(csv_path, encoding=encoding) as fd:
        for _ in range(skip):
            fd.readline()
        reader = DictReader(fd, delimiter=delimiter)
        rows = list(map(row_fn, reader))
    return pd.DataFrame(rows)


def convert_shinsei(csv_path):
    fields = {
        'Value Date': 'Date',
        'DR': 'Outflow',
        'CR': 'Inflow',
        'Description': 'Memo',
    }
    df = read_csv(
        csv_path,
        parse_shinsei_row,
        encoding='utf-16',
        skip=8,
        delimiter='\t',
    )
    return make_ynab(df, fields, create_negative_rows=False)


def convert_giro(csv_path):
    giro_fields = {
        'Wertstellung': 'Date',
        'Betrag (EUR)': 'Inflow',
        'Verwendungszweck': 'Memo',
        'Auftraggeber / Begünstigter': 'Payee',
    }
    df = read_csv(csv_path, parse_dkb_row)
    return make_ynab(df, giro_fields)


def convert_cc(csv_path):
    cc_fields = {
        'Wertstellung': 'Date',
        'Betrag (EUR)': 'Inflow',
        'Beschreibung': 'Memo',
    }
    try:
        df = read_csv(csv_path, parse_dkb_row)
    except KeyError:
        print("New DKB CC format")
        df = read_csv(csv_path, parse_dkb_row, skip=7)
    df_ynab = make_ynab(df, cc_fields)
    df_ynab['Payee'] = df_ynab['Memo']
    return df_ynab


def get_output_path(file_path, in_dir, out_dir):
    return path.join(
        out_dir,
        path.relpath(file_path, in_dir),
    )


def main(kwargs):
    in_glob = path.join(kwargs['in-dir'], '*/*.csv')
    print("Looking for files matching", in_glob)

    for csv_path in glob(in_glob, recursive=True):
        print("Handling", csv_path)
        mapping = {
            'shinsei': convert_shinsei,
            'dkb_cc': convert_cc,
            'dkb_giro': convert_giro,
        }
        for k, fn in mapping.items():
            if k in csv_path:
                break
        else:
            raise ValueError("Unknown format for file '{}'".format(csv_path))
        output = fn(csv_path)

        out_path = get_output_path(
            csv_path,
            kwargs['in-dir'],
            kwargs['out-dir'],
        )
        makedirs(path.dirname(out_path), exist_ok=True)
        output.to_csv(out_path)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('in-dir')
    parser.add_argument('out-dir')
    main(vars(parser.parse_args()))
