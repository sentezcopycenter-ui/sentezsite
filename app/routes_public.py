from flask import Blueprint, jsonify, render_template, current_app
from app.price_rules import get_rule_map

bp = Blueprint("public", __name__)

@bp.get("/")
def index():
    return render_template("index.html")


@bp.get("/sepet")
def sepet_page():
    return render_template("sepet.html")


@bp.get("/mesafeli-satis")
def distance_sales():
    return render_template("legal_distance_sales.html")


@bp.get("/gizlilik")
def privacy_policy():
    return render_template("legal_privacy.html")


@bp.get("/teslimat-iade")
def delivery_return():
    return render_template("legal_delivery_return.html")

@bp.get("/api/public/prices")
def prices():
    return jsonify({
        "bw": current_app.config["PRICE_BW"],
        "color": current_app.config["PRICE_COLOR"],
        "pages_per_sheet": current_app.config["PAGES_PER_SHEET"],
        "currency": "TRY"
    })

@bp.get("/api/public/config")
def public_config():
    return jsonify({
        "shipping_enabled": current_app.config["SHIPPING_ENABLED"],
        "free_shipping_limit": current_app.config["FREE_SHIPPING_LIMIT"],
        "shipping_fee": current_app.config["SHIPPING_FEE"],
        "whatsapp_number": current_app.config["WHATSAPP_NUMBER"],
        "bank_recipient_name": current_app.config["BANK_RECIPIENT_NAME"],
        "bank_iban": current_app.config["BANK_IBAN"]
    })


@bp.get("/api/public/price_rules")
def public_price_rules():
    """Price rules editable from admin. Returns base A4 prices + labels."""
    return jsonify({
        "rules": get_rule_map(),
        "size_factor": {"A3": 2.0, "A4": 1.0, "A5": 0.75},
        "currency": "TRY"
    })
