# Python_3D_Viewer

Visualizador y analizador de mallas 3D en formato OBJ. Carga un modelo,
calcula sus propiedades topológicas (vértices, caras, aristas, componentes
conectados, genus vía característica de Euler) y permite comparar tres
variantes de la malla en una sola ventana: original, suavizado laplaciano y
edge split.

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

```bash
python -m mesh_viewer [ruta/al/modelo.obj]
```

Si no se indica un archivo, se usa `OBJs/cup.obj` por defecto.

Controles en la ventana:

- Arrastrar (botón izquierdo) = rotar la cámara
- Rueda del mouse = zoom
- Radio buttons (o teclas `1`/`2`/`3`) = cambiar entre Original, Laplacian
  Smoothing y Edge Split

Cada variante se exporta automáticamente a `OBJsExport/` la primera vez que
se visualiza.

## Estructura

```text
mesh_viewer/
├── obj_io.py      # lectura/escritura de archivos .obj
├── topology.py    # aristas, componentes conectados, genus
├── mesh_ops.py    # suavizado laplaciano, edge split
├── viewer.py       # ventana única con PyVista
└── app.py           # orquestación / entry point
```
