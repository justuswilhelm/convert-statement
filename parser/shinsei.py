"""Contain the Shinsei parsers."""
from decimal import (
    Decimal,
)
from parser.format import (
    CellParser,
    ConstantParser,
    CsvFormat,
    CsvTransactionParser,
    ExtractDateParser,
    ExtractParser,
)


shinsei_row_parser = CsvTransactionParser(
    date=ExtractDateParser("取引日", "%Y/%m/%d"),
    withdrawal=CellParser(lambda row: Decimal(row["お支払金額"] or 0)),
    deposit=CellParser(lambda row: Decimal(row["お預り金額"] or 0)),
    description=ExtractParser("摘要", str),
    memo=ConstantParser(""),
    num=ConstantParser(""),
)
shinsei_en_row_parser = CsvTransactionParser(
    date=ExtractDateParser("Value Date", "%Y/%m/%d"),
    withdrawal=CellParser(lambda row: Decimal(row["CR"] or 0)),
    deposit=CellParser(lambda row: Decimal(row["DR"] or 0)),
    description=ExtractParser("Description", str),
    memo=ConstantParser(""),
    num=ConstantParser(""),
)
new_shinsei_row_parser = CsvTransactionParser(
    date=ExtractDateParser("取引日", "%Y/%m/%d"),
    withdrawal=CellParser(lambda row: Decimal(row["出金金額"] or 0)),
    deposit=CellParser(lambda row: Decimal(row["入金金額"] or 0)),
    description=ExtractParser("摘要", str),
    memo=ConstantParser(""),
    num=ConstantParser(""),
)
new_shinsei_en_row_parser = CsvTransactionParser(
    date=ExtractDateParser("Value Date", "%Y/%m/%d"),
    withdrawal=CellParser(lambda row: Decimal(row["Debit"] or 0)),
    deposit=CellParser(lambda row: Decimal(row["Credit"] or 0)),
    description=ExtractParser("Description", str),
    memo=ConstantParser(""),
    num=ConstantParser(""),
)
convert_shinsei = CsvFormat(
    parser=shinsei_row_parser,
    encoding="utf-16",
    delimiter="\t",
    skip=8,
    path="shinsei",
)
convert_shinsei_en = CsvFormat(
    parser=shinsei_en_row_parser,
    encoding="utf-16",
    delimiter="\t",
    skip=8,
    path="shinsei_en",
)
convert_shinsei_new = CsvFormat(
    parser=new_shinsei_row_parser,
    encoding="shift-jis",
    delimiter=",",
    skip=0,
    path="shinsei_new",
)
convert_shinsei_new_en = CsvFormat(
    parser=new_shinsei_en_row_parser,
    encoding="shift-jis",
    delimiter=",",
    skip=0,
    path="shinsei_new_en",
)
convert_shinsei_new_v2 = CsvFormat(
    parser=new_shinsei_row_parser,
    encoding="utf-8-sig",
    delimiter=",",
    skip=0,
    path="shinsei_new_v2",
)
