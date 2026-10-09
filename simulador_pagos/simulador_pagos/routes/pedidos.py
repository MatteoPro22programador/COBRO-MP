"""Creación y gestión de pedidos del usuario autenticado."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from extensions import db
from forms import AccionForm
from models import Producto, Pedido, ItemPedido

bp = Blueprint("pedidos", __name__, url_prefix="/pedidos")


def pedido_propio_o_404(id):
    """Devuelve el pedido si pertenece al usuario actual."""
    p = db.get_or_404(Pedido, id)
    if p.usuario_id != current_user.id:
        abort(403)
    return p


@bp.route("/")
@login_required
def lista():
    pedidos = Pedido.query.filter_by(usuario_id=current_user.id).order_by(Pedido.id.desc()).all()
    return render_template("pedidos/lista.html", pedidos=pedidos)


@bp.route("/nuevo", methods=["GET", "POST"])
@login_required
def nuevo():
    form = AccionForm()
    productos = Producto.query.filter(Producto.stock > 0).order_by(Producto.nombre).all()
    if form.validate_on_submit():
        pedido = Pedido(usuario_id=current_user.id)
        for prod in productos:
            try:
                cant = int(request.form.get(f"qty_{prod.id}", 0) or 0)
            except ValueError:
                cant = 0
            if cant <= 0:
                continue
            if cant > prod.stock:
                db.session.rollback()
                flash(f"Stock insuficiente de {prod.nombre} (quedan {prod.stock}).", "error")
                return render_template("pedidos/nuevo.html", productos=productos, form=form)
            prod.stock -= cant
            pedido.items.append(ItemPedido(producto_id=prod.id, cantidad=cant,
                                           precio_unitario=prod.precio))
        if not pedido.items:
            flash("Elige al menos un producto.", "error")
            return render_template("pedidos/nuevo.html", productos=productos, form=form)
        db.session.add(pedido)
        db.session.commit()
        flash("Pedido creado. Ya puedes pagarlo.", "ok")
        return redirect(url_for("pedidos.detalle", id=pedido.id))
    return render_template("pedidos/nuevo.html", productos=productos, form=form)


@bp.route("/<int:id>")
@login_required
def detalle(id):
    return render_template("pedidos/detalle.html", pedido=pedido_propio_o_404(id), accion=AccionForm())


@bp.route("/<int:id>/cancelar", methods=["POST"])
@login_required
def cancelar(id):
    pedido = pedido_propio_o_404(id)
    if pedido.estado != "pendiente":
        flash("Solo se pueden cancelar pedidos pendientes.", "error")
    else:
        for it in pedido.items:
            it.producto.stock += it.cantidad
        pedido.estado = "cancelado"
        db.session.commit()
        flash("Pedido cancelado y stock repuesto.", "ok")
    return redirect(url_for("pedidos.detalle", id=id))
