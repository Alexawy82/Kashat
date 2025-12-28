from kashat.detect.p2p import parse_p2p_descriptor


def test_parse_p2p_venmo():
    desc = "pmnt sent 1004 venmo *mai elm visa direct ny"
    info = parse_p2p_descriptor(desc, amount=-20.0)
    assert info
    assert info["provider"] == "venmo"
    assert info["direction"] == "to"
    assert info["counterparty"] == "mai elm"


def test_parse_p2p_cashapp():
    desc = "pmnt sent 1004 cash app*sean cordell oakland ca 40593652772939793939797"
    info = parse_p2p_descriptor(desc, amount=-45.0)
    assert info
    assert info["provider"] == "cashapp"
    assert info["direction"] == "to"
    assert info["counterparty"] == "sean cordell"


def test_parse_p2p_western_union():
    desc = "pmnt sent 0930 wuvisaaft 800-325-6000 co 24692165273109014555893"
    info = parse_p2p_descriptor(desc, amount=-508.99)
    assert info
    assert info["provider"] == "western_union"
    assert info["direction"] == "to"
    assert "counterparty" not in info


def test_parse_p2p_zelle_unified():
    desc = "zelle payment to rob keys conf# oo0097ll6"
    info = parse_p2p_descriptor(desc, amount=-280.0)
    assert info
    assert info["provider"] == "zelle"
    assert info["direction"] == "to"
    assert info["counterparty"] == "rob keys"
