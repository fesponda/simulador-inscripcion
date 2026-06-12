"""
app.py
Servidor Flask para el simulador de inscripción universitaria — modo presentación.

Los datos se cargan al arrancar desde config.py y los resultados se pre-calculan
una vez. Los colegas solo navegan los tabs sin posibilidad de cargar archivos.

Uso local:
    python app.py

Despliegue en Render/Railway:
    Ver README_DEPLOY.md
"""

import json
import os
import io
from collections import defaultdict
from flask import Flask, render_template, jsonify, Response

from simulador import parsear_csv_cursos, simular_n_veces, generar_csv_empalmes
from salones import calcular_disponibilidad
import config

app = Flask(__name__)
app.config["JSON_ENSURE_ASCII"] = False


# ─── Carga de datos al arrancar ───────────────────────────────────────────────

def cargar_datos():
    """Carga y pre-calcula todos los resultados al iniciar el servidor."""

    print(f"[inicio] Cargando alumnos desde {config.ARCHIVO_ALUMNOS}...")
    with open(config.ARCHIVO_ALUMNOS, encoding="utf-8") as f:
        alumnos = json.load(f)

    print(f"[inicio] Cargando programación desde {config.ARCHIVO_PROGRAMACION}...")
    with open(config.ARCHIVO_PROGRAMACION, encoding="utf-8-sig") as f:
        csv_txt = f.read()

    print(f"[inicio] Parseando cursos...")
    cursos = parsear_csv_cursos(csv_txt)

    print(f"[inicio] Ejecutando simulación ({config.N_CORRIDAS} corridas)...")
    resultado = simular_n_veces(alumnos, cursos, config.SEED, config.N_CORRIDAS)

    # Horarios de cursos para la tabla de empalmes
    resultado["horarios_cursos"] = {
        clave: [
            {"grupo": g.numero, "horario": g.horario_str,
             "salon": g.salon, "capacidad": g.capacidad}
            for g in grupos
        ]
        for clave, grupos in cursos.items()
    }

    # Planes de estudio (opcional)
    if os.path.exists(config.ARCHIVO_PLANES):
        print(f"[inicio] Cargando planes desde {config.ARCHIVO_PLANES}...")
        with open(config.ARCHIVO_PLANES, encoding="utf-8") as f:
            planes_raw = json.load(f)
        planes = parsear_planes(planes_raw)
        resultado["empalme_pares"] = analizar_planes(resultado["empalme_pares"], planes)
        print(f"[inicio] Planes cargados: {len(planes)} programa(s)")
    else:
        print(f"[inicio] Sin planes (no se encontró {config.ARCHIVO_PLANES})")
        for par in resultado["empalme_pares"]:
            par["mismo_semestre"] = []

    print(f"[inicio] Calculando disponibilidad de salones...")
    resultado["_salones"] = calcular_disponibilidad(csv_txt)

    print(f"[inicio] Calculando cursos multi-clave...")
    resultado["_multi_clave"] = calcular_cursos_multiples(csv_txt)

    resultado["_csv_txt"] = csv_txt  # para exportar CSV
    print(f"[inicio] ✓ Listo. {resultado['total_alumnos']} alumnos, "
          f"{len(resultado['empalme_pares'])} pares de empalme.")
    return resultado


# ─── Funciones auxiliares ─────────────────────────────────────────────────────

def parsear_planes(planes_raw: dict) -> dict:
    resultado = {}
    for programa, semestres in planes_raw.items():
        resultado[programa] = {}
        for semestre, claves in semestres.items():
            resultado[programa][semestre] = {c.strip() for c in claves if c.strip()}
    return resultado


def analizar_planes(pares: list, planes: dict) -> list:
    for par in pares:
        mat1, mat2 = par["mat1"], par["mat2"]
        coincidencias = []
        for programa, semestres in planes.items():
            for semestre, claves in semestres.items():
                if mat1 in claves and mat2 in claves:
                    coincidencias.append(f"{programa} sem.{semestre}")
        par["mismo_semestre"] = coincidencias
    return pares


