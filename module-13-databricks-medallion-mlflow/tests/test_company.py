from src.company import COMPANY_ALIASES, clean_company


def test_ngtl_comma_variants_merge():
    a = clean_company("NGTL GP Ltd., as general partner on behalf of NGTL Limited Partnership")
    b = clean_company("NGTL GP Ltd., as general partner, on behalf of NGTL Limited Partnership")
    assert a == b


def test_westcoast_trading_name_merges_into_legal_name():
    assert (
        clean_company("Westcoast Energy Inc., carrying on business as Spectra Energy Transmission")
        == "Westcoast Energy Inc."
    )


def test_alliance_general_partner_wording_merges():
    name = ("Alliance Pipeline Ltd., as General Partner for and on behalf of "
            "Alliance Pipeline Limited Partnership")
    assert clean_company(name) == "Alliance Pipeline Ltd."


def test_minell_limited_and_ltd_merge():
    assert clean_company("Minell Pipeline Limited") == clean_company("Minell Pipeline Ltd.")


def test_transcanada_bc_system_label_merges():
    assert clean_company("TransCanada PipeLines Limited B.C. System") == "TransCanada PipeLines Limited"


def test_unmapped_name_is_unchanged():
    assert clean_company("Enbridge Pipelines Inc.") == "Enbridge Pipelines Inc."


def test_none_stays_none():
    assert clean_company(None) is None


def test_repeated_whitespace_is_collapsed():
    assert clean_company("  Enbridge   Pipelines Inc. ") == "Enbridge Pipelines Inc."


def test_distinct_legal_entities_are_not_merged():
    assert clean_company("Trans Mountain Pipeline Inc.") != clean_company("Trans Mountain Pipeline ULC")
    assert clean_company(
        "Westcoast Energy GP Inc. on behalf of Westcoast Energy Limited Partnership"
    ) != clean_company("Westcoast Energy Inc.")


def test_alias_targets_are_not_themselves_aliased():
    assert all(target not in COMPANY_ALIASES for target in COMPANY_ALIASES.values())