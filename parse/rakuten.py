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
    ExtractParser,
)
from parse.helper import (
    abs_if_negative_else_0,
    at_least_0,
)


JCB_RE = re.compile(
    r"(?P<description>JCBデビット) "
    r"(?P<mode>[A|B])(?P<number>\d{7}) "
    r"(?P<reference>\d{16})$"
)


def 入出金(row: CsvRow) -> Decimal:
    """Extract withdrawal / deposit from Rakuten row."""
    return Decimal(row["入出金(円)"])


def ご利用金額(row: CsvRow) -> Decimal:
    """Extract withdrawal / deposit from Rakuten JCB row."""
    return Decimal(row["ご利用金額（円）"])


def try_jcb(row: CsvRow, return_number: bool) -> str:
    """Try extracting a JCB verification number and description."""
    description = row["入出金先内容"]
    m = JCB_RE.match(description)
    if m:
        if return_number:
            return m.group("number")
        else:
            description = m.group("description")
            mode = m.group("mode")
            reference = m.group("reference")
            return f"{description} {mode} {reference}"
    else:
        if return_number:
            return ""
        else:
            return description


def extract_conversion_info(row: CsvRow) -> str:
    """Condense currency converson info in a Rakuten JCB row."""
    region = row["使用地域"]
    if region == "国内":
        return "Domestic"
    elif region == "海外":
        return f"Local: {row['現地通貨額']} {row['通貨略称']}, Rate: {row['換算レート']}"
    else:
        raise ValueError(f"Unknown region: {region}")


rakuten_parser = CsvTransactionParser(
    date=ExtractDateParser("取引日", "%Y%m%d"),
    withdrawal=CellParser(lambda row: abs_if_negative_else_0(入出金(row))),
    deposit=CellParser(lambda row: at_least_0(入出金(row))),
    description=CellParser(lambda row: try_jcb(row, return_number=False)),
    memo=ConstantParser(""),
    num=CellParser(lambda row: try_jcb(row, return_number=True)),
)


rakuten_jcb_parser = CsvTransactionParser(
    date=ExtractDateParser("ご利用日", "%Y%m%d"),
    withdrawal=CellParser(lambda row: at_least_0(ご利用金額(row))),
    deposit=CellParser(lambda row: abs_if_negative_else_0(ご利用金額(row))),
    description=ExtractParser("ご利用先", str),
    memo=CellParser(extract_conversion_info),
    num=ExtractParser("承認番号", str),
)
convert_rakuten_v1 = CsvFormat(
    parser=rakuten_parser,
    encoding="shift-jis",
    delimiter=",",
    skip=0,
    path="rakuten_v1",
)
convert_rakuten_jcb_v1 = CsvFormat(
    parser=rakuten_jcb_parser,
    encoding="shift-jis",
    delimiter=",",
    skip=0,
    path="rakuten_jcb_v1",
)
