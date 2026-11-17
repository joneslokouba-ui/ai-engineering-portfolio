from src.naming import make_unique, normalize_name


def test_normalize_simple_header():
    assert normalize_name("Incident Number") == "incident_number"


def test_normalize_units_in_parentheses():
    assert normalize_name("Approximate Volume Released (m3)") == "approximate_volume_released_m3"


def test_normalize_strips_edges_and_symbols():
    assert normalize_name("  Year / Month -- ") == "year_month"


def test_normalize_empty_name_gets_placeholder():
    assert normalize_name("   ") == "column"
    assert normalize_name("***") == "column"


def test_make_unique_keeps_distinct_names():
    assert make_unique(["a", "b", "c"]) == ["a", "b", "c"]


def test_make_unique_suffixes_repeats_in_order():
    assert make_unique(["a", "b", "a", "a"]) == ["a", "b", "a_2", "a_3"]


def test_normalized_collisions_become_unique():
    names = [normalize_name(n) for n in ["Volume (m3)", "Volume m3"]]
    assert make_unique(names) == ["volume_m3", "volume_m3_2"]