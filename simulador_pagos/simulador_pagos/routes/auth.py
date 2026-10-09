"""Registro, inicio y cierre de sesión (Flask-Login)."""
from urllib.parse import urlparse

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db
from forms import RegistroForm, LoginForm
from models import Usuario

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/registro", methods=["GET", "POST"])
def registro():
    if current_user.is_authenticated:
        return redirect(url_for("productos.lista"))
    form = RegistroForm()
    if form.validate_on_submit():
        u = Usuario(nombre=form.nombre.data.strip(), email=form.email.data.lower())
        u.set_password(form.password.data)
        db.session.add(u)
        db.session.commit()
        flash("Cuenta creada. Ya puedes iniciar sesión.", "ok")
        return redirect(url_for("auth.login"))
    return render_template("auth/registro.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("productos.lista"))
    form = LoginForm()
    if form.validate_on_submit():
        u = Usuario.query.filter_by(email=form.email.data.lower()).first()
        if u and u.check_password(form.password.data):
            login_user(u)
            destino = request.args.get("next", "")
            if not destino or urlparse(destino).netloc:
                destino = url_for("productos.lista")
            return redirect(destino)
        flash("Correo o contraseña incorrectos.", "error")
    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada.", "ok")
    return redirect(url_for("auth.login"))
