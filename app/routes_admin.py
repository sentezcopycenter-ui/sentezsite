from datetime import datetime
from functools import wraps
from flask import Blueprint, jsonify, request, render_template, session, redirect
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.models import Order, PriceRule, Setting
from app.price_rules import ensure_price_rules
from flask import current_app

bp = Blueprint("admin", __name__)

def _get_setting(key: str) -> str | None:
    s = Setting.query.filter_by(key=key).first()
    return s.value if s else None

def _set_setting(key: str, value: str | None):
    s = Setting.query.filter_by(key=key).first()
    if not s:
        s = Setting(key=key, value=value)
        db.session.add(s)
    else:
        s.value = value
    db.session.commit()

def ensure_admin_password():
    """Create default admin password hash on first boot."""
    h = _get_setting("admin_password_hash")
    if h:
        return
    default_pw = getattr(current_app.config, "ADMIN_PASSWORD", None) or current_app.config.get("ADMIN_PASSWORD") or "admin"
    _set_setting("admin_password_hash", generate_password_hash(default_pw))

def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        ensure_admin_password()
        if session.get("is_admin") is True:
            return fn(*args, **kwargs)
        # API endpoints return JSON
        if request.path.startswith("/api/"):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        return redirect("/admin/login?next=" + (request.full_path or request.path))
    return wrapper

@bp.get("/admin/login")
def admin_login_page():
    ensure_admin_password()
    nxt = request.args.get("next") or "/admin"
    return render_template("admin_login.html", next=nxt, error=None, msg=None)

@bp.post("/admin/login")
def admin_login_post():
    ensure_admin_password()
    pw = (request.form.get("password") or "").strip()
    nxt = (request.form.get("next") or "").strip() or "/admin"
    h = _get_setting("admin_password_hash") or ""
    if pw and h and check_password_hash(h, pw):
        session["is_admin"] = True
        return redirect(nxt)
    return render_template("admin_login.html", next=nxt, error="Şifre hatalı.", msg=None)

@bp.get("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect("/")

@bp.get("/admin/password")
@require_admin
def admin_password_page():
    return render_template("admin_password.html", error=None, msg=None)

@bp.post("/admin/password")
@require_admin
def admin_password_post():
    old_pw = (request.form.get("old_password") or "").strip()
    new_pw = (request.form.get("new_password") or "").strip()
    new_pw2 = (request.form.get("new_password2") or "").strip()

    if not new_pw or len(new_pw) < 4:
        return render_template("admin_password.html", error="Yeni şifre en az 4 karakter olmalı.", msg=None)
    if new_pw != new_pw2:
        return render_template("admin_password.html", error="Yeni şifreler eşleşmiyor.", msg=None)

    h = _get_setting("admin_password_hash") or ""
    if not check_password_hash(h, old_pw):
        return render_template("admin_password.html", error="Mevcut şifre yanlış.", msg=None)

    _set_setting("admin_password_hash", generate_password_hash(new_pw))
    return render_template("admin_password.html", error=None, msg="Şifre güncellendi ✅")

@bp.get("/admin")
@require_admin
def admin_page():
    return render_template("admin.html")


@bp.get("/admin/prices")
@require_admin
def admin_prices_page():
    # Make sure defaults exist
    ensure_price_rules()
    return render_template("admin_prices.html")


@bp.get("/api/admin/pricerules")
@require_admin
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
@require_admin
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
@require_admin
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
@require_admin
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
@require_admin
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
