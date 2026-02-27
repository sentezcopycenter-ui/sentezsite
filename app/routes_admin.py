from datetime import datetime
from flask import Blueprint, jsonify, request, render_template
from app import db
from app.models import Order, PriceRule
from app.price_rules import ensure_price_rules

bp = Blueprint("admin", __name__)

@bp.get("/admin")
def admin_page():
    return render_template("admin.html")


@bp.get("/admin/prices")
def admin_prices_page():
    # Make sure defaults exist
    ensure_price_rules()
    return render_template("admin_prices.html")


@bp.get("/api/admin/pricerules")
def admin_get_pricerules():
    ensure_price_rules()
    rules = PriceRule.query.order_by(PriceRule.id.asc()).all()
    return jsonify({"ok": True, "rules": [
        {
            "id": r.id,
            "key": r.key,
            "label": r.label,
            "bw_a4": float(r.bw_a4),
            "color_a4": float(r.color_a4),
            "bw_a5": float(getattr(r, "bw_a5", 0.0) or 0.0),
            "color_a5": float(getattr(r, "color_a5", 0.0) or 0.0),
            "bw_a3": float(getattr(r, "bw_a3", 0.0) or 0.0),
            "color_a3": float(getattr(r, "color_a3", 0.0) or 0.0),
        }
        for r in rules
    ]})


@bp.post("/api/admin/pricerules")
def admin_update_pricerules():
    ensure_price_rules()
    data = request.get_json(force=True, silent=True) or {}
    rules_in = data.get("rules") or []
    by_key = {r.key: r for r in PriceRule.query.all()}
    for it in rules_in:
        key = (it.get("key") or "").strip()
        if not key or key not in by_key:
            continue
        r = by_key[key]
        if it.get("label") is not None:
            r.label = (it.get("label") or r.label)
        if it.get("bw_a4") is not None:
            try:
                r.bw_a4 = float(it.get("bw_a4"))
            except Exception:
                pass
        if it.get("color_a4") is not None:
            try:
                r.color_a4 = float(it.get("color_a4"))
            except Exception:
                pass
        for f in ["bw_a5", "color_a5", "bw_a3", "color_a3"]:
            if it.get(f) is not None:
                try:
                    setattr(r, f, float(it.get(f)))
                except Exception:
                    pass
        r.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True})

@bp.get("/api/admin/orders")
def admin_orders():
    status = request.args.get("status")
    q = Order.query
    if status:
        q = q.filter_by(status=status)
    orders = q.order_by(Order.id.desc()).limit(200).all()
    return jsonify({"ok": True, "orders": [{
        "id": o.id,
        "order_code": o.order_code,
        "status": o.status,
        "customer_name": o.customer_name,
        "customer_phone": o.customer_phone,
        "subtotal_try": o.subtotal_try,
        "shipping_try": o.shipping_try,
        "grand_total_try": o.grand_total_try,
        "invoice_requested": bool(o.invoice_requested),
        "cargo_company": o.cargo_company,
        "tracking_no": o.tracking_no,
        "created_at": o.created_at.isoformat() + "Z",
    } for o in orders]})

@bp.get("/api/admin/order/<int:order_id>")
def admin_order_detail(order_id: int):
    o = Order.query.get_or_404(order_id)
    return jsonify({"ok": True, "order": {
        "id": o.id,
        "order_code": o.order_code,
        "status": o.status,
        "customer_name": o.customer_name,
        "customer_phone": o.customer_phone,
        "note": o.note,
        "subtotal_try": o.subtotal_try,
        "shipping_try": o.shipping_try,
        "grand_total_try": o.grand_total_try,
        "invoice_requested": bool(o.invoice_requested),
        "invoice_type": o.invoice_type,
        "tc_no": o.tc_no,
        "tax_no": o.tax_no,
        "tax_office": o.tax_office,
        "company_title": o.company_title,
        "address_city": o.address_city,
        "address_district": o.address_district,
        "address_full": o.address_full,
        "cargo_company": o.cargo_company,
        "tracking_no": o.tracking_no,
        "created_at": o.created_at.isoformat() + "Z",
    }, "files": [{
        "id": f.id,
        "filename": f.filename,
        "paper": f.paper,
        "color": f.color,
        "duplex": f.duplex,
        "quality": f.quality,
        "binding": f.binding,
        "sheets": f.sheets,
        "copies": f.copies,
        "line_total_try": f.line_total_try
    } for f in o.files]})

@bp.post("/api/admin/order/<int:order_id>/update")
def admin_update(order_id: int):
    o = Order.query.get_or_404(order_id)
    data = request.get_json(force=True, silent=True) or {}

    st = (data.get("status") or "").strip()
    if st in ("awaiting_receipt","ready_to_print","printed","shipped","completed","cancelled"):
        o.status = st

    cargo_company = data.get("cargo_company")
    tracking_no = data.get("tracking_no")
    if cargo_company is not None:
        o.cargo_company = (cargo_company or None)
    if tracking_no is not None:
        o.tracking_no = (tracking_no or None)

    o.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True})
