from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from flask import current_app

from app import db
from app.models import PriceRule


DEFAULT_RULES = [
    {"key": "80_1hamur", "label": "80 gr 1. hamur", "factor": 1.0},
    {"key": "240_1hamur", "label": "240 gr 1. hamur", "factor": 1.35},
    {"key": "sticker_parlak", "label": "sticker parlak", "factor": 1.70},
    {"key": "sticker_selefonlu", "label": "sticker parlak selefonlu", "factor": 1.90},
    {"key": "vesikalik", "label": "vesikalık fotoğraf", "factor": 1.50},
    {"key": "brosur", "label": "broşür", "factor": 1.60},
    {"key": "sertifika_dokulu", "label": "sertifika dokulu", "factor": 1.80},
    {"key": "laminasyon", "label": "laminasyon", "factor": 2.00},
]


SIZE_FACTOR = {"A3": 2.0, "A4": 1.0, "A5": 0.75}


def _fill_sizes_from_a4(pr: PriceRule) -> None:
    """Backfill A5/A3 prices from A4 if missing (compat for older DBs)."""
    try:
        if float(getattr(pr, "bw_a5", 0.0) or 0.0) <= 0:
            pr.bw_a5 = round(float(pr.bw_a4) * float(SIZE_FACTOR["A5"]), 2)
        if float(getattr(pr, "color_a5", 0.0) or 0.0) <= 0:
            pr.color_a5 = round(float(pr.color_a4) * float(SIZE_FACTOR["A5"]), 2)
        if float(getattr(pr, "bw_a3", 0.0) or 0.0) <= 0:
            pr.bw_a3 = round(float(pr.bw_a4) * float(SIZE_FACTOR["A3"]), 2)
        if float(getattr(pr, "color_a3", 0.0) or 0.0) <= 0:
            pr.color_a3 = round(float(pr.color_a4) * float(SIZE_FACTOR["A3"]), 2)
    except Exception:
        return


def ensure_price_rules() -> List[PriceRule]:
    """Create default rules if none exist."""
    existing = PriceRule.query.order_by(PriceRule.id.asc()).all()
    if existing:
        # Backfill new columns for older DBs
        touched = False
        for pr in existing:
            before = (float(getattr(pr, 'bw_a5', 0) or 0), float(getattr(pr, 'bw_a3', 0) or 0))
            _fill_sizes_from_a4(pr)
            after = (float(getattr(pr, 'bw_a5', 0) or 0), float(getattr(pr, 'bw_a3', 0) or 0))
            if before != after:
                pr.updated_at = datetime.utcnow()
                touched = True
        if touched:
            db.session.commit()
        return existing

    base_bw = float(current_app.config.get("PRICE_BW", 0.5))
    base_color = float(current_app.config.get("PRICE_COLOR", 0.9))
    out: List[PriceRule] = []
    for r in DEFAULT_RULES:
        pr = PriceRule(
            key=r["key"],
            label=r["label"],
            bw_a4=round(base_bw * float(r["factor"]), 2),
            color_a4=round(base_color * float(r["factor"]), 2),
            bw_a5=round(base_bw * float(r["factor"]) * float(SIZE_FACTOR["A5"]), 2),
            color_a5=round(base_color * float(r["factor"]) * float(SIZE_FACTOR["A5"]), 2),
            bw_a3=round(base_bw * float(r["factor"]) * float(SIZE_FACTOR["A3"]), 2),
            color_a3=round(base_color * float(r["factor"]) * float(SIZE_FACTOR["A3"]), 2),
            updated_at=datetime.utcnow(),
        )
        db.session.add(pr)
        out.append(pr)
    db.session.commit()
    return out


def get_rule_map() -> Dict[str, Dict[str, float]]:
    """Return {paper_type: {label, bw_a4, color_a4, bw_a5, color_a5, bw_a3, color_a3}}"""
    rules = ensure_price_rules()
    return {
        r.key: {
            "label": r.label,
            "bw_a4": float(r.bw_a4),
            "color_a4": float(r.color_a4),
            "bw_a5": float(getattr(r, "bw_a5", 0.0) or 0.0),
            "color_a5": float(getattr(r, "color_a5", 0.0) or 0.0),
            "bw_a3": float(getattr(r, "bw_a3", 0.0) or 0.0),
            "color_a3": float(getattr(r, "color_a3", 0.0) or 0.0),
        }
        for r in rules
    }


def unit_price_try(paper_type: str, paper: str, color: str) -> float:
    """Compute TRY unit price for a billable page/yaprak."""
    rules = get_rule_map()
    pt = (paper_type or "80_1hamur").strip()
    paper = (paper or "A4").upper()
    color = (color or "bw").lower()
    r = rules.get(pt)

    def cfg_base() -> float:
        return float(current_app.config["PRICE_COLOR"] if color == "color" else current_app.config["PRICE_BW"])

    if not r:
        base_a4 = cfg_base()
        return base_a4 * float(SIZE_FACTOR.get(paper, 1.0))

    # Prefer explicit per-size columns
    if paper == "A5":
        v = float(r.get("color_a5") if color == "color" else r.get("bw_a5") or 0.0)
        if v > 0:
            return v
    if paper == "A3":
        v = float(r.get("color_a3") if color == "color" else r.get("bw_a3") or 0.0)
        if v > 0:
            return v

    # Default to A4
    base_a4 = float(r.get("color_a4") if color == "color" else r.get("bw_a4") or 0.0)
    if base_a4 <= 0:
        base_a4 = cfg_base()
    return base_a4 * float(SIZE_FACTOR.get(paper, 1.0))
