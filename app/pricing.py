import math
from flask import current_app

from app.price_rules import unit_price_try


def compute_line_total_v2(*, pages: int, copies: int, duplex: str, paper: str, color: str, paper_type: str, nup: int = 1) -> float:
    pages = max(1, int(pages or 1))
    copies = max(1, int(copies or 1))
    duplex = (duplex or "single")
    nup = max(1, int(nup or 1))
    cap = (nup * 2) if duplex == "double" else nup
    billable = math.ceil(pages / cap)
    unit = float(unit_price_try(paper_type, paper, color))
    return float(billable) * unit * float(copies)

def compute_shipping(subtotal_try: float) -> float:
    if not current_app.config["SHIPPING_ENABLED"]:
        return 0.0
    limit = float(current_app.config["FREE_SHIPPING_LIMIT"])
    fee = float(current_app.config["SHIPPING_FEE"])
    return 0.0 if float(subtotal_try) >= limit else fee
