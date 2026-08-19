import pytest

from crew.main import normalizar_ticket


@pytest.mark.parametrize(
    ("raw_id", "esperado"),
    [
        ("DEV-5", ("DEV-5", "dev-5")),
        (" dev-5 ", ("DEV-5", "dev-5")),
        ("Dev123-42", ("DEV123-42", "dev123-42")),
    ],
)
def test_normalizar_ticket_acepta_identificadores_validos(raw_id, esperado):
    assert normalizar_ticket(raw_id) == esperado


@pytest.mark.parametrize(
    "raw_id",
    ["", "   ", "DEV", "DEV-", "-5", "DEV 5", "DEV-5-extra"],
)
def test_normalizar_ticket_rechaza_identificadores_invalidos(raw_id):
    with pytest.raises(ValueError):
        normalizar_ticket(raw_id)
