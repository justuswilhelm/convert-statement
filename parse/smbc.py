"""Contain the SMBC parsers."""
import re
from decimal import (
    Decimal,
)

from parse.format import (
    CellParser,
    ConstantParser,
    CsvFormat,
    CsvRow,
    CsvTransactionParser,
    ExtractDateParser,
)


VISA_RE = re.compile(r"V(?P<number>\d{6})　?(?P<description>.*)$")
VISA_SAGAKU_RE = re.compile(r"V(?P<description>ｻｶﾞｸ)(?P<number>\d{6})$")


def try_visa(row: CsvRow, return_number: bool) -> str:
    """Try extracting a Visa verification number and/or description."""
    description = row["お取り扱い内容"]
    m1 = VISA_RE.match(description)
    m2 = VISA_SAGAKU_RE.match(description)
    if m1:
        if return_number:
            return m1.group("number")
        else:
            return m1.group("description")
    elif m2:
        if return_number:
            return m2.group("number")
        else:
            return m2.group("description")
    else:
        if return_number:
            return ""
        else:
            return description


smbc_parser = CsvTransactionParser(
    date=ExtractDateParser("年月日", "%Y/%m/%d"),
    withdrawal=CellParser(lambda row: -Decimal(row["お引出し"] or 0)),
    deposit=CellParser(lambda row: Decimal(row["お預入れ"] or 0)),
    description=CellParser(lambda row: try_visa(row, return_number=False)),
    memo=ConstantParser(""),
    num=CellParser(lambda row: try_visa(row, return_number=True)),
)
smbc_new_parser = CsvTransactionParser(
    date=ExtractDateParser("年月日", "%Y/%m/%d"),
    withdrawal=CellParser(lambda row: Decimal(row["お引出し"] or 0)),
    deposit=CellParser(lambda row: Decimal(row["お預入れ"] or 0)),
    description=CellParser(lambda row: try_visa(row, return_number=False)),
    memo=ConstantParser(""),
    num=CellParser(lambda row: try_visa(row, return_number=True)),
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
