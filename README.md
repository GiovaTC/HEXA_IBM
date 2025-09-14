# HEXA_IBM

<img width="2555" height="1077" alt="image" src="https://github.com/user-attachments/assets/d97e5c0f-5d08-49ad-bb18-541dca3e3540" />

## Descripción
Este proyecto en Python realiza los siguientes pasos:

1. Toma una cadena hexadecimal (por ejemplo `"0x1A3F"` o `"1A3F"`).  
2. La interpreta como entero y la mapea a un ángulo (grados y radianes).  
3. Calcula las funciones trigonométricas (sin, cos, tan).  
4. Inserta el registro en una tabla Oracle.  
5. Llama a un stored procedure en Oracle para confirmar el registro.  
6. (**Opcional**) Integra una verificación externa con IBM Watson (plantilla para llamar la API — necesitarás tu **apikey** y **url** de Watson).  

El proyecto usa **python-oracledb** para la conexión a Oracle.

---

## 1) DDL Oracle (crear tabla y SP)
Ejecuta en **SQL*Plus** o en tu herramienta de DBA:

```sql
-- Tabla para almacenar la "entidad trigonométrica"
CREATE TABLE TRIG_ENTITY (
  ID NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  HEX_INPUT VARCHAR2(100),
  INT_VALUE NUMBER,
  ANGLE_DEG NUMBER,
  ANGLE_RAD NUMBER,
  SIN_VAL NUMBER,
  COS_VAL NUMBER,
  TAN_VAL NUMBER,
  CREATED_AT TIMESTAMP DEFAULT SYSTIMESTAMP,
  CONFIRMED_BY_WATSON VARCHAR2(100),
  CONFIRMATION_STATUS VARCHAR2(20),
  WATSON_RESPONSE CLOB
);

-- Procedimiento almacenado para confirmar un registro.
CREATE OR REPLACE PROCEDURE SP_CONFIRM_RECORD(
    p_id IN NUMBER,
    p_status IN VARCHAR2,
    p_confirmed_by IN VARCHAR2,
    p_out_message OUT VARCHAR2
) AS
BEGIN
  UPDATE TRIG_ENTITY
    SET CONFIRMATION_STATUS = p_status,
        CONFIRMED_BY_WATSON = p_confirmed_by
    WHERE ID = p_id;
  IF SQL%ROWCOUNT = 0 THEN
    p_out_message := 'NO_RECORD';
  ELSE
    p_out_message := 'OK';
  END IF;
  COMMIT;
EXCEPTION
  WHEN OTHERS THEN
    p_out_message := 'ERROR: ' || SQLERRM;
    ROLLBACK;
END SP_CONFIRM_RECORD;
/

2) Script Python
Archivo: trig_entity_oracle.py

python
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
import requests   # solo si usarás Watson
from typing import Optional, Dict, Any

# -----------------------
# Configuración (edita)
# -----------------------
ORACLE_CONFIG = {
    "user": "TU_USUARIO",
    "password": "TU_PASSWORD",
    "dsn": "HOST:PORT/SERVICENAME"  # ejemplo: "localhost:1521/XEPDB1"
}

# Watson (opcional)
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

def insert_trig_entity(conn, hex_input: str, int_val: int, angle_deg: float, trig: Dict[str, float]) -> int:
    sql = """
    INSERT INTO TRIG_ENTITY (
        HEX_INPUT, INT_VALUE, ANGLE_DEG, ANGLE_RAD, SIN_VAL, COS_VAL, TAN_VAL
    ) VALUES (:hex_input, :int_val, :angle_deg, :angle_rad, :sin_val, :cos_val, :tan_val)
    RETURNING ID INTO :id_out
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
        raise RuntimeError("Watson config incompleta")

    headers = {"Content-Type": "application/json"}
    headers["X-IBM-Client-Id"] = watson_cfg["apikey"]

    resp = requests.post(watson_cfg["url"], headers=headers, data=json.dumps(payload), timeout=10)
    resp.raise_for_status()
    return resp.json()

# -----------------------
# Flujo principal
# -----------------------
def process_hex_and_store(hex_input: str, confirm_with_watson: bool = False) -> Dict[str, Any]:
    int_value = hex_to_int(hex_input)
    angle_deg = int_to_angle_deg(int_value)
    trig = compute_trig(angle_deg)

    conn = get_oracle_connection(ORACLE_CONFIG)
    try:
        record_id = insert_trig_entity(conn, hex_input, int_value, angle_deg, trig)
    except Exception:
        conn.close()
        raise

    confirmation_status = "PENDING"
    confirmer_name = None
    watson_resp_text = None

    if confirm_with_watson:
        payload = {
            "input": {
                "text": f"Confirm record: id={record_id}, hex={hex_input}, sin={trig['sin']:.6f}, cos={trig['cos']:.6f}"
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
                SET WATSON_RESPONSE = :watson_response
                WHERE ID = :id
            """, {"watson_response": watson_resp_text, "id": record_id})
            conn.commit()
            cur.close()
        except Exception as e:
            watson_resp_text = f"ERROR_WATSON: {str(e)}"
            confirmation_status = "PENDING"
            confirmer_name = "WATSON_ERROR"

    sp_msg = call_sp_confirm(conn, record_id, confirmation_status, confirmer_name or "SYSTEM")
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
# Ejemplo
# -----------------------
if __name__ == "__main__":
    sample_hex = "0x1A3F"
    try:
        result = process_hex_and_store(sample_hex, confirm_with_watson=False)
        print("Resultado:", json.dumps({
            "id": result["id"],
            "hex": result["hex_input"],
            "int": result["int_value"],
            "angle_deg": result["angle_deg"],
            "sin": result["trig"]["sin"],
            "cos": result["trig"]["cos"],
            "tan": result["trig"]["tan"],
            "sp_msg": result["sp_message"],
            "status": result["confirmation_status"]
        }, indent=2))
    except Exception as ex:
        print("Error en el flujo:", str(ex))

3) Notas y recomendaciones
Instalar librería:

bash
pip install oracledb requests
Modo thin: python-oracledb funciona sin cliente Oracle adicional si tu base acepta conexiones directas.
Stored Procedure: ajusta SP_CONFIRM_RECORD a la lógica de tu negocio.

IBM Watson:
Requiere apikey y url correctos.
El ejemplo usa un header simple, ajusta según la API real (Assistant v2, NLU, etc.).

Seguridad:
No dejes credenciales en texto plano.
Usa variables de entorno o un secret manager.
Precaución con tan: si cos ≈ 0, puede dar valores muy grandes.
