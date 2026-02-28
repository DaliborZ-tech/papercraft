"""Generátor sestavovacího návodu (build guide).

Vytváří textový a strukturovaný návod se:
- legendou (typy čar, značky),
- seznamem dílů (part list),
- tabulkou párování hran (edge-match table),
- doporučeným pořadím sestavení.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from archpapercraft.tabs_generator.markings import FoldType, PartMarkings


@dataclass
class EdgeMatch:
    """Pár hran k slepení."""
    match_id: int
    part_a: int
    part_b: int
    label: str = ""


@dataclass
class PartInfo:
    """Informace o jednom dílu pro návod."""
    part_id: int
    label: str = ""
    fold_count: int = 0
    mountain_folds: int = 0
    valley_folds: int = 0
    edge_match_count: int = 0
    area_mm2: float = 0.0


@dataclass
class BuildGuide:
    """Kompletní sestavovací návod."""

    project_name: str = "ArchPapercraft Studio"
    scale: str = "1:100"
    paper_grammage: int = 160
    parts: list[PartInfo] = field(default_factory=list)
    edge_matches: list[EdgeMatch] = field(default_factory=list)
    assembly_order: list[int] = field(default_factory=list)

    @property
    def legend(self) -> list[str]:
        """Legenda značení."""
        return [
            "── ── ──  Horský přehyb (mountain fold) — přehnout od sebe",
            "─·─·─·─   Údolní přehyb (valley fold) — přehnout k sobě",
            "━━━━━━━   Řezná hrana (cut edge) — vystřihnout",
            "▲         Šipka nahoru — orientace dílu",
            "+         Registrační křížek — zarovnání při tisku",
            "[A1]      Číslo dílu",
            "[●12]     Číslo páru hrany — slepit s protějškem",
        ]

    def to_text(self) -> str:
        """Vygeneruje textový návod."""
        lines: list[str] = []
        lines.append(f"╔══════════════════════════════════════════╗")
        lines.append(f"║  SESTAVOVACÍ NÁVOD                        ║")
        lines.append(f"║  {self.project_name:<40} ║")
        lines.append(f"╚══════════════════════════════════════════╝")
        lines.append("")
        lines.append(f"Měřítko: {self.scale}")
        lines.append(f"Gramáž papíru: {self.paper_grammage} g/m²")
        lines.append(f"Počet dílů: {len(self.parts)}")
        lines.append("")

        # Legenda
        lines.append("─── LEGENDA ────────────────────────────────")
        for item in self.legend:
            lines.append(f"  {item}")
        lines.append("")

        # Seznam dílů
        lines.append("─── SEZNAM DÍLŮ ────────────────────────────")
        for part in self.parts:
            label = part.label or f"Díl {part.part_id}"
            lines.append(
                f"  [{part.part_id:>3}] {label:<20} "
                f"přehybů: {part.fold_count} "
                f"(▲{part.mountain_folds} ▼{part.valley_folds}) "
                f"hran: {part.edge_match_count}"
            )
        lines.append("")

        # Tabulka párování hran
        if self.edge_matches:
            lines.append("─── PÁROVÁNÍ HRAN ──────────────────────────")
            lines.append(f"  {'ID':>4}  {'Díl A':>6}  {'Díl B':>6}  Popis")
            lines.append(f"  {'─'*4}  {'─'*6}  {'─'*6}  {'─'*20}")
            for em in self.edge_matches:
                lines.append(
                    f"  {em.match_id:>4}  {em.part_a:>6}  {em.part_b:>6}  {em.label}"
                )
            lines.append("")

        # Doporučené pořadí
        if self.assembly_order:
            lines.append("─── DOPORUČENÉ POŘADÍ SESTAVENÍ ────────────")
            for i, pid in enumerate(self.assembly_order, 1):
                part_label = ""
                for p in self.parts:
                    if p.part_id == pid:
                        part_label = p.label or f"Díl {pid}"
                        break
                lines.append(f"  {i}. {part_label}")
            lines.append("")

        lines.append("Tip: Nejprve vystřihněte všechny díly, poté")
        lines.append("     bigujte přehybové linie a nakonec lepte.")
        lines.append("")
        return "\n".join(lines)


def generate_build_guide(
    all_markings: list[PartMarkings],
    *,
    project_name: str = "ArchPapercraft Studio",
    scale: str = "1:100",
    paper_grammage: int = 160,
) -> BuildGuide:
    """Vytvoří sestavovací návod ze seznamu značení dílů.

    Parameters
    ----------
    all_markings : list[PartMarkings]
        Značení pro každý díl.
    project_name : str
        Název projektu.
    scale : str
        Měřítko modelu.
    paper_grammage : int
        Gramáž papíru.
    """
    guide = BuildGuide(
        project_name=project_name,
        scale=scale,
        paper_grammage=paper_grammage,
    )

    # Mapování match_id → díly
    match_to_parts: dict[int, list[int]] = {}

    for markings in all_markings:
        mtn = sum(1 for f in markings.fold_lines if f.fold_type == FoldType.MOUNTAIN)
        val = sum(1 for f in markings.fold_lines if f.fold_type == FoldType.VALLEY)

        part_info = PartInfo(
            part_id=markings.part_id,
            label=markings.part_label,
            fold_count=len(markings.fold_lines),
            mountain_folds=mtn,
            valley_folds=val,
            edge_match_count=len(markings.edge_labels),
        )
        guide.parts.append(part_info)

        for _edge, mid in markings.edge_labels.items():
            if mid == 0:
                continue
            match_to_parts.setdefault(mid, []).append(markings.part_id)

    # Vytvoř tabulku párování
    for mid, pids in sorted(match_to_parts.items()):
        unique_pids = sorted(set(pids))
        if len(unique_pids) >= 2:
            guide.edge_matches.append(EdgeMatch(
                match_id=mid,
                part_a=unique_pids[0],
                part_b=unique_pids[1],
            ))
        elif len(unique_pids) == 1:
            # Samo-párování (hrana uvnitř jednoho dílu)
            guide.edge_matches.append(EdgeMatch(
                match_id=mid,
                part_a=unique_pids[0],
                part_b=unique_pids[0],
                label="(vnitřní hrana)",
            ))

    # Jednoduché pořadí: nejprve velké díly, pak menší
    guide.assembly_order = [p.part_id for p in
                           sorted(guide.parts,
                                  key=lambda p: p.edge_match_count,
                                  reverse=True)]

    return guide
