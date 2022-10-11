"""Test rakuten module."""
from parse import (
    rakuten,
)


def test_JCB_RE() -> None:
    """Test VISA_RE."""
    m1 = rakuten.JCB_RE.fullmatch("JCBデビット A0000001 0000000000000001")
    assert m1
    assert m1.group("number") == "0000001"
    assert m1.group("description") == "JCBデビット"
    assert m1.group("mode") == "A"
    assert m1.group("reference") == "0000000000000001"
    m2 = rakuten.JCB_RE.fullmatch("JCBデビット B0000001 0000000000000001")
    assert m2
    assert m2.group("number") == "0000001"
    assert m2.group("description") == "JCBデビット"
    assert m2.group("mode") == "B"
    assert m2.group("reference") == "0000000000000001"
    m3 = rakuten.JCB_RE.fullmatch("ＫＡＩＳＨＡ")
    assert not m3


def test_try_jcb() -> None:
    """Test try_jcb."""
    row1 = {"入出金先内容": "JCBデビット B0000001 0000000000000001"}
    assert (
        rakuten.try_jcb(row1, return_number=False)
        == "JCBデビット B 0000000000000001"
    )
    assert rakuten.try_jcb(row1, return_number=True) == "0000001"
    row2 = {"入出金先内容": "ＫＡＩＳＨＡ"}
    assert rakuten.try_jcb(row2, return_number=False) == "ＫＡＩＳＨＡ"
    assert rakuten.try_jcb(row2, return_number=True) == ""
