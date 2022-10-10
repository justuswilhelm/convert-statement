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
    at_least_0,
    derive_withdrawal,
)


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
