from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

def _ensure_schema(app: Flask):
    """Lightweight schema migrations for sqlite deployments.

    We keep this minimal (ALTER TABLE / index) so existing shops don't need
    manual DB resets when we add a small column.
    """
    try:
        engine = db.get_engine(app)
        if engine.url.get_backend_name() != "sqlite":
            return
        with engine.begin() as conn:
            cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(orders)").fetchall()]
            if "order_code" not in cols:
                conn.exec_driver_sql("ALTER TABLE orders ADD COLUMN order_code VARCHAR(6)")
            # Unique index for public order code
            conn.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_order_code ON orders(order_code)")

            # price_rules: add per-size columns if missing (sqlite only)
            pr_cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(price_rules)").fetchall()]
            for col in ["bw_a5", "color_a5", "bw_a3", "color_a3"]:
                if col not in pr_cols:
                    conn.exec_driver_sql(f"ALTER TABLE price_rules ADD COLUMN {col} FLOAT DEFAULT 0.0")

            # order_files: add nup column if missing
            of_cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(order_files)").fetchall()]
            if "nup" not in of_cols:
                conn.exec_driver_sql("ALTER TABLE order_files ADD COLUMN nup INTEGER DEFAULT 1")
    except Exception:
        # If anything goes wrong, app should still boot; worst case the admin
        # can delete instance/app.db for a clean slate.
        return

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, static_folder="../static", template_folder="../templates", instance_relative_config=True)

    # Ensure instance dir exists (for sqlite)
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except Exception:
        pass

    app.config.from_object("app.config.Config")

    db.init_app(app)

    from app import models  # noqa: F401
    with app.app_context():
        db.create_all()
        _ensure_schema(app)

    from app.routes_public import bp as public_bp
    from app.routes_orders import bp as orders_bp
    from app.routes_admin import bp as admin_bp
    app.register_blueprint(public_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(admin_bp)

    return app
