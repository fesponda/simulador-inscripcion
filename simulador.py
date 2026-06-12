"""
simulador.py
Lógica de simulación de inscripción y detección de empalmes.
"""

import random
import csv
import io
from dataclasses import dataclass
from typing import Optional


# ─── Estructuras de datos ─────────────────────────────────────────────────────

@dataclass
class Grupo:
    clave: str
    numero: str
    dias: list
    hora_ini: str
    hora_fin: str
    salon: str
    capacidad: int
    inscritos: int = 0

    def __post_init__(self):
        self._ini_min = self._hm(self.hora_ini)
        self._fin_min = self._hm(self.hora_fin)

    @staticmethod
    def _hm(t):
        try:
            partes = t.strip().split(":")
            return int(partes[0]) * 60 + int(partes[1])
        except Exception:
            return 0

    def tiene_traslape(self, otro):
        dias_comun = any(a and b for a, b in zip(self.dias, otro.dias))
        if not dias_comun:
            return False
        return self._ini_min < otro._fin_min and otro._ini_min < self._fin_min

    @property
    def tiene_cupo(self):
        return self.inscritos < self.capacidad

    @property
    def horario_str(self):
        nombres = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá"]
        dias_str = "-".join(n for n, d in zip(nombres, self.dias) if d)
        return f"{self.hora_ini}–{self.hora_fin} ({dias_str})"

    def copia(self):
        return Grupo(
            clave=self.clave, numero=self.numero, dias=self.dias[:],
            hora_ini=self.hora_ini, hora_fin=self.hora_fin,
            salon=self.salon, capacidad=self.capacidad, inscritos=0,
        )


@dataclass
class ResultadoMateria:
    status: str
    grupo: Optional[str]
    motivo: str
    conflicto_con: Optional[str] = None
    grupo_conflicto: Optional[dict] = None


# ─── Parseo ───────────────────────────────────────────────────────────────────

def parsear_csv_cursos(contenido):
    reader = csv.DictReader(io.StringIO(contenido.strip()))
    reader.fieldnames = [f.strip().lower() for f in (reader.fieldnames or [])]
    cursos = {}
    for row in reader:
        row = {k.strip().lower(): v.strip() for k, v in row.items()}
        clave = row.get("clave", "").strip()
        if not clave:
            continue
        dias = [1 if row.get(d, "0") not in ("", "0") else 0
                for d in ["lu", "ma", "mi", "ju", "vi", "sa"]]
        try:
            cap = int(float(row.get("capacidad", row.get("slbrdef_capacity", 30))))
        except (ValueError, TypeError):
            cap = 30
        grupo = Grupo(
            clave=clave, numero=row.get("grupo", "1"), dias=dias,
            hora_ini=row.get("hor_ini", ""), hora_fin=row.get("hor_fin", ""),
            salon=row.get("salon", ""), capacidad=cap,
        )
        cursos.setdefault(clave, []).append(grupo)
    return cursos





# ─── Simulación ───────────────────────────────────────────────────────────────

def _mejor_asignacion(materias_claves, grupos_disponibles):
    """
    Backtracking completo: encuentra la asignación de grupos que maximiza
    el número de materias inscritas sin traslape entre ellas.

    Parámetros
    ----------
    materias_claves : list[str]
        Claves de las materias que el alumno quiere inscribir.
    grupos_disponibles : dict[str, list[Grupo]]
        Grupos con cupo disponible para cada clave (ya filtrados por cupo).

    Retorna
    -------
    dict[str, Grupo | None]
        {clave: Grupo asignado} para las materias que se pudieron inscribir,
        {clave: None} para las que no tuvieron solución.
    """
    n = len(materias_claves)
    mejor = [{}]          # mejor solución encontrada hasta ahora
    asignacion_actual = {}

    def backtrack(idx):
        if idx == n:
            # Solución completa: guardamos si es mejor que la actual
            if len(asignacion_actual) > len(mejor[0]):
                mejor[0] = dict(asignacion_actual)
            return
        # Poda: incluso inscribiendo todas las restantes no superamos la mejor
        restantes = n - idx
        if len(asignacion_actual) + restantes <= len(mejor[0]):
            return

        clave = materias_claves[idx]
        opciones = grupos_disponibles.get(clave, [])

        # Intentar cada grupo disponible con cupo
        for g in opciones:
            traslapa = any(g.tiene_traslape(asig) for asig in asignacion_actual.values())
            if not traslapa:
                asignacion_actual[clave] = g
                backtrack(idx + 1)
                del asignacion_actual[clave]
                # Optimización: si ya inscribimos todo, no seguimos
                if len(mejor[0]) == n:
                    return

        # También probar sin inscribir esta materia (puede liberar horario
        # para otras y resultar en más materias en total)
        backtrack(idx + 1)

    backtrack(0)
    return mejor[0]


