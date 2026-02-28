"""Jednotný systém jednotek — interní reprezentace vždy v milimetrech.

Aplikace interně pracuje VÝHRADNĚ v milimetrech (mm).
Při importu/exportu/UI prezentaci se provádí konverze.

Podporované vstupní/výstupní jednotky: mm, cm, m, in (palce), ft (stopy).

Použití::

    from archpapercraft.core_geometry.units import to_mm, from_mm, convert

    # Import z metrů → interní mm
    wall_length_mm = to_mm(10.0, "m")   # → 10 000.0

    # Export z interních mm → cm
    wall_length_cm = from_mm(10_000.0, "cm")  # → 1 000.0

    # Přímá konverze
    value = convert(2.5, "m", "mm")  # → 2 500.0
"""

from __future__ import annotations

# ── Konverzní tabulka: 1 jednotka = kolik mm ───────────────────────────

UNIT_TO_MM: dict[str, float] = {
    "mm": 1.0,
    "cm": 10.0,
    "m": 1_000.0,
    "in": 25.4,
    "ft": 304.8,
}

SUPPORTED_UNITS = tuple(UNIT_TO_MM.keys())

# Interní jednotka je vždy mm
INTERNAL_UNIT = "mm"


def _validate_unit(unit: str) -> None:
    if unit not in UNIT_TO_MM:
        raise ValueError(
            f"Neznámá jednotka '{unit}'. Podporované: {', '.join(SUPPORTED_UNITS)}"
        )


def to_mm(value: float, source_unit: str) -> float:
    """Převede hodnotu z ``source_unit`` do interních milimetrů."""
    _validate_unit(source_unit)
    return value * UNIT_TO_MM[source_unit]


def from_mm(value_mm: float, target_unit: str) -> float:
    """Převede hodnotu z interních milimetrů do ``target_unit``."""
    _validate_unit(target_unit)
    return value_mm / UNIT_TO_MM[target_unit]


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """Převede hodnotu mezi dvěma libovolnými jednotkami."""
    return from_mm(to_mm(value, from_unit), to_unit)


def scale_factor_for_display(scale_str: str) -> float:
    """Parsuje textový zápis měřítka (např. ``'1:100'``) na číselný faktor.

    Příklady::

        '1:100' → 0.01
        '1:50'  → 0.02
        '1:1'   → 1.0
    """
    parts = scale_str.split(":")
    if len(parts) == 2:
        try:
            return float(parts[0]) / float(parts[1])
        except (ValueError, ZeroDivisionError):
            pass
    return 1.0


def model_to_paper_mm(
    model_value: float,
    model_unit: str,
    scale_str: str,
) -> float:
    """Převede rozměr modelu na milimetry na papíře.

    Pipeline: model_value [model_unit] → mm → × scale_factor → paper mm.

    Příklad: zeď 10 m v měřítku 1:100 → 10 000 mm × 0.01 = 100 mm na papíře.
    """
    mm_value = to_mm(model_value, model_unit)
    sf = scale_factor_for_display(scale_str)
    return mm_value * sf


def paper_mm_to_model(
    paper_mm: float,
    model_unit: str,
    scale_str: str,
) -> float:
    """Opačný směr: milimetry na papíře → rozměr modelu."""
    sf = scale_factor_for_display(scale_str)
    if sf == 0:
        return 0.0
    mm_value = paper_mm / sf
    return from_mm(mm_value, model_unit)
