"""
trig_entity_oracle.py

Requisitos:
  pip install oracledb requests

Descripción:
  - Convierte un input hexadecimal a entero.
  - Mapea al rango angular, calcula sin/cos/tan.
  - Inserta la entidad en Oracle.
  - Llama al procedimiento SP_CONFIRM_RECORD para marcar confirmación.
  - Opcional: muestra plantilla para enviar a IBM Watson (requiere credenciales).
"""

import math
import oracledb
import json
import requests
from typing import Optional, Dict, Any

# -----------------------
# configuracion ( edita )
#  -----------------------
ORACLE_CONFIG = {
    "user": "system",
    "password": "Tapiero123",
    "dsn": "localhost:1521/orcl"
}

# watson (opcional)
WATSON_CONFIG = {
    "apikey": "TU_WATSON_APIKEY",
    "url": "https://api.us-south.assistant.watson.cloud.ibm.com/instances/XXXX/v1/message?version=2021-06-14",
    "assistant_id": None 
}

# -----------------------
# Funciones utilitarias
# -----------------------