def _diagnostico_fallo(clave_fallo, grupos_clave, grupos_con_cupo, todas_ofertadas, asignacion_optima):
    """
    Determina por qué una materia no pudo inscribirse en la asignación óptima.

    Estrategia:
    0. Si TODOS los grupos de la materia están llenos (sin cupo) → "lleno" directo.
    1. Verificar si hay traslape directo con alguna materia ya inscrita.
    2. Si no hay traslape directo → conflicto indirecto, forzar backtracking.

    Retorna (status, motivo, conflicto_con, grupo_conflicto)
    """
    # ── Paso 0: todos los grupos están llenos ────────────────────────────────
    grupos_disponibles = grupos_con_cupo.get(clave_fallo, [])
    if not grupos_disponibles:
        # No hay ningún grupo con cupo — cupo puro, sin importar horarios
        return ("lleno",
                "Todos los grupos están llenos",
                None, None)

    # ── Paso 1: traslape directo con la asignación óptima ────────────────────
    primer_conflicto_directo = None
    primer_gc_directo = None
    hay_libre_sin_cupo = False

    for g in grupos_clave:
        conflicto_directo = next(
            (asig for asig in asignacion_optima.values() if g.tiene_traslape(asig)),
            None
        )
        if conflicto_directo is None:
            if not g.tiene_cupo:
                hay_libre_sin_cupo = True
        else:
            if primer_conflicto_directo is None:
                primer_conflicto_directo = conflicto_directo.clave
                primer_gc_directo = {"g1": g.numero, "g2": conflicto_directo.numero}

    # Si todos los grupos (con cupo) tienen traslape directo → traslape clásico
    todos_tienen_traslape_directo = all(
        any(g.tiene_traslape(asig) for asig in asignacion_optima.values())
        for g in grupos_disponibles  # solo grupos con cupo
    )
    if todos_tienen_traslape_directo:
        return ("traslape",
                "Todos los grupos se traslapan con materias inscritas",
                primer_conflicto_directo, primer_gc_directo)

    # Si hay grupos con cupo libres de traslape pero todos están llenos → lleno
    if hay_libre_sin_cupo and not any(
        not any(g.tiene_traslape(asig) for asig in asignacion_optima.values())
        and g.tiene_cupo
        for g in grupos_clave
    ):
        return ("lleno",
                "Grupo sin traslape está lleno",
                primer_conflicto_directo, primer_gc_directo)

    # ── Paso 2: conflicto indirecto ───────────────────────────────────────────
    ofertadas_sin_fallo = [c for c in todas_ofertadas if c != clave_fallo]
    ofertadas_forzando = [clave_fallo] + ofertadas_sin_fallo
    asig_forzada = _mejor_asignacion(ofertadas_forzando, grupos_con_cupo)

    sacrificadas = [
        c for c in asignacion_optima
        if c not in asig_forzada and c != clave_fallo
    ]

    if sacrificadas:
        victima = sacrificadas[0]
        gc_indirecto = None
        for g_fallo in grupos_con_cupo.get(clave_fallo, []):
            for g_vic in grupos_con_cupo.get(victima, []):
                if g_fallo.tiene_traslape(g_vic):
                    gc_indirecto = {"g1": g_fallo.numero, "g2": g_vic.numero}
                    break
            if gc_indirecto:
                break

        return ("traslape",
                f"Conflicto indirecto: meterla obliga a sacrificar {victima}",
                victima, gc_indirecto)

    return ("lleno",
            "Sin cupo disponible en grupos compatibles",
            primer_conflicto_directo, primer_gc_directo)


