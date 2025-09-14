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

def call_sp_confirm(conn, record_id: int, status: str, confirmer: str) -> str:
    cur = conn.cursor()
    out_msg = cur.var(str)
    cur.callproc("SP_CONFIRM_RECORD", [record_id, status, confirmer, out_msg])
    res = out_msg.getvalue()
    cur.close()
    return res

# -----------------------
# Watson (plantilla)
# -----------------------   
def send_to_watson_template(payload: Dict[str, Any], watson_cfg: Dict[str, str]) -> Dict[str, Any]:
    if not watson_cfg.get("apikey") or not watson_cfg.get("url"):
        raise RuntimeError("watson config incompleta")

    headers = {"Content-Type": "application/json"}
    headers["X-IBM-Client-Id"] = watson_cfg["apikey"]

    resp = requests.post(watson_cfg["url"], headers=headers, data= json.dumps(payload),  timeout= 10)
    resp.raise_for_status()
    return resp.json

# -----------------------
# Flujo principal
# -----------------------
def process_hex_and_store(hex_input: str, confirm_with_watson: bool = False) -> Dict[str, Any]:
    int_value = hex_to_int(hex_input)
    angle_deg = int_to_angle_deg(int_value)
    trig = compute_trig(angle_deg)

    conn = get_oracle_connection(ORACLE_CONFIG)
    try:
        record_id  = insert_trig_entity(conn, hex_input, int_value, angle_deg, trig)
    except Exception:
        conn.close()
        raise
    
    confirmation_status = "PENDING"
    confirmer_name = None
    watson_resp_text = None

    if confirm_with_watson:
        payload = {
            "input": {
                "text": f"Confirm record: id={record_id}, hex={hex_input}, sin=(trig['sin']:.6f), cos={trig['cos']:.6f}"   
            }
        }   
        try:
            watson_res = send_to_watson_template(payload, WATSON_CONFIG)
            watson_resp_text = json.dumps(watson_res)[:4000]
            confirmation_status = "CONFIRMED" if watson_res else "REJECTED"
            confirmer_name = "IBM_WATSON"
            cur = conn.cursor()
            cur.execute("""
                UPDATE TRIG_ENTITY
                SET WATSON RESPONSE = :watson_response 
                WHERE ID = :id
            """, {"watson_response": watson_resp_text, "id": record_id})
            conn.commit()
            cur.close()
        except Exception as e:
            watson_resp_text = f"ERROR_WATSON: {str(e)}"    
            confirmation_status = "PENDING"
            confirmer_name = "WATSON_ERROR"

    sp_msg = call_sp_confirm(conn,record_id, confirmation_status, confirmer_name or "SYSTEM")
    conn.close()

    return {
        "id": record_id,
        "hex_input": hex_input,
        "int_value": int_value,
        "angle_deg": angle_deg,
        "trig": trig,
        "watson_response": watson_resp_text,
        "sp_message": sp_msg,   
        "confirmation_status": confirmation_status
    } 

# -----------------------
# Ejemplo .
# -----------------------                
