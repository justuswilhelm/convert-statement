"""Contain the SMBC parsers."""
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
convert_rakuten_v1 = CsvFormat(
    parser=rakuten_parser,
    encoding="shift-jis",
    delimiter=",",
    skip=0,
    path="rakuten_v1",
)
