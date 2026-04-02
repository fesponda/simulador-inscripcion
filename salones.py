"""
salones.py
Disponibilidad de salones calculada con el enfoque de diccionario de slots.

Lógica:
  1. Por cada salón y DÍA INDIVIDUAL se inicializa el conjunto de todos los slots
     disponibles (7:00–22:00, cada 30 min).
  2. Se recorre la programación y se eliminan los slots ocupados por cada curso
     en cada uno de sus días activos.
  3. Para cada PATRÓN de días (Lu-Mi, Ma-Ju, Lu-Mi-Vi, etc.) la disponibilidad
     es la INTERSECCIÓN de los slots libres de cada día que lo compone.
     Así, un curso Lu-Mi-Vi que ocupa 8:00-9:29 bloquea correctamente ese
     horario en el patrón Lu-Mi aunque el curso sea "de tres días".
"""

import csv
import io
from collections import defaultdict

DIA_NOMBRES = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá"]
DIA_COLS    = ["lu", "ma", "mi", "ju", "vi", "sa"]
HORA_INI    = 7 * 60      # 420 min
HORA_FIN    = 22 * 60     # 1320 min
SLOT        = 30
MIN_LIBRE   = 60

TODOS_SLOTS = set(range(HORA_INI, HORA_FIN, SLOT))


def _hm(t: str):
    try:
        h, m = t.strip().split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return None


def _fmt(m: int) -> str:
    return f"{m // 60}:{m % 60:02d}"


def _patron_str(dias: tuple) -> str:
    return "-".join(n for n, d in zip(DIA_NOMBRES, dias) if d)


def _bloques_libres(slots_libres: set) -> list:
    """Encuentra bloques contiguos de >= MIN_LIBRE minutos en slots_libres."""
    bloques = []
    inicio = None
    prev = None
    for s in sorted(slots_libres):
        if inicio is None:
            inicio = prev = s
        elif s == prev + SLOT:
            prev = s
        else:
            dur = prev + SLOT - inicio
            if dur >= MIN_LIBRE:
                bloques.append({"ini": inicio, "fin": prev + SLOT,
                                 "ini_fmt": _fmt(inicio), "fin_fmt": _fmt(prev + SLOT),
                                 "duracion_min": dur})
            inicio = prev = s
    if inicio is not None:
        dur = prev + SLOT - inicio
        if dur >= MIN_LIBRE:
            bloques.append({"ini": inicio, "fin": prev + SLOT,
                             "ini_fmt": _fmt(inicio), "fin_fmt": _fmt(prev + SLOT),
                             "duracion_min": dur})
    return bloques


def calcular_disponibilidad(csv_texto: str) -> dict:
    reader = csv.DictReader(io.StringIO(csv_texto.strip()))
    reader.fieldnames = [f.strip().lower() for f in (reader.fieldnames or [])]

    # Paso 1: slots OCUPADOS por salón y DÍA INDIVIDUAL (0=Lu … 5=Sá)
    # ocupado[salon][dia_idx] = set de slots ocupados ese día
    ocupado: dict[str, dict[int, set]] = defaultdict(lambda: defaultdict(set))
    capacidad_salon: dict[str, int] = {}
    patrones_vistos: set[tuple] = set()

    for row in reader:
        row = {k.strip().lower(): v.strip() for k, v in row.items()}
        salon = row.get("salon", "").strip()
        if not salon:
            continue

        dias = tuple(
            1 if row.get(d, "0") not in ("", "0") else 0
            for d in DIA_COLS
        )
        if not any(dias):
            continue

        ini = _hm(row.get("hor_ini", ""))
        fin = _hm(row.get("hor_fin", ""))
        if ini is None or fin is None:
            continue

        try:
            cap = int(float(row.get("capacidad", row.get("slbrdef_capacity", 0))))
        except (ValueError, TypeError):
            cap = 0
        if cap > capacidad_salon.get(salon, 0):
            capacidad_salon[salon] = cap

        patrones_vistos.add(dias)

        # Marcar slots ocupados en cada día activo individualmente
        fin_slot = ((fin + SLOT - 1) // SLOT) * SLOT
        dias_activos = [i for i, d in enumerate(dias) if d]
        for dia_idx in dias_activos:
            slot = ini
            while slot < fin_slot:
                if HORA_INI <= slot < HORA_FIN:
                    ocupado[salon][dia_idx].add(slot)
                slot += SLOT

    # Paso 2: calcular disponibilidad por patrón
    # Para un patrón de días, la disponibilidad es la intersección de los
    # slots libres de cada día individual que lo compone.
    patrones_ordenados = sorted(
        patrones_vistos,
        key=lambda p: (-sum(p), _patron_str(p))
    )

    salones_resultado: dict[str, dict] = {}

    for salon in sorted(ocupado.keys()):
        patron_data: dict[str, dict] = {}

        for patron in patrones_ordenados:
            dias_activos = [i for i, d in enumerate(patron) if d]

            # Slots libres = intersección de (TODOS - ocupados_dia) para cada día
            libres = TODOS_SLOTS.copy()
            for dia_idx in dias_activos:
                ocupados_dia = ocupado[salon].get(dia_idx, set())
                libres -= ocupados_dia  # quitar lo que esté ocupado en cualquier día

            ocupados_patron = TODOS_SLOTS - libres

            patron_data[_patron_str(patron)] = {
                "slots_ocupados": sorted(ocupados_patron),
                "bloques_libres": _bloques_libres(libres),
            }

        salones_resultado[salon] = {
            "capacidad": capacidad_salon.get(salon, 0),
            "patrones": patron_data,
        }

    return {
        "patrones": [_patron_str(p) for p in patrones_ordenados],
        "salones": salones_resultado,
        "slots": [{"min": s, "fmt": _fmt(s)} for s in sorted(TODOS_SLOTS)],
        "hora_ini_fmt": _fmt(HORA_INI),
        "hora_fin_fmt": _fmt(HORA_FIN),
    }
