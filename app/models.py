from datetime import datetime
from app import db

class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)

    # public order tracking code (6 digits)
    order_code = db.Column(db.String(6), nullable=True, unique=True)

    # workflow
    status = db.Column(db.String(32), nullable=False, default="awaiting_receipt")
    # awaiting_receipt -> ready_to_print -> printed -> shipped -> completed

    # customer
    customer_name = db.Column(db.String(120), nullable=True)
    customer_phone = db.Column(db.String(64), nullable=True)
    note = db.Column(db.Text, nullable=True)

    # totals (TRY)
    subtotal_try = db.Column(db.Float, nullable=False, default=0.0)
    shipping_try = db.Column(db.Float, nullable=False, default=0.0)
    grand_total_try = db.Column(db.Float, nullable=False, default=0.0)

    # invoice
    invoice_requested = db.Column(db.Boolean, nullable=False, default=False)
    invoice_type = db.Column(db.String(16), nullable=True)  # individual|corporate
    tc_no = db.Column(db.String(16), nullable=True)
    tax_no = db.Column(db.String(16), nullable=True)
    tax_office = db.Column(db.String(120), nullable=True)
    company_title = db.Column(db.String(200), nullable=True)

    address_city = db.Column(db.String(80), nullable=True)
    address_district = db.Column(db.String(80), nullable=True)
    address_full = db.Column(db.Text, nullable=True)

    # shipping tracking (manual)
    cargo_company = db.Column(db.String(80), nullable=True)
    tracking_no = db.Column(db.String(120), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    files = db.relationship("OrderFile", backref="order", cascade="all,delete-orphan")

class OrderFile(db.Model):
    __tablename__ = "order_files"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)

    filename = db.Column(db.String(255), nullable=False)
    storage_path = db.Column(db.String(512), nullable=False)
    mime = db.Column(db.String(120), nullable=True)
    size_bytes = db.Column(db.Integer, nullable=False, default=0)

    paper = db.Column(db.String(10), nullable=False, default="A4")
    color = db.Column(db.String(10), nullable=False, default="bw")
    duplex = db.Column(db.String(10), nullable=False, default="single")
    quality = db.Column(db.String(10), nullable=False, default="std")
    binding = db.Column(db.String(20), nullable=False, default="none")

    # pricing/product
    paper_type = db.Column(db.String(64), nullable=False, default="80_1hamur")
    pages = db.Column(db.Integer, nullable=False, default=1)

    # N-up (pages per sheet on each side): 1,2,4,6
    nup = db.Column(db.Integer, nullable=False, default=1)

    sheets = db.Column(db.Integer, nullable=False, default=1)
    copies = db.Column(db.Integer, nullable=False, default=1)
    line_total_try = db.Column(db.Float, nullable=False, default=0.0)


class PriceRule(db.Model):
    __tablename__ = "price_rules"
    id = db.Column(db.Integer, primary_key=True)

    key = db.Column(db.String(64), nullable=False, unique=True)  # paper_type
    label = db.Column(db.String(120), nullable=False)

    # Unit prices (TRY per billable page/yaprak) for each paper size
    bw_a4 = db.Column(db.Float, nullable=False, default=0.0)
    color_a4 = db.Column(db.Float, nullable=False, default=0.0)
    bw_a5 = db.Column(db.Float, nullable=False, default=0.0)
    color_a5 = db.Column(db.Float, nullable=False, default=0.0)
    bw_a3 = db.Column(db.Float, nullable=False, default=0.0)
    color_a3 = db.Column(db.Float, nullable=False, default=0.0)

    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Setting(db.Model):
    __tablename__ = "settings"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(120), nullable=False, unique=True)
    value = db.Column(db.Text, nullable=True)
