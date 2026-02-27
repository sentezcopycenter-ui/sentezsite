import os, uuid
from datetime import datetime
from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename

from pypdf import PdfReader

from app import db
from app.models import Order, OrderFile
import math
from app.pricing import compute_line_total_v2, compute_shipping

bp = Blueprint("orders", __name__)

def _uploads_dir() -> str:
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
    os.makedirs(base, exist_ok=True)
    return base

def _only_digits(s: str) -> str:
    return "".join(ch for ch in (s or "") if ch.isdigit())

def _generate_unique_order_code() -> str:
    """Generate a 6-digit numeric code that is not reused."""
    import secrets
    for _ in range(60):
        code = f"{secrets.randbelow(1_000_000):06d}"
        if not Order.query.filter_by(order_code=code).first():
            return code
    # fallback (extremely unlikely)
    return f"{int(datetime.utcnow().timestamp()) % 1_000_000:06d}"

@bp.post("/api/upload")
def upload():
    if "files" not in request.files:
        return jsonify({"ok": False, "error": "files field missing"}), 400
    files = request.files.getlist("files")
    out = []
    up_dir = _uploads_dir()
    for f in files:
        if not f or not f.filename:
            continue
        fn = secure_filename(f.filename)
        token = uuid.uuid4().hex[:16]
        stored = f"{token}__{fn}"
        path = os.path.join(up_dir, stored)
        f.save(path)
        pages = 1
        try:
            if fn.lower().endswith(".pdf"):
                reader = PdfReader(path)
                pages = len(reader.pages) or 1
        except Exception:
            pages = 1
        out.append({"filename": fn, "stored_name": stored, "size_bytes": os.path.getsize(path), "mime": f.mimetype, "pages": pages})
    return jsonify({"ok": True, "files": out})


@bp.get("/api/order/track")
def track_order():
    """Customer order tracking.

    New behavior:
    - order_code OR phone is enough.
    - If only phone is provided and multiple orders exist, return a list.
    - If both provided, we verify phone matches the order.
    """
    order_code = (request.args.get("order_code") or "").strip()
    phone = _only_digits(request.args.get("phone") or "")

    if not order_code and not phone:
        return jsonify({"ok": False, "error": "Sipariş kodu veya telefon gerekli."}), 400

    def _dto(o: Order):
        return {
            "order_code": o.order_code,
            "status": o.status,
            "subtotal_try": o.subtotal_try,
            "shipping_try": o.shipping_try,
            "grand_total_try": o.grand_total_try,
            "cargo_company": o.cargo_company,
            "tracking_no": o.tracking_no,
        }

    # Case 1: order code provided
    if order_code:
        o = Order.query.filter_by(order_code=order_code).first()
        if not o:
            return jsonify({"ok": False, "error": "Sipariş bulunamadı."}), 404

        if phone:
            if _only_digits(o.customer_phone or "")[-10:] != phone[-10:]:
                return jsonify({"ok": False, "error": "Sipariş bulunamadı."}), 404

        return jsonify({"ok": True, "order": _dto(o)})

    # Case 2: only phone provided -> list
    # We match by last 10 digits to tolerate +90 / 0 prefixes.
    key = phone[-10:]
    q = Order.query.all()
    matches = []
    for o in q:
        ph = _only_digits(o.customer_phone or "")
        if ph and ph[-10:] == key:
            matches.append(o)

    if not matches:
        return jsonify({"ok": False, "error": "Sipariş bulunamadı."}), 404

    # newest first
    matches.sort(key=lambda x: x.created_at or datetime.min, reverse=True)
    return jsonify({"ok": True, "orders": [_dto(o) for o in matches]})

@bp.post("/api/order/create")
def create_order():
    data = request.get_json(force=True, silent=True) or {}
    items = data.get("items") or []
    if not items:
        return jsonify({"ok": False, "error": "Sepet boş."}), 400

    customer = data.get("customer") or {}
    invoice = data.get("invoice") or {}

    order = Order(
        order_code=_generate_unique_order_code(),
        status="awaiting_receipt",
        customer_name=(customer.get("name") or None),
        customer_phone=(customer.get("phone") or None),
        note=(customer.get("note") or None),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.session.add(order)
    db.session.flush()

    subtotal = 0.0
    up_dir = _uploads_dir()

    for it in items:
        stored_name = it.get("stored_name")
        if not stored_name:
            continue
        path = os.path.join(up_dir, stored_name)
        if not os.path.isfile(path):
            return jsonify({"ok": False, "error": f"Dosya bulunamadı: {stored_name}"}), 400

        paper = it.get("paper") or "A4"
        color = it.get("color") or "bw"
        duplex = it.get("duplex") or "single"
        binding = it.get("binding") or "none"
        paper_type = it.get("paper_type") or "80_1hamur"
        pages = int(it.get("pages") or 1)
        copies = int(it.get("copies") or 1)
        nup = int(it.get("nup") or 1)

        nup = max(1, nup)
        cap = (nup * 2) if duplex == "double" else nup
        billable = math.ceil(max(1, pages) / cap)
        line_total = compute_line_total_v2(
            pages=pages,
            copies=copies,
            duplex=duplex,
            paper=paper,
            color=color,
            paper_type=paper_type,
            nup=nup,
        )
        subtotal += line_total

        db.session.add(OrderFile(
            order_id=order.id,
            filename=it.get("filename") or stored_name,
            storage_path=path,
            mime=it.get("mime"),
            size_bytes=os.path.getsize(path),
            paper=paper, color=color, duplex=duplex, quality="std", binding=binding,
            paper_type=paper_type, pages=pages,
            nup=nup,
            sheets=billable, copies=copies,
            line_total_try=line_total
        ))

    inv_req = bool(invoice.get("requested"))
    order.invoice_requested = inv_req
    if inv_req:
        inv_type = (invoice.get("type") or "individual").strip()
        order.invoice_type = inv_type if inv_type in ("individual", "corporate") else "individual"
        order.tc_no = _only_digits(invoice.get("tc_no"))[:11] or None
        order.tax_no = _only_digits(invoice.get("tax_no"))[:10] or None
        order.tax_office = (invoice.get("tax_office") or None)
        order.company_title = (invoice.get("company_title") or None)
        order.address_city = (invoice.get("city") or None)
        order.address_district = (invoice.get("district") or None)
        order.address_full = (invoice.get("address") or None)

    shipping = compute_shipping(subtotal)
    order.subtotal_try = float(subtotal)
    order.shipping_try = float(shipping)
    order.grand_total_try = float(subtotal + shipping)
    order.updated_at = datetime.utcnow()

    db.session.commit()

    return jsonify({
        "ok": True,
        "order": {
            "order_code": order.order_code,
            "status": order.status,
            "subtotal_try": order.subtotal_try,
            "shipping_try": order.shipping_try,
            "grand_total_try": order.grand_total_try
        }
    })

@bp.get("/api/file/<int:file_id>/download")
def download_file(file_id: int):
    f = OrderFile.query.get_or_404(file_id)
    return send_file(f.storage_path, as_attachment=True, download_name=f.filename)
