"""
test_simulador.py
Suite de pruebas para el simulador de inscripción universitaria.

Uso (sin dependencias externas):
    cd simulador_inscripcion
    python -m unittest tests.test_simulador -v

O para correr todas las pruebas:
    python -m unittest discover tests/ -v

Con pytest (si está instalado):
    python -m pytest tests/ -v
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulador import parsear_csv_cursos, simular_n_veces, simular_una_vez
from tests.datos_sinteticos import *


# ── Helpers ───────────────────────────────────────────────────────────────────

def simular(csv_txt, alumnos, n=50, seed=42):
    cursos = parsear_csv_cursos(csv_txt)
    return simular_n_veces(alumnos, cursos, seed, n)


def mat(res, clave):
    return res["resumen_materias"].get(clave, {
        "promedio_afectados": 0.0, "promedio_empalme": 0.0,
        "promedio_cupo_puro": 0.0, "pct_afectados": 0.0
    })


def par(res, mat1, mat2):
    key = tuple(sorted([mat1, mat2]))
    for p in res["empalme_pares"]:
        if tuple(sorted([p["mat1"], p["mat2"]])) == key:
            return p
    return None


# ── Empalmes ──────────────────────────────────────────────────────────────────

class TestEmpalmes(unittest.TestCase):

    def test_caso1_traslape_puro_detectado(self):
        """A y B mismo horario, 10 alumnos: par detectado con prom=10, razón=Traslape."""
        res = simular(CSV_TRASLAPE_PURO, ALUMNOS_TRASLAPE_PURO)
        p = par(res, "MAT-A", "MAT-B")
        self.assertIsNotNone(p, "El par MAT-A x MAT-B debe detectarse")
        self.assertEqual(p["promedio_afectados"], 10.0)
        self.assertEqual(p["pct_corridas_con_afectados"], 100.0)
        self.assertEqual(p["razon"], "Traslape")

    def test_caso1_ambas_materias_en_por_materia(self):
        """Empalme A×B: ambas deben aparecer en Por materia con prom_empalme=10."""
        res = simular(CSV_TRASLAPE_PURO, ALUMNOS_TRASLAPE_PURO)
        self.assertEqual(mat(res, "MAT-A")["promedio_empalme"], 10.0,
            "MAT-A (ganadora) también debe reportar empalme")
        self.assertEqual(mat(res, "MAT-B")["promedio_empalme"], 10.0)

    def test_caso2_cupo_exacto_sin_problema(self):
        """30 alumnos, A(H1,H2) B(H1) cap=30: todos caben, 0 afectados."""
        res = simular(CSV_CUPO_INSUF, ALUMNOS_CUPO_INSUF_30)
        self.assertEqual(len(res["empalme_pares"]), 0)
        self.assertEqual(mat(res, "MAT-B")["promedio_afectados"], 0.0)

    def test_caso3_cupo_insuficiente_exactamente_1(self):
        """31 alumnos, A(H1,H2) B(H1) cap=30: 1 sin B por cupo puro, 0 empalme."""
        res = simular(CSV_CUPO_INSUF, ALUMNOS_CUPO_INSUF_31)
        self.assertEqual(len(res["empalme_pares"]), 0,
            "No debe haber empalme de horario")
        self.assertEqual(mat(res, "MAT-B")["promedio_cupo_puro"], 1.0)
        self.assertEqual(mat(res, "MAT-B")["promedio_empalme"], 0.0)
        self.assertEqual(mat(res, "MAT-A")["promedio_afectados"], 0.0)

    def test_caso4_sin_empalme_grupos_cruzados(self):
        """A(H1,H2) B(H1,H2), 60 alumnos: todos inscriben, 0 empalmes."""
        res = simular(CSV_SIN_EMPALME, ALUMNOS_SIN_EMPALME)
        self.assertEqual(len(res["empalme_pares"]), 0)
        self.assertEqual(mat(res, "MAT-A")["promedio_afectados"], 0.0)
        self.assertEqual(mat(res, "MAT-B")["promedio_afectados"], 0.0)

    def test_caso5_tres_materias_encadenadas(self):
        """A(H1,H2) B(H1) C(H2): 20 A+B ok, 10 A+B+C con conflicto en B o C.
        MAT-A también aparece como afectada para los 10 alumnos E (no pudieron
        meter los 3, aunque A quedara inscrita — simetría del par)."""
        res = simular(CSV_TRES_MATERIAS, ALUMNOS_TRES_MATERIAS)
        total_afect = (mat(res, "MAT-B")["promedio_afectados"] +
                       mat(res, "MAT-C")["promedio_afectados"])
        self.assertGreaterEqual(total_afect, 10.0)
        # MAT-A aparece como afectada para los E (simetría del empalme)
        self.assertEqual(mat(res, "MAT-A")["promedio_afectados"], 10.0,
            "MAT-A debe tener 10 afectados (los E que no pudieron meter los 3)")

    def test_caso6_cupo_minimo_cap1(self):
        """A(H1) cap=1, B(H1) cap=30, 10 alumnos.
        - 9 sin A por cupo puro.
        - 1 que sí inscribió A no puede meter B por traslape → empalme=1 en A.
        - MAT-B tiene 1 afectado (el que inscribió A)."""
        res = simular(CSV_CUPO_MINIMO, ALUMNOS_CUPO_MINIMO)
        self.assertEqual(mat(res, "MAT-A")["promedio_cupo_puro"], 9.0)
        self.assertEqual(mat(res, "MAT-A")["promedio_empalme"], 1.0,
            "El alumno que inscribió A tiene empalme con B")
        self.assertEqual(mat(res, "MAT-B")["promedio_empalme"], 1.0)

    def test_caso7_cinco_mismo_horario_inscribe_una(self):
        """1 alumno, 5 materias mismo horario: inscribe 1, 4 traslape."""
        cursos = parsear_csv_cursos(CSV_CINCO_MISMO_HORARIO)
        res_una = simular_una_vez(ALUMNOS_CINCO, cursos, 42)
        ok = sum(1 for rm in res_una["X001"].values() if rm.status == "ok")
        fallos = sum(1 for rm in res_una["X001"].values() if rm.status != "ok")
        self.assertEqual(ok, 1, f"Debe inscribir 1, inscribió {ok}")
        self.assertEqual(fallos, 4)

    def test_caso8_cinco_con_alternativas_inscribe_todas(self):
        """1 alumno, 5 materias con 2 grupos c/u en horarios distintos: inscribe todas."""
        res = simular(CSV_CINCO_ALTERNATIVAS, ALUMNOS_CINCO_ALT)
        self.assertEqual(len(res["empalme_pares"]), 0)
        for c in ["MAT-A","MAT-B","MAT-C","MAT-D","MAT-E"]:
            self.assertEqual(mat(res, c)["promedio_afectados"], 0.0,
                f"{c} no debe tener afectados")

    def test_cupo_puro_no_genera_par_empalme(self):
        """Cupo puro (sin traslape irresolvible) no genera par en empalme_pares."""
        res = simular(CSV_CUPO_INSUF, ALUMNOS_CUPO_INSUF_31)
        self.assertEqual(len(res["empalme_pares"]), 0)

    def test_prom_empalme_mas_cupo_igual_total(self):
        """prom_empalme + prom_cupo_puro == promedio_afectados para cada materia."""
        res = simular(CSV_TRASLAPE_PURO, ALUMNOS_TRASLAPE_PURO)
        for clave, v in res["resumen_materias"].items():
            self.assertAlmostEqual(
                v["promedio_empalme"] + v["promedio_cupo_puro"],
                v["promedio_afectados"], places=1,
                msg=f"{clave}: empalme + cupo != total"
            )

    def test_razon_traslape_cupo_ambos(self):
        """Razón debe ser Traslape, Cupo o Ambos."""
        res = simular(CSV_TRASLAPE_PURO, ALUMNOS_TRASLAPE_PURO)
        for p in res["empalme_pares"]:
            self.assertIn(p["razon"], ["Traslape", "Cupo", "Ambos"])


# ── Parseo ────────────────────────────────────────────────────────────────────

class TestParseo(unittest.TestCase):

    def test_capacidad_float_string(self):
        """Capacidad '65.0' debe parsearse como 65."""
        csv_txt = HEADER + "\nMAT-A,1,0,1,0,1,0,0,8:00,9:29,SAL-A,65.0"
        cursos = parsear_csv_cursos(csv_txt)
        self.assertEqual(cursos["MAT-A"][0].capacidad, 65)

    def test_capacidad_default_si_invalida(self):
        """Capacidad inválida usa 30 como default."""
        csv_txt = HEADER + "\nMAT-A,1,0,1,0,1,0,0,8:00,9:29,SAL-A,abc"
        cursos = parsear_csv_cursos(csv_txt)
        self.assertEqual(cursos["MAT-A"][0].capacidad, 30)

    def test_clave_nan_ignorada(self):
        """Claves 'nan' en lista de alumnos se ignoran."""
        csv_txt = HEADER + "\nMAT-A,1,0,1,0,1,0,0,8:00,9:29,SAL-A,30"
        alumnos = {"A001": ["MAT-A", "nan", "NaN", " "]}
        cursos = parsear_csv_cursos(csv_txt)
        res = simular_n_veces(alumnos, cursos, 42, 5)
        self.assertNotIn("nan", res["resumen_materias"])
        self.assertNotIn("NaN", res["resumen_materias"])

    def test_capacidad_columna_vieja(self):
        """Acepta columna 'slbrdef_capacity' como fallback de 'capacidad'."""
        csv_viejo = (
            "clave,grupo,lu,ma,mi,ju,vi,sa,hor_ini,hor_fin,salon,slbrdef_capacity\n"
            "MAT-A,1,0,1,0,1,0,0,8:00,9:29,SAL-A,45.0"
        )
        cursos = parsear_csv_cursos(csv_viejo)
        self.assertEqual(cursos["MAT-A"][0].capacidad, 45)

    def test_no_ofertada_no_contamina_resumen(self):
        """Materia en lista de alumnos pero no en CSV: no aparece en Por materia."""
        csv_txt = HEADER + "\nMAT-A,1,0,1,0,1,0,0,8:00,9:29,SAL-A,30"
        alumnos = {"A001": ["MAT-A", "MAT-NOEXISTE"]}
        cursos = parsear_csv_cursos(csv_txt)
        res = simular_n_veces(alumnos, cursos, 42, 5)
        v = res["resumen_materias"].get("MAT-NOEXISTE", {})
        self.assertEqual(v.get("promedio_afectados", 0.0), 0.0)

    def test_no_ofertadas_en_resultado(self):
        """Materia no ofertada debe aparecer en la lista no_ofertadas."""
        csv_txt = HEADER + "\nMAT-A,1,0,1,0,1,0,0,8:00,9:29,SAL-A,30"
        alumnos = {"A001": ["MAT-A", "MAT-NOEXISTE"]}
        cursos = parsear_csv_cursos(csv_txt)
        res = simular_n_veces(alumnos, cursos, 42, 5)
        claves_no_ofert = [v["clave"] for v in res["no_ofertadas"]]
        self.assertIn("MAT-NOEXISTE", claves_no_ofert)


# ── Planes de estudio ─────────────────────────────────────────────────────────

class TestPlanes(unittest.TestCase):

    def setUp(self):
        from app import parsear_planes, analizar_planes
        self.parsear_planes = parsear_planes
        self.analizar_planes = analizar_planes

    def test_mismo_semestre_detectado(self):
        """ECO-001 y ECO-002 en mismo semestre de ECONOMIA se detectan."""
        planes = self.parsear_planes(PLANES_TEST)
        pares = [{"mat1": "ECO-001", "mat2": "ECO-002"}]
        result = self.analizar_planes(pares, planes)
        self.assertIn("ECONOMIA sem.3", result[0]["mismo_semestre"])

    def test_semestres_distintos_no_detectado(self):
        """Si están en semestres distintos del mismo programa, no coinciden."""
        planes = self.parsear_planes({"CONT": {"1": ["ECO-001"], "2": ["ECO-002"]}})
        pares = [{"mat1": "ECO-001", "mat2": "ECO-002"}]
        result = self.analizar_planes(pares, planes)
        self.assertEqual(result[0]["mismo_semestre"], [])

    def test_multiples_programas_todos_reportados(self):
        """Si coinciden en varios programas, todos se reportan."""
        planes = self.parsear_planes({
            "PROG-A": {"1": ["ECO-001", "ECO-002"]},
            "PROG-B": {"2": ["ECO-001", "ECO-002"]},
        })
        pares = [{"mat1": "ECO-001", "mat2": "ECO-002"}]
        result = self.analizar_planes(pares, planes)
        self.assertEqual(len(result[0]["mismo_semestre"]), 2)

    def test_claves_con_espacios_normalizadas(self):
        """Claves con espacios en el JSON de planes se normalizan."""
        planes = self.parsear_planes({"P": {"1": [" ECO-001 ", "ECO-002"]}})
        pares = [{"mat1": "ECO-001", "mat2": "ECO-002"}]
        result = self.analizar_planes(pares, planes)
        self.assertEqual(len(result[0]["mismo_semestre"]), 1)

    def test_planes_almacenados_como_sets(self):
        """Las claves del plan deben ser sets internamente (sin duplicados)."""
        planes = self.parsear_planes({"P": {"1": ["A", "B", "A"]}})
        self.assertIsInstance(planes["P"]["1"], set)
        self.assertEqual(len(planes["P"]["1"]), 2)


# ── Multi-clave ───────────────────────────────────────────────────────────────

class TestMultiClave(unittest.TestCase):

    def setUp(self):
        from app import calcular_cursos_multiples
        self.calcular = calcular_cursos_multiples

    def test_detecta_misma_aula_y_horario(self):
        """MAT-X y MAT-Y en misma aula y horario exacto se detectan."""
        res = self.calcular(CSV_MULTI_CLAVE)
        claves_detectadas = [tuple(sorted(v["claves"])) for v in res["cursos_multiples"]]
        self.assertIn(("MAT-X", "MAT-Y"), claves_detectadas)

    def test_no_detecta_misma_aula_hora_distinta(self):
        """Misma aula pero hora distinta NO es multi-clave."""
        res = self.calcular(CSV_MULTI_CLAVE)
        for v in res["cursos_multiples"]:
            if "MAT-Z" in v["claves"]:
                self.assertNotIn("MAT-X", v["claves"])

    def test_no_detecta_aula_distinta(self):
        """Mismo horario pero aula distinta NO es multi-clave."""
        res = self.calcular(CSV_MULTI_CLAVE)
        for v in res["cursos_multiples"]:
            if "MAT-W" in v["claves"]:
                self.assertNotIn("MAT-X", v["claves"])

    def test_total_correcto(self):
        """Solo 1 grupo multi-clave en CSV_MULTI_CLAVE."""
        res = self.calcular(CSV_MULTI_CLAVE)
        self.assertEqual(res["total"], 1)

    def test_deduplicacion_filas_repetidas(self):
        """Filas duplicadas en el CSV no generan falsos positivos."""
        csv_dup = (HEADER + "\n"
            "MAT-A,1,0,1,0,1,0,0,8:00,9:29,SAL-1,30\n"
            "MAT-A,1,0,1,0,1,0,0,8:00,9:29,SAL-1,30\n"
            "MAT-B,1,0,1,0,1,0,0,8:00,9:29,SAL-1,30\n"
        )
        res = self.calcular(csv_dup)
        self.assertEqual(res["total"], 1)
        self.assertEqual(res["cursos_multiples"][0]["n_claves"], 2)


# ── Disponibilidad de salones ─────────────────────────────────────────────────

class TestSalones(unittest.TestCase):

    def setUp(self):
        from salones import calcular_disponibilidad
        self.calcular = calcular_disponibilidad

    def test_slots_ocupados_ma_ju(self):
        """Curso Ma-Ju 8:00-9:29 ocupa slots 480, 510, 540 en patrón Ma-Ju."""
        res = self.calcular(CSV_SALONES)
        slots = res["salones"]["SALA-101"]["patrones"]["Ma-Ju"]["slots_ocupados"]
        for s in [8*60, 8*60+30, 9*60]:
            self.assertIn(s, slots, f"Slot {s//60}:{s%60:02d} debe estar ocupado")

    def test_curso_lumivi_bloquea_lumi(self):
        """Slots ocupados por curso Lu-Mi-Vi deben estar también en Lu-Mi."""
        res = self.calcular(CSV_SALONES)
        slots_lumivi = set(res["salones"]["SALA-102"]["patrones"]["Lu-Mi-Vi"]["slots_ocupados"])
        slots_lumi   = set(res["salones"]["SALA-102"]["patrones"]["Lu-Mi"]["slots_ocupados"])
        self.assertTrue(slots_lumivi.issubset(slots_lumi),
            "Lu-Mi debe incluir slots de cursos Lu-Mi-Vi")

    def test_bloques_libres_minimo_60min(self):
        """Todos los bloques libres deben ser >= 60 minutos."""
        res = self.calcular(CSV_SALONES)
        for salon, v in res["salones"].items():
            for patron, pd in v["patrones"].items():
                for bl in pd["bloques_libres"]:
                    self.assertGreaterEqual(bl["duracion_min"], 60,
                        f"{salon} {patron}: bloque < 60min")

    def test_slots_dentro_rango_7_22(self):
        """Todos los slots reportados deben estar entre 7:00 y 22:00."""
        res = self.calcular(CSV_SALONES)
        for s in res["slots"]:
            self.assertGreaterEqual(s["min"], 7*60)
            self.assertLess(s["min"], 22*60)

    def test_salon_libre_en_patron_sin_cursos(self):
        """SALA-102 no tiene cursos Ma-Ju: debe tener slots_ocupados=[] en Ma-Ju."""
        res = self.calcular(CSV_SALONES)
        if "Ma-Ju" in res["salones"].get("SALA-102", {}).get("patrones", {}):
            slots_ocp = res["salones"]["SALA-102"]["patrones"]["Ma-Ju"]["slots_ocupados"]
            self.assertEqual(slots_ocp, [])


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 65)
    print("SUITE DE PRUEBAS — Simulador de Inscripción Universitaria")
    print("=" * 65)
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(__import__(__name__))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    total = result.testsRun
    fallos = len(result.failures) + len(result.errors)
    print(f"\n{'✓ TODOS LOS TESTS PASARON' if fallos == 0 else f'✗ {fallos} TESTS FALLARON'} ({total} total)")
