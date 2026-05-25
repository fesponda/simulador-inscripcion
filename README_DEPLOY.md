# Despliegue en Render

Los datos (selecciones, programación, planes) **nunca se suben a GitHub**.
Se cargan directamente en Render como "Secret Files", lo que los mantiene privados.

---

## 1. Subir el código a GitHub (sin datos)

```bash
cd simulador_inscripcion
git init
git add .
git commit -m "Simulador de inscripción"
```

Crea un repositorio en github.com (puede ser público o privado — los datos
no están en el código) y conéctalo:

```bash




```

---

## 2. Crear el servicio en Render

1. Ve a [dashboard.render.com](https://dashboard.render.com)
2. **New → Web Service**
3. Conecta tu repositorio de GitHub
4. Render detecta `render.yaml` automáticamente
5. **Antes de hacer Deploy**, ve al paso 3

---

## 3. Subir los archivos de datos como Secret Files

En el dashboard de Render, dentro de tu servicio:

1. Ve a **Environment → Secret Files**
2. Agrega cada archivo:

| Filename | Contenido |
|---|---|
| `selecciones.json` | Tu archivo de selecciones de alumnos |
| `programacion.csv` | Tu archivo de programación de cursos |
| `planes.json` | Tu archivo de planes de estudio (opcional) |

Render monta estos archivos en `/etc/secrets/` dentro del servidor.
El código los lee automáticamente desde ahí.

3. Haz clic en **Deploy** — en unos minutos la URL estará disponible.

---

## 4. Actualizar datos

Para actualizar los archivos de datos:
1. En Render → Environment → Secret Files
2. Edita o reemplaza el archivo
3. Haz clic en **Save Changes** — Render redespliega automáticamente

Para actualizar el código:
```bash
git add . && git commit -m "Actualización" && git push
```
Render redespliega automáticamente al detectar el push.

---

## Uso local (desarrollo)

Coloca los archivos en la carpeta `data/` del proyecto (esta carpeta
está en `.gitignore` y nunca se sube a GitHub):

```
simulador_inscripcion/
└── data/
    ├── selecciones.json
    ├── programacion.csv
    └── planes.json
```

Luego:
```bash
pip install -r requirements.txt
python app.py
# Abrir http://localhost:5000
```

---

## Notas

- El plan gratuito de Render puede tardar ~30 segundos en arrancar si
  el servicio estuvo inactivo (spin down after inactivity).
- Los colegas solo ven resultados — no pueden subir ni modificar datos.
- Para agregar autenticación (usuario/contraseña), consulta al desarrollador.