def simular_una_vez(alumnos, cursos, seed):
    grupos = {c: [g.copia() for g in lista] for c, lista in cursos.items()}
    rng = random.Random(seed)
    orden = list(alumnos.keys())
    rng.shuffle(orden)
    resultado = {}

    for matricula in orden:
        resultado[matricula] = {}

        # Separar materias ofertadas de no ofertadas
        # Filtrar claves vacías o inválidas (ej. "nan" de exports de pandas)
        materias = [c.strip() for c in alumnos[matricula]
                    if c.strip() and c.strip().lower() != 'nan']
        no_ofertadas = [c for c in materias if not grupos.get(c)]
        ofertadas    = [c for c in materias if grupos.get(c)]

        for clave in no_ofertadas:
            resultado[matricula][clave] = ResultadoMateria(
                status="no_ofertada", grupo=None,
                motivo="Materia no ofertada en la programación")

        if not ofertadas:
            continue

        # Grupos con cupo disponible para el backtracking
        grupos_con_cupo = {
            c: [g for g in grupos[c] if g.tiene_cupo]
            for c in ofertadas
        }

        # Backtracking: encontrar la mejor combinación de grupos
        asignacion = _mejor_asignacion(ofertadas, grupos_con_cupo)

        # Registrar cupo consumido en los grupos asignados
        for clave, g in asignacion.items():
            g.inscritos += 1
            resultado[matricula][clave] = ResultadoMateria(
                status="ok", grupo=g.numero, motivo="")

        # Diagnosticar las materias que no quedaron en la asignación óptima
        for clave in ofertadas:
            if clave not in asignacion:
                status, motivo, conflicto_con, grupo_conflicto = _diagnostico_fallo(
                    clave_fallo=clave,
                    grupos_clave=grupos[clave],
                    grupos_con_cupo=grupos_con_cupo,
                    todas_ofertadas=ofertadas,
                    asignacion_optima=asignacion,
                )
                resultado[matricula][clave] = ResultadoMateria(
                    status=status, grupo=None, motivo=motivo,
                    conflicto_con=conflicto_con, grupo_conflicto=grupo_conflicto)

    return resultado


