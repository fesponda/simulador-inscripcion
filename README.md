# Simulador de Inscripción — Detección de Empalmes

Aplicación Flask para simular el proceso de inscripción universitaria y visualizar
conflictos de horario (traslapes) y grupos sin cupo.

## Estructura del proyecto

```
simulador_inscripcion/
├── app.py            # Servidor Flask (rutas)
├── simulador.py      # Lógica de simulación y exportación
├── requirements.txt
└── templates/
    └── index.html    # Interfaz web
```

## Instalación

```bash
# 1. Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Correr el servidor
python app.py
```

Abrir en el navegador: http://localhost:5000

## Formato de datos

### Alumnos (JSON)

```json
{
  "A001": ["MAT101", "FIS201", "QUI101"],
  "A002": ["MAT101", "ING301", "LIT201"]
}
```

### Programación de cursos (CSV)

| Columna            | Descripción                                       |
|--------------------|---------------------------------------------------|
| `clave`            | Código de la materia                              |
| `grupo`            | Número de grupo                                   |
| `lu` `ma` `mi` `ju` `vi` `sa` | 1 si hay clase ese día, 0 si no      |
| `hor_ini`          | Hora de inicio (HH:MM)                            |
| `hor_fin`          | Hora de fin (HH:MM)                               |
| `salon`            | Código del salón                                  |
| `capacidad`        | Capacidad del salón (cupo máximo)                 |

```csv
clave,grupo,lu,ma,mi,ju,vi,sa,hor_ini,hor_fin,salon,capacidad
MAT101,1,1,0,1,0,1,0,08:00,10:00,A101,25
MAT101,2,0,1,0,1,0,0,10:00,12:00,A102,25
FIS201,1,1,0,1,0,1,0,08:00,10:00,B301,20
```

## API

| Endpoint        | Método | Descripción                              |
|-----------------|--------|------------------------------------------|
| `/`             | GET    | Interfaz web                             |
| `/simular`      | POST   | Ejecuta la simulación, devuelve JSON     |
| `/exportar_csv` | POST   | Genera el CSV de empalmes para descarga  |

### POST /simular — body JSON

```json
{
  "alumnos":    { "A001": ["MAT101", "FIS201"] },
  "csv_cursos": "clave,grupo,...\nMAT101,1,...",
  "seed":       42,
  "n_corridas": 20
}
```

### POST /exportar_csv — body JSON

```json
{
  "empalme_pares": [...],
  "csv_cursos":    "clave,grupo,..."
}
```

## Lógica de simulación

1. Se barajan aleatoriamente las matrículas (orden de inscripción).
2. Cada alumno intenta inscribir todas sus materias usando **backtracking completo**: se prueban todas las combinaciones posibles de grupos para encontrar la asignación que maximiza el número de materias inscritas sin traslape y con cupo disponible.
3. Para cada materia que no pudo inscribirse, se diagnostica la causa:
   - **Traslape directo**: todos los grupos de la materia se traslapan con alguna materia ya inscrita en la asignación óptima.
   - **Conflicto indirecto**: hay grupos sin traslape directo, pero inscribir la materia obligaría a sacrificar otra — se hace un segundo backtracking forzando la materia y se identifica cuál sale.
   - **Cupo lleno**: hay grupo compatible en horario pero sin lugares disponibles.
4. Se registran los pares de materias que causaron el conflicto.
5. El proceso se repite N veces con semillas distintas (orden de inscripción diferente en cada corrida) para obtener estadísticas robustas sobre cupo.

Un par aparece como empalme en el reporte **únicamente si el backtracking no pudo inscribir a al menos un alumno en ambas materias** en al menos una corrida. Si siempre existe una combinación de grupos que resuelve el conflicto y hay cupo suficiente, el par no se reporta.

## Definición de métricas

### Tab Empalmes

