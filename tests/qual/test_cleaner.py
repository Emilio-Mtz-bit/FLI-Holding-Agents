from agents.qual.cleaner import clean


def test_collapses_multiple_spaces():
    assert clean("hola   mundo") == "hola mundo"


def test_collapses_multiple_newlines():
    result = clean("linea1\n\n\n\nlinea2")
    assert "\n\n\n" not in result


def test_strips_page_number_pattern():
    result = clean("contenido\n3\nmas contenido")
    assert "\n3\n" not in result


def test_strips_horizontal_rule():
    result = clean("texto\n---\nmas texto")
    assert "---" not in result


def test_normalizes_unicode():
    result = clean("café y señor")
    assert "café" in result


def test_lowercases_text():
    result = clean("GRUPO NAMA es Excelente")
    assert result == result.lower()


def test_empty_string_returns_empty():
    assert clean("") == ""