def simular_n_veces(alumnos, cursos, seed_base, n_corridas):
    """
    Ejecuta N corridas y acumula estadísticas.
    La clasificación de empalmes se basa exclusivamente en los resultados
    de la simulación con backtracking — no en análisis estático.

    Un par (A, B) es "empalme real" si en al menos una corrida algún alumno
    no pudo inscribir una de las dos materias por falta de cupo o traslape
    irresolvible. Si el backtracking siempre encuentra solución para todos
    los alumnos, el par no aparece como empalme.
    """
    stats_mat = {}
    stats_alumno = {}
    empalme_pares = {}
    afectados_mat_por_corrida = {}      # {clave: [set_corrida_0, ...]} — todos los fallos
    cupo_puro_por_corrida = {}          # {clave: [set_corrida_0, ...]} — lleno sin conflicto_con
    resultado_unico = None

    # Índice: alumnos que necesitan cada par de materias (para la columna informativa)
    # Filtrar claves vacías o inválidas (ej. "nan" de exports de pandas)
    alumnos_por_materia = {}
    for mat, materias in alumnos.items():
        for clave in materias:
            c = clave.strip()
            if not c or c.lower() == 'nan':
                continue
            alumnos_por_materia.setdefault(c, set()).add(mat)

    for r in range(n_corridas):
        res = simular_una_vez(alumnos, cursos, seed_base + r)
        if r == 0:
            resultado_unico = res

        for matricula, materias in res.items():
            if matricula not in stats_alumno:
                stats_alumno[matricula] = {"ok": 0, "empalme": 0}

            for clave, rm in materias.items():
                if clave not in stats_mat:
                    stats_mat[clave] = {
                        "ok": 0, "traslape": 0, "lleno": 0,
                        "no_ofertada": 0, "total": 0,
                        "alumnos_sin_inscribir": set(),
                    }
                stats_mat[clave][rm.status] += 1
                stats_mat[clave]["total"] += 1

                if rm.status == "ok":
                    stats_alumno[matricula]["ok"] += 1
                else:
                    stats_alumno[matricula]["empalme"] += 1
                    # no_ofertada es categoría aparte — no cuenta como empalme ni cupo
                    if rm.status != "no_ofertada":
                        # Registrar alumno único que falló esta materia en esta corrida
                        if clave not in afectados_mat_por_corrida:
                            afectados_mat_por_corrida[clave] = [set() for _ in range(n_corridas)]
                        afectados_mat_por_corrida[clave][r].add(matricula)
                        # Cupo puro: fallo por lleno (con o sin conflicto de horario)
                        if rm.status == "lleno":
                            if clave not in cupo_puro_por_corrida:
                                cupo_puro_por_corrida[clave] = [set() for _ in range(n_corridas)]
                            cupo_puro_por_corrida[clave][r].add(matricula)

                # Solo registrar el par si el alumno realmente no pudo inscribirse
                if rm.status in ("traslape", "lleno") and rm.conflicto_con:
                    par_key = "||".join(sorted([clave, rm.conflicto_con]))
                    if par_key not in empalme_pares:
                        empalme_pares[par_key] = {
                            "mat1": min(clave, rm.conflicto_con),
                            "mat2": max(clave, rm.conflicto_con),
                            "traslape": 0, "lleno": 0,
                            "afectados_por_corrida": [set() for _ in range(n_corridas)],
                            "detalle_grupos": [],
                        }
                    ep = empalme_pares[par_key]
                    ep[rm.status] += 1
                    ep["afectados_por_corrida"][r].add(matricula)
                    if rm.grupo_conflicto and len(ep["detalle_grupos"]) < 3:
                        desc = (f"{clave} gr.{rm.grupo_conflicto['g1']} ↔ "
                                f"{rm.conflicto_con} gr.{rm.grupo_conflicto['g2']}")
                        if desc not in ep["detalle_grupos"]:
                            ep["detalle_grupos"].append(desc)

                    # También registrar la materia "ganadora" del par como afectada
                    # — el alumno no pudo inscribir AMBAS, aunque una sí quedó inscrita
                    if rm.status == "traslape":
                        otra = rm.conflicto_con
                        if otra not in afectados_mat_por_corrida:
                            afectados_mat_por_corrida[otra] = [set() for _ in range(n_corridas)]
                        afectados_mat_por_corrida[otra][r].add(matricula)

    total_alumnos = len(alumnos)
    pares_lista = []

    for par_key, ep in empalme_pares.items():
        mat1, mat2   = ep["mat1"], ep["mat2"]
        traslape_sim = ep["traslape"]
        lleno_sim    = ep["lleno"]
        apc          = ep["afectados_por_corrida"]

        # Promedio de alumnos únicos afectados por corrida
        promedio_afectados = round(sum(len(s) for s in apc) / n_corridas, 1)
        # % de corridas con al menos un afectado
        corridas_con_afect = sum(1 for s in apc if s)
        pct_corridas = round(corridas_con_afect * 100 / n_corridas, 1)
        # Alumnos únicos totales (para ordenar y para resumen_materias)
        todos_afectados = set().union(*apc)

        # Alumnos que necesitan ambas (dato informativo)
        n_necesitan = len(
            alumnos_por_materia.get(mat1, set()) &
            alumnos_por_materia.get(mat2, set())
        )
        n_solicitan_mat1 = len(alumnos_por_materia.get(mat1, set()))
        n_solicitan_mat2 = len(alumnos_por_materia.get(mat2, set()))

        # Razón y recomendación basadas en lo que observó la simulación
        if traslape_sim > 0 and lleno_sim > 0:
            razon = "Ambos"
            recomendacion = "Abrir grupo en horario alternativo y/o aumentar cupo"
        elif traslape_sim > 0:
            razon = "Traslape"
            recomendacion = "Abrir grupo en horario alternativo"
        else:
            razon = "Cupo"
            recomendacion = "Aumentar cupo o abrir nuevo grupo"

        pares_lista.append({
            "mat1": mat1, "mat2": mat2,
            "tipo_empalme": "empalme_real",
            "traslape": traslape_sim,
            "lleno": lleno_sim,
            "total_conflictos": traslape_sim + lleno_sim,
            "alumnos_solicitan_mat1": n_solicitan_mat1,
            "alumnos_solicitan_mat2": n_solicitan_mat2,
            "alumnos_que_necesitan_ambas": n_necesitan,
            "promedio_afectados": promedio_afectados,
            "pct_corridas_con_afectados": pct_corridas,
            "razon": razon,
            "recomendacion": recomendacion,
            "detalle_grupos": ep["detalle_grupos"],
            "_todos_afectados": list(todos_afectados),  # para resumen_materias
        })

    # Ordenar por promedio afectados descendente
    pares_lista.sort(key=lambda x: (-x["promedio_afectados"], -x["pct_corridas_con_afectados"]))

    # ── Resumen por materia: promedio de alumnos únicos afectados por corrida ──
    # Usamos los resultados ya calculados en el loop principal (sin re-simular)
    resumen_materias = {}
    for clave in alumnos_por_materia:
        total_solicitan = len(alumnos_por_materia[clave])
        corridas_clave  = afectados_mat_por_corrida.get(clave, [])
        corridas_cupo   = cupo_puro_por_corrida.get(clave, [])

        promedio = round(
            sum(len(s) for s in corridas_clave) / n_corridas, 1
        ) if corridas_clave else 0.0

        promedio_cupo_puro = round(
            sum(len(s) for s in corridas_cupo) / n_corridas, 1
        ) if corridas_cupo else 0.0

        # Promedio afectados por empalme = total - cupo_puro
        promedio_empalme = round(promedio - promedio_cupo_puro, 1)

        pct = round(promedio * 100 / total_solicitan, 1) if total_solicitan else 0.0

        # Razón desde los pares registrados
        razones = []
        for ep in empalme_pares.values():
            if ep["mat1"] == clave or ep["mat2"] == clave:
                if ep["traslape"] > 0 and ep["lleno"] > 0:
                    razones.append("Traslape + cupo")
                elif ep["traslape"] > 0:
                    razones.append("Traslape")
                else:
                    razones.append("Cupo lleno")
        razon_empalme = max(set(razones), key=razones.count) if razones else None

        # Tipo de fallo dominante
        if promedio == 0:
            tipo_fallo = "ninguno"
        elif promedio_empalme > 0 and promedio_cupo_puro > 0:
            tipo_fallo = "mixto"
        elif promedio_cupo_puro > 0:
            tipo_fallo = "cupo_puro"
        else:
            tipo_fallo = "empalme"

        resumen_materias[clave] = {
            "alumnos_solicitan": total_solicitan,
            "promedio_afectados": promedio,
            "promedio_empalme": promedio_empalme,
            "promedio_cupo_puro": promedio_cupo_puro,
            "pct_afectados": pct,
            "razon_empalme": razon_empalme or "—",
            "tipo_fallo": tipo_fallo,
        }

    alumnos_con_empalme = len(set(
        mat for p in pares_lista for mat in p["_todos_afectados"]
    ))

    # ── Materias no ofertadas: solicitadas pero sin grupo en el CSV ──────────
    # Usar resultado_unico (primera corrida) — es determinístico para no_ofertada
    no_ofertadas = {}
    if resultado_unico:
        for mat, materias in resultado_unico.items():
            for clave, rm in materias.items():
                if rm.status == "no_ofertada":
                    if clave not in no_ofertadas:
                        no_ofertadas[clave] = {"alumnos_solicitan": 0}
                    no_ofertadas[clave]["alumnos_solicitan"] += 1

    # Ordenar por número de alumnos descendente
    no_ofertadas_lista = sorted(
        [{"clave": k, "alumnos_solicitan": v["alumnos_solicitan"]}
         for k, v in no_ofertadas.items()],
        key=lambda x: -x["alumnos_solicitan"]
    )

    res_serial = {}
    if resultado_unico:
        for mat, materias in resultado_unico.items():
            res_serial[mat] = {
                clave: {
                    "status": rm.status, "grupo": rm.grupo,
                    "motivo": rm.motivo, "conflicto_con": rm.conflicto_con,
                }
                for clave, rm in materias.items()
            }

    return {
        "empalme_pares": pares_lista,
        "n_corridas": n_corridas,
        "seed_base": seed_base,
        "total_alumnos": total_alumnos,
        "alumnos_con_empalme": alumnos_con_empalme,
        "resumen_materias": resumen_materias,
        "no_ofertadas": no_ofertadas_lista,
    }


