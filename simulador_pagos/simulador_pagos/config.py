"""Configuración. Las credenciales de Mercado Pago se leen del entorno (.env)."""
import os

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "clave-de-desarrollo-cambiar")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "simulador.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Mercado Pago ---
    MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN", "")
    MP_CURRENCY = os.environ.get("MP_CURRENCY", "ARS")
    BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000")
    MP_AUTO_RETURN = os.environ.get("MP_AUTO_RETURN") == "1"
    MP_NOTIFICATION_URL = os.environ.get("MP_NOTIFICATION_URL", "")
