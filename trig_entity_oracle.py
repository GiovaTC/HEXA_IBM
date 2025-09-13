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
def hex_to_int(hex_str: str) -> int:
    s = hex_str.strip().lower()
    if s.startswith("0x"):
        s = s[2:]
    if s == "":
        raise ValueError("Hex vacío")
    return int(s, 16)

def int_to_angle_deg(value: int, modulus: Optional[int] = 360) -> float:
    return (value % modulus)

def compute_trig(angle_deg: float) -> Dict[str, float]:
    rad = math.radians(angle_deg)
    sin_v = math.sin(rad)
    cos_v = math.cos(rad)
    try:
        tan_v = math.tan(rad)
    except Exception:
        tan_v = float('inf')
    return {"angle_rad": rad, "sin": sin_v, "cos": cos_v, "tan": tan_v} 

# -----------------------
# Operaciones Oracle
# -----------------------
def get_oracle_connection(cfg: Dict[str, str]):
    return oracledb.connect(user=cfg["user"], password=cfg["password"], dsn=cfg["dsn"])

def insert_trig_entity(conn, hex_input: str, int_val: int, angle_deg: float, trig: Dict[str, float])
    sql = """
    INSERT INTO TRIG_ENTITY (
        HEX_INPUT, INT_VALUE, ANGLE_DEG, ANGLE_RAD, SIN_VAL, COS_VAL, TAN_VAL
    ) VALUES (:hex_input, :int_val, :angle_deg, :angle_rad, :sin_val, :cos_val, :tan_val)
    RETURNING ID INTO: id_out
    """

    cur = conn.cursor()
    id_out = cur.var(int)
    cur.execute(sql, {
        "hex_input": hex_input,
        "int_val": int_val,
        "angle_deg": angle_deg,
        "angle_rad": trig["angle_rad"],
        "sin_val": trig["sin"],
        "cos_val": trig["cos"],
        "tan_val": trig["tan"],
        "id_out": id_out
    })
    conn.commit()
    generated_id = int(id_out.getvalue()[0])
    cur.close()
    return generated_id