| Columna | Definición |
|---|---|
| **Solicitan A / B** | Número total de alumnos que tienen esa materia en su lista de deseos, independientemente de si pudieron inscribirla. |
| **Solicitan ambas** | Alumnos que tienen *ambas* materias del par en su lista. |
| **Prom. afectados** | Promedio por corrida de alumnos únicos que no pudieron inscribir *alguna de las dos* materias del par debido a este conflicto. Es la unión de ambas direcciones: incluye tanto a quien falló la materia A por conflicto con B, como a quien falló B por conflicto con A. Puede ser mayor que el `Prom. no inscriben` de cada materia por separado. |
| **% corridas** | Porcentaje de corridas de simulación en que al menos un alumno no pudo inscribir alguna de las dos materias por este conflicto. Un valor alto indica que el problema es consistente y no depende del orden de inscripción. |
| **Razón** | Causa del conflicto observada en la simulación: `Traslape` (el backtracking no encontró combinación de grupos compatible), `Cupo` (hay grupos en horarios compatibles pero sin lugares disponibles), o `Ambos` (combinación de traslape y cupo). |
| **Empalme por plan** | Programas de estudio donde ambas materias aparecen en el mismo semestre del plan curricular. Indica que el plan supone que un alumno típico querrá llevar ambas materias simultáneamente, lo que hace el conflicto más urgente de atender independientemente de su causa. Esta columna es informativa y se calcula a partir del archivo de planes cargado opcionalmente — si no se carga, queda vacía (`—`). Un par puede aparecer aquí aunque existan grupos teóricamente compatibles en horario, si en la práctica la simulación determina que hay alumnos que no logran inscribir ambas. |

### Tab Por materia

Muestra todas las materias donde al menos un alumno no pudo inscribirse en al menos una corrida. Ordenada por Prom. total descendente.

| Columna | Definición |
|---|---|
| **Solicitan** | Número de alumnos que tienen esta materia en su lista de deseos. |
| **Prom. empalme** | Promedio por corrida de alumnos únicos que no pudieron inscribir esta materia por conflicto irresolvible de horario con otra materia. Solo aplica cuando el backtracking no encontró ninguna combinación de grupos compatible. |
| **Prom. cupo puro** | Promedio por corrida de alumnos únicos que no pudieron inscribir esta materia porque el grupo (o los grupos compatibles en horario) ya estaba lleno cuando les tocó inscribirse. Indica que el cupo total de la materia es insuficiente para la demanda, independientemente de los horarios. |
| **Prom. total** | `Prom. empalme + Prom. cupo puro`. Promedio total de alumnos por corrida que no pudieron inscribir esta materia por cualquier causa. |
| **% afectados** | `Prom. total / Solicitan × 100`. Porcentaje de los alumnos que solicitaron la materia que en promedio no pudieron inscribirla. Por ejemplo, si 24 alumnos en promedio no pueden inscribir una materia que solicitan 84, el % afectados es `24 / 84 × 100 = 28.6%`. |

Una materia puede tener valores en ambas columnas (`Prom. empalme` y `Prom. cupo puro`) si distintos alumnos fallan por causas distintas, o si el mismo alumno en distintas corridas falla por una u otra causa.

**Importante — simetría del empalme:** cuando dos materias A y B están en conflicto de horario, el simulador reporta *ambas* en este tab, no solo la que "perdió". Si un alumno no pudo inscribir A y B juntas, el backtracking elige una de las dos (digamos A) y deja fuera B. En ese caso B aparece con `Prom. empalme > 0` porque falló directamente, pero A también aparece con `Prom. empalme > 0` porque el alumno no pudo inscribir ambas — aunque A quedara inscrita en esa corrida. Esto refleja que el problema es del *par*, no de una sola materia.

## Limitación conocida: conflictos de tres o más materias


Cuando tres (o más) materias están involucradas en un conflicto encadenado — por ejemplo, `ECO-11122`, `ECO-15101` y `MAT-101` donde ninguna combinación de dos de ellas traslapa, pero las tres juntas no caben — el backtracking deja fuera una de las tres y registra el par correspondiente a esa decisión.

El problema es que cuál materia queda fuera depende del orden en que el backtracking las procesa, y ese orden puede variar. En la práctica, acumulando suficientes corridas, todos los pares involucrados en el conflicto eventualmente aparecen en el reporte. Sin embargo, el reporte no indica explícitamente que el problema es de tres materias — solo muestra pares.

**TODO (mejora futura):** detectar y reportar conflictos de tres o más materias como una unidad, mostrando el conjunto completo de materias que no pueden inscribirse simultáneamente en lugar de descomponerlo en pares. Esto requeriría guardar, para cada alumno y cada corrida, el conjunto completo de materias que el backtracking no pudo acomodar y asociarlas como un solo conflicto grupal.