# ─── Exportación CSV ──────────────────────────────────────────────────────────

def generar_csv_empalmes(pares, horarios_cursos):
    """Genera el CSV de empalmes como string."""
    output = io.StringIO()
    writer = csv.writer(output)

    def fmt_horarios(clave):
        grupos = horarios_cursos.get(clave, [])
        if not grupos:
            return "—"
        partes = [f"Gr{g['grupo']}:{g['horario']}" for g in grupos]
        return " | ".join(partes)

    writer.writerow([
        "Materia_A", "Horarios_A",
        "Materia_B", "Horarios_B",
        "Razon",
        "Alumnos_solicitan_A",
        "Alumnos_solicitan_B",
        "Alumnos_solicitan_ambas",
        "Promedio_afectados_por_corrida",
        "Pct_corridas_con_afectados",
        "Empalme_por_plan",
    ])

    for p in pares:
        writer.writerow([
            p["mat1"], fmt_horarios(p["mat1"]),
            p["mat2"], fmt_horarios(p["mat2"]),
            p["razon"],
            p["alumnos_solicitan_mat1"],
            p["alumnos_solicitan_mat2"],
            p["alumnos_que_necesitan_ambas"],
            p["promedio_afectados"],
            f"{p['pct_corridas_con_afectados']}%",
            "; ".join(p.get("mismo_semestre", [])) or "—",
        ])

    return output.getvalue()
