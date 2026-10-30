import json
import re
import time
import numpy as np
from pyodide.ffi import create_proxy
from pyscript import document

INICIO = time.time()

# ---------- Dados ----------
with open("dados.json", encoding="utf-8") as f:
    DADOS = json.load(f)
FRUTAS = DADOS["frutas"]
CRITERIOS = DADOS["criterios"]
MATRIZ = np.array([x["vetor"] for x in FRUTAS], dtype=float)  # embeddings