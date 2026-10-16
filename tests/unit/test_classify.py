import pytest

from zmg_cafes_etl.classify import classify_establishment_kind


@pytest.mark.parametrize(
    ("name", "razon_social", "expected"),
    [
        ("Café Ejemplo Centro", "Café Ejemplo Centro SA de CV", "cafe"),
        ("Coffee Shop Deluxe", None, "cafe"),
        ("Espresso Bar", None, "cafe"),
        ("Nevería y Paletería La Flor", None, "neveria"),
        ("La Michoacana Paletas y Nieves", None, "neveria"),
        (None, "Helados Don Pancho SA de CV", "neveria"),
        ("Refresquería La Esquina", None, "refresqueria"),
        (None, "Fuente de Sodas La Esquina SA de CV", "refresqueria"),
        ("Abarrotes Don Beto", "Abarrotes Don Beto SA de CV", "otro"),
        (None, None, "otro"),
        ("", "", "otro"),
        # Mixed keywords: neveria/refresqueria outrank "cafe" because those
        # are exactly the subtypes this heuristic exists to surface.
        ("Nevería y Cafetería La Reina", None, "neveria"),
        ("Refresquería y Café Las Palmas", None, "refresqueria"),
        # Blank Nombre falls back to Razon_social.
        ("", "Negocio Local Café Dos SA de CV", "cafe"),
    ],
)
def test_classify_establishment_kind(name, razon_social, expected) -> None:
    assert classify_establishment_kind(name, razon_social) == expected
