"""Contain the DKB parsers."""
from decimal import (
    Decimal,
)
from parser.format import (
    CellParser,
    ConstantParser,
    CsvFormat,
    CsvRow,
    CsvTransactionParser,
    ExtractDateParser,
    ExtractParser,
)
from parser.helper import (
    abs_if_negative_else_0,
    at_least_0,
)


def betrag_eur(row: CsvRow) -> Decimal:
    """Extract Betrag (EUR)."""
    return Decimal(row["Betrag (EUR)"].replace(".", "").replace(",", "."))


giro_row_parser = CsvTransactionParser(
    date=ExtractDateParser("Wertstellung", "%d.%m.%Y"),
    withdrawal=CellParser(lambda row: abs_if_negative_else_0(betrag_eur(row))),
    deposit=CellParser(lambda row: at_least_0(betrag_eur(row))),
    description=ExtractParser("Auftraggeber / Begünstigter", str),
    memo=ExtractParser("Verwendungszweck", str),
    num=ConstantParser(""),
)
cc_row_parser = CsvTransactionParser(
    date=ExtractDateParser("Belegdatum", "%d.%m.%Y"),
    withdrawal=CellParser(lambda row: abs_if_negative_else_0(betrag_eur(row))),
    deposit=CellParser(lambda row: at_least_0(betrag_eur(row))),
    description=ExtractParser("Beschreibung", str),
    memo=ConstantParser(""),
    num=ConstantParser(""),
)
convert_giro_v1 = CsvFormat(
    parser=giro_row_parser,
    encoding="latin_1",
    delimiter=";",
    skip=6,
    path="dkb_giro_v1",
)
convert_cc_von_bis_v1 = CsvFormat(
    parser=cc_row_parser,
    delimiter=";",
    encoding="latin_1",
    skip=7,
    path="dkb_cc_von_bis_v1",
)
convert_cc_zeitraum_v1 = CsvFormat(
    parser=cc_row_parser,
    delimiter=";",
    encoding="latin_1",
    skip=6,
    path="dkb_cc_zeitraum_v1",
)
