"""CRUD de productos. Solo el creador puede editar o eliminar."""
from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from extensions import db
from forms import ProductoForm, AccionForm
from models import Producto, ItemPedido

bp = Blueprint("productos", __name__, url_prefix="/productos")


def _propio_o_404(id):
    p = db.get_or_404(Producto, id)
    if p.dueno_id != current_user.id:
        abort(403)
    return p


@bp.route("/")
@login_required
def lista():
    productos = Producto.query.order_by(Producto.nombre).all()
    return render_template("productos/lista.html", productos=productos, accion=AccionForm())


@bp.route("/nuevo", methods=["GET", "POST"])
@login_required
def nuevo():
    form = ProductoForm()
    if form.validate_on_submit():
        p = Producto(dueno_id=current_user.id)
        form.populate_obj(p)
        db.session.add(p)
        db.session.commit()
        flash("Producto agregado.", "ok")
        return redirect(url_for("productos.lista"))
    return render_template("productos/form.html", form=form, titulo="Nuevo producto")


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
@login_required
def editar(id):
    p = _propio_o_404(id)
    form = ProductoForm(obj=p)
    if form.validate_on_submit():
        form.populate_obj(p)
        db.session.commit()
        flash("Producto actualizado.", "ok")
        return redirect(url_for("productos.lista"))
    return render_template("productos/form.html", form=form, titulo="Editar producto")


@bp.route("/<int:id>/eliminar", methods=["POST"])
@login_required
def eliminar(id):
    p = _propio_o_404(id)
    if ItemPedido.query.filter_by(producto_id=p.id).first():
        flash("No se puede eliminar: el producto figura en pedidos. Pon su stock en 0.", "error")
    else:
        db.session.delete(p)
        db.session.commit()
        flash("Producto eliminado.", "ok")
    return redirect(url_for("productos.lista"))
