"""
datos_sinteticos.py
Datos de prueba reutilizables para todos los tests del simulador.
"""

HEADER = "clave,grupo,lu,ma,mi,ju,vi,sa,hor_ini,hor_fin,salon,capacidad"

# ── Horarios base ─────────────────────────────────────────────────────────────
H1  = "0,1,0,1,0,0,8:00,9:29"     # Ma-Ju  8:00-9:29
H2  = "0,1,0,1,0,0,10:00,11:29"   # Ma-Ju 10:00-11:29
H3  = "0,1,0,1,0,0,12:00,13:29"   # Ma-Ju 12:00-13:29
H4  = "0,1,0,1,0,0,14:00,15:29"   # Ma-Ju 14:00-15:29
H5  = "0,1,0,1,0,0,16:00,17:29"   # Ma-Ju 16:00-17:29
LM1 = "1,0,1,0,0,0,8:00,9:29"    # Lu-Mi  8:00-9:29
LM2 = "1,0,1,0,0,0,10:00,11:29"  # Lu-Mi 10:00-11:29
LMV = "1,0,1,0,1,0,8:00,9:29"    # Lu-Mi-Vi 8:00-9:29


def row(clave, grupo, horario, cap=30, salon=None):
    s = salon or f"SAL-{clave[-1]}"
    return f"{clave},{grupo},{horario},{s},{cap}"


def csv_from(*rows):
    return "\n".join([HEADER] + list(rows))


# ── Dataset 1: Traslape puro ──────────────────────────────────────────────────
# A y B en el mismo horario, sin alternativa
CSV_TRASLAPE_PURO = csv_from(
    row("MAT-A", 1, H1),
    row("MAT-B", 1, H1),
)
ALUMNOS_TRASLAPE_PURO = {f"A{i:03}": ["MAT-A", "MAT-B"] for i in range(10)}

# ── Dataset 2: Cupo exacto (30 alumnos, cap=30) ───────────────────────────────
CSV_CUPO_EXACTO = csv_from(
    row("MAT-A", 1, H1),
    row("MAT-B", 1, H1),
)
ALUMNOS_CUPO_EXACTO = {f"B{i:03}": ["MAT-A", "MAT-B"] for i in range(30)}

# ── Dataset 3: Cupo insuficiente (31 alumnos, cap=30, alternativa en H2) ──────
CSV_CUPO_INSUF = csv_from(
    row("MAT-A", 1, H1),
    row("MAT-A", 2, H2),
    row("MAT-B", 1, H1),
)
ALUMNOS_CUPO_INSUF_30 = {f"C{i:03}": ["MAT-A", "MAT-B"] for i in range(30)}
ALUMNOS_CUPO_INSUF_31 = {f"C{i:03}": ["MAT-A", "MAT-B"] for i in range(31)}

# ── Dataset 4: Sin empalme (grupos cruzados suficientes) ──────────────────────
CSV_SIN_EMPALME = csv_from(
    row("MAT-A", 1, H1), row("MAT-A", 2, H2),
    row("MAT-B", 1, H1), row("MAT-B", 2, H2),
)
ALUMNOS_SIN_EMPALME = {f"D{i:03}": ["MAT-A", "MAT-B"] for i in range(60)}

# ── Dataset 5: Tres materias encadenadas ──────────────────────────────────────
# A(H1,H2), B(H1), C(H2): B y C en horarios opuestos de A
CSV_TRES_MATERIAS = csv_from(
    row("MAT-A", 1, H1), row("MAT-A", 2, H2),
    row("MAT-B", 1, H1),
    row("MAT-C", 1, H2),
)
ALUMNOS_TRES_MAT_AB  = {f"E{i:03}": ["MAT-A", "MAT-B"] for i in range(20)}
ALUMNOS_TRES_MAT_ABC = {f"F{i:03}": ["MAT-A", "MAT-B", "MAT-C"] for i in range(10)}
ALUMNOS_TRES_MATERIAS = {**ALUMNOS_TRES_MAT_AB, **ALUMNOS_TRES_MAT_ABC}

# ── Dataset 6: Cupo mínimo (cap=1) ────────────────────────────────────────────
CSV_CUPO_MINIMO = csv_from(
    row("MAT-A", 1, H1, cap=1),
    row("MAT-B", 1, H1, cap=30),
)
ALUMNOS_CUPO_MINIMO = {f"G{i:03}": ["MAT-A", "MAT-B"] for i in range(10)}

# ── Dataset 7: Empalme por plan (ambas materias en mismo semestre) ─────────────
CSV_EMPALME_PLAN = csv_from(
    row("ECO-001", 1, H1),
    row("ECO-002", 1, H1),
)
ALUMNOS_EMPALME_PLAN = {f"H{i:03}": ["ECO-001", "ECO-002"] for i in range(8)}
PLANES_TEST = {
    "ECONOMIA": {"3": ["ECO-001", "ECO-002", "ECO-003"]},
    "CONTADURIA": {"4": ["ECO-001", "MAT-A"]},
}

# ── Dataset 8: Multi-clave (misma aula/hora, distintas claves) ────────────────
CSV_MULTI_CLAVE = csv_from(
    row("MAT-X", 1, H1, salon="AULA-1"),
    row("MAT-Y", 1, H1, salon="AULA-1"),  # misma aula/hora → cross-listed
    row("MAT-Z", 1, H2, salon="AULA-1"),  # misma aula, hora distinta → ok
    row("MAT-W", 1, H1, salon="AULA-2"),  # aula distinta → ok
)

# ── Dataset 9: Disponibilidad de salones ──────────────────────────────────────
# SALA-101: ocupado Ma-Ju 8:00-9:29 y 10:00-11:29 → libre 12:00-22:00 en Ma-Ju
# SALA-102: curso Lu-Mi-Vi 8:00-9:29 → bloquea 8:00-9:29 en Lu-Mi y Lu-Mi-Vi
CSV_SALONES = csv_from(
    row("MAT-A", 1, H1,  salon="SALA-101"),
    row("MAT-B", 1, H2,  salon="SALA-101"),
    row("MAT-C", 1, LMV, salon="SALA-102"),
    row("MAT-D", 1, LM2, salon="SALA-102"),
)

# ── Dataset 10: Cinco materias mismo horario (caso extremo backtracking) ───────
CSV_CINCO_MISMO_HORARIO = csv_from(
    row("MAT-A", 1, H1), row("MAT-B", 1, H1),
    row("MAT-C", 1, H1), row("MAT-D", 1, H1), row("MAT-E", 1, H1),
)
ALUMNOS_CINCO = {"X001": ["MAT-A", "MAT-B", "MAT-C", "MAT-D", "MAT-E"]}

# ── Dataset 11: Cinco materias con grupos alternativos ────────────────────────
CSV_CINCO_ALTERNATIVAS = csv_from(
    row("MAT-A", 1, H1), row("MAT-A", 2, H2),
    row("MAT-B", 1, H1), row("MAT-B", 2, H2),
    row("MAT-C", 1, H1), row("MAT-C", 2, H3),
    row("MAT-D", 1, H1), row("MAT-D", 2, H4),
    row("MAT-E", 1, H1), row("MAT-E", 2, H5),
)
ALUMNOS_CINCO_ALT = {"Y001": ["MAT-A", "MAT-B", "MAT-C", "MAT-D", "MAT-E"]}
