"""Test smbc module."""
from parse import (
    smbc,
)


def test_VISA_RE() -> None:
    """Test VISA_RE."""
    m1 = smbc.VISA_RE.match("V999999")
    assert m1
    assert m1.group("number") == "999999"
    assert m1.group("description") == ""
    m2 = smbc.VISA_RE.match("V999999　コンニチハ")
    assert m2
    assert m2.group("number") == "999999"
    assert m2.group("description") == "コンニチハ"
    m3 = smbc.VISA_RE.match("振込　ｺﾝﾆﾁﾊ")
    assert m3 is None


def test_VISA_SAGAKU_RE() -> None:
    """Test VISA_SAGAKU_RE."""
    m1 = smbc.VISA_SAGAKU_RE.fullmatch("Vｻｶﾞｸ999999")
    assert m1
    assert m1.group("number") == "999999"
    m2 = smbc.VISA_SAGAKU_RE.fullmatch("振込　ｺﾝﾆﾁﾊ")
    assert m2 is None


def test_try_visa() -> None:
    """Test try_visa."""
    row1 = {"お取り扱い内容": "V999999"}
    assert smbc.try_visa(row1, return_number=False) == ""
    assert smbc.try_visa(row1, return_number=True) == "999999"
    row2 = {"お取り扱い内容": "V999999　コンニチハ"}
    assert smbc.try_visa(row2, return_number=False) == "コンニチハ"
    assert smbc.try_visa(row2, return_number=True) == "999999"
    row3 = {"お取り扱い内容": "Vｻｶﾞｸ999999"}
    assert smbc.try_visa(row3, return_number=False) == "ｻｶﾞｸ"
    assert smbc.try_visa(row3, return_number=True) == "999999"
    row4 = {"お取り扱い内容": "カード振込　ｺﾝﾆﾁﾊ"}
    assert smbc.try_visa(row4, return_number=False) == "カード振込　ｺﾝﾆﾁﾊ"
    assert smbc.try_visa(row4, return_number=True) == ""
