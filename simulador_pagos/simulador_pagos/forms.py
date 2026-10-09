"""Formularios Flask-WTF."""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, DecimalField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange, ValidationError

from models import Usuario


class RegistroForm(FlaskForm):
    nombre = StringField("Nombre", validators=[DataRequired(), Length(max=80)])
    email = StringField("Correo electrónico", validators=[DataRequired(), Email()])
    password = PasswordField("Contraseña", validators=[DataRequired(), Length(min=6)])
    confirmar = PasswordField("Repetir contraseña", validators=[EqualTo("password", "Las contraseñas no coinciden.")])
    submit = SubmitField("Crear cuenta")

    def validate_email(self, field):
        if Usuario.query.filter_by(email=field.data.lower()).first():
            raise ValidationError("Ya existe una cuenta con ese correo.")


class LoginForm(FlaskForm):
    email = StringField("Correo electrónico", validators=[DataRequired(), Email()])
    password = PasswordField("Contraseña", validators=[DataRequired()])
    submit = SubmitField("Iniciar sesión")


class ProductoForm(FlaskForm):
    nombre = StringField("Nombre", validators=[DataRequired(), Length(max=120)])
    descripcion = TextAreaField("Descripción")
    precio = DecimalField("Precio", places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    stock = IntegerField("Stock", validators=[NumberRange(min=0)], default=0)
    submit = SubmitField("Guardar producto")


class AccionForm(FlaskForm):
    """Formulario vacío: solo aporta el token CSRF a botones POST."""
    submit = SubmitField("Confirmar")
