"""Contain the SMBC parsers."""
from decimal import (
    Decimal,
)

from parse.format import (
    CellParser,
    ConstantParser,
    CsvFormat,
    CsvTransactionParser,
    ExtractDateParser,
    ExtractParser,
)


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
convert_smbc_v1 = CsvFormat(
    parser=smbc_parser,
    encoding="shift-jis",
    delimiter=",",
    skip=0,
    path="smbc_v1",
)
convert_smbc_v2 = CsvFormat(
    parser=smbc_new_parser,
    encoding="shift-jis",
    delimiter=",",
    skip=0,
    path="smbc_v2",
)