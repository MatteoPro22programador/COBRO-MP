"""Punto de entrada: fábrica de la aplicación Flask."""
from flask import Flask, redirect, url_for

from config import Config
from extensions import db, login_manager, csrf


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Inicia sesión para continuar."

    from routes.auth import bp as auth_bp
    from routes.productos import bp as productos_bp
    from routes.pedidos import bp as pedidos_bp
    from routes.pagos import bp as pagos_bp

    for bp in (auth_bp, productos_bp, pedidos_bp, pagos_bp):
        app.register_blueprint(bp)

    @app.route("/")
    def index():
        return redirect(url_for("productos.lista"))

    with app.app_context():
        db.create_all()
    return app


if __name__ == "__main__":
    create_app().run(debug=True)