def calcular_cursos_multiples(csv_texto: str) -> dict:
    import csv as csv_mod
    DIA_COLS = ['lu','ma','mi','ju','vi','sa']
    DIA_NOM  = ['Lu','Ma','Mi','Ju','Vi','Sá']

    reader = csv_mod.DictReader(io.StringIO(csv_texto.strip()))
    reader.fieldnames = [f.strip().lower() for f in (reader.fieldnames or [])]

    slots = defaultdict(set)
    slot_cap = {}
    horarios_clave = defaultdict(set)  # {clave: set de horarios}

    for row in reader:
        row = {k.strip().lower(): v.strip() for k,v in row.items()}
        salon = row.get('salon','').strip()
        if not salon: continue
        dias  = tuple(1 if row.get(d,'0') not in ('','0') else 0 for d in DIA_COLS)
        if not any(dias): continue
        ini   = row.get('hor_ini','')
        fin   = row.get('hor_fin','')
        clave = row.get('clave','').strip()
        grupo = row.get('grupo','').strip()
        if not clave: continue
        try:
            cap = int(float(row.get('capacidad', row.get('slbrdef_capacity', 0))))
        except (ValueError, TypeError):
            cap = 0
        key = (salon, dias, ini, fin)
        slots[key].add((clave, grupo))
        if key not in slot_cap:
            slot_cap[key] = cap
        dias_str = '-'.join(n for n,d in zip(DIA_NOM, dias) if d)
        horarios_clave[clave].add(f"{ini}–{fin} ({dias_str})")

    resultado = []
    for (salon, dias, ini, fin), cursos in slots.items():
        claves_unicas = {c for c,g in cursos}
        if len(claves_unicas) <= 1:
            continue
        dias_str = '-'.join(n for n,d in zip(DIA_NOM, dias) if d)
        resultado.append({
            'salon': salon, 'dias': dias_str,
            'hor_ini': ini, 'hor_fin': fin,
            'horario': f"{ini}–{fin} ({dias_str})",
            'capacidad': slot_cap[(salon, dias, ini, fin)],
            'claves': sorted(claves_unicas),
            'n_claves': len(claves_unicas),
            'horarios_por_clave': {
                c: sorted(horarios_clave[c]) for c in sorted(claves_unicas)
            },
        })

    def hm(t):
        try: h,m = t.split(':'); return int(h)*60+int(m)
        except: return 0

    resultado.sort(key=lambda x: (x['salon'], hm(x['hor_ini'])))
    return {'cursos_multiples': resultado, 'total': len(resultado)}


# ─── Pre-calcular al arrancar ─────────────────────────────────────────────────
DATOS = cargar_datos()


# ─── Rutas ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/resultado")
def resultado():
    # Devuelve todo excepto los campos internos (_csv_txt, _salones, _multi_clave)
    # y resultado_unico que es grande y no se usa en la UI
    excluir = {'resultado_unico'}
    publico = {k: v for k, v in DATOS.items()
               if not k.startswith("_") and k not in excluir}

    # Limpiar campos internos de cada par de empalme
    campos_internos = {'_todos_afectados', 'recomendacion', 'tipo_empalme',
                       'total_conflictos', 'traslape', 'lleno'}
    publico["empalme_pares"] = [
        {k: v for k, v in p.items() if k not in campos_internos}
        for p in publico["empalme_pares"]
    ]

    return jsonify(publico)


@app.route("/salones")
def salones():
    return jsonify(DATOS["_salones"])


@app.route("/multi_clave")
def multi_clave():
    return jsonify(DATOS["_multi_clave"])


@app.route("/exportar_csv")
def exportar_csv():
    contenido = generar_csv_empalmes(
        DATOS["empalme_pares"],
        DATOS.get("horarios_cursos", {})
    )
    contenido_bytes = "\ufeff" + contenido
    return Response(
        contenido_bytes,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=empalmes.csv"},
    )


@app.route("/exportar_multi_clave")
def exportar_multi_clave():
    import csv as csv_mod
    output = io.StringIO()
    writer = csv_mod.writer(output)
    writer.writerow(["Salón", "Horario compartido", "Capacidad", "N° Claves",
                     "Clave", "Todos los horarios de la clave"])
    for v in DATOS["_multi_clave"]["cursos_multiples"]:
        for clave in v["claves"]:
            horarios = " | ".join(v["horarios_por_clave"].get(clave, []))
            writer.writerow([
                v["salon"], v["horario"], v["capacidad"],
                v["n_claves"], clave, horarios,
            ])
    contenido = "\ufeff" + output.getvalue()
    return Response(
        contenido,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=multi_clave.csv"},
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
