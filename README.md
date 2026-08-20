# Python_3D_Viewer

Visualizador y analizador de mallas 3D en formato OBJ. Carga un modelo,
calcula sus propiedades topológicas (vértices, caras, aristas, componentes
conectados, genus vía característica de Euler) y geométricas (área, volumen,
bounding box, calidad de triángulos, aristas non-manifold), y permite
comparar tres variantes de la malla en una sola ventana: original, suavizado
laplaciano y edge split.

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
- Checkboxes (Vértices / Aristas / Superficie) = mostrar u ocultar cada capa
- Slider "Color" = color sólido de la superficie, o "Por Componente" para
  colorear cada componente conectado con un color distinto
- Checkboxes de reparación (Soldar vértices / Unificar orientación / Rellenar
  huecos) = aplican sobre la variante actual, en ese orden fijo, y se
  recalculan al vuelo (no mutan los archivos ni el caché de la variante).
  "Rellenar huecos" triangula cada hueco por ear clipping, siguiendo la
  forma real del contorno (no un abanico desde un centroide), y nunca crea
  una cara que duplique una arista que ya tenga 2 dueños.
- Slider "Decimar" = reduce triángulos preservando la forma (quadric
  decimation de VTK), 0 = sin reducir, 0.9 = ~90% menos triángulos
- Slider "Subdividir (Loop)" = suaviza y agrega detalle (0 a 3 niveles,
  cada nivel ~4x los triángulos)

Cada variante se exporta automáticamente a `OBJsExport/` la primera vez que
se visualiza. Los arreglos de reparación, decimación y subdivisión son solo
de vista — no se exportan.

El overlay también muestra medidas geométricas de la malla actualmente
mostrada (con reparaciones/decimación/subdivisión ya aplicadas): área,
volumen (solo si la malla es watertight, es decir "Huecos: 0"), bounding
box, calidad promedio de triángulo con un mini-histograma en texto, y
cantidad de aristas non-manifold (compartidas por 3+ caras).

Nota: la subdivisión Loop puede fallar en mallas con aristas non-manifold
(ver el stat "Non-manifold" del overlay) — en ese caso el visor avisa
directamente en el overlay (no solo por consola) y no aplica el cambio. Los
vértices sin usar en ninguna cara (defecto real de algunos .obj, p.ej.
Bunny.obj trae 116 así) se descartan automáticamente antes de decimar o
subdividir, sin necesidad de activar "Soldar vértices" primero.

## Estructura

```text
mesh_viewer/
├── obj_io.py       # lectura/escritura de archivos .obj
├── topology.py     # aristas, componentes conectados, genus
├── mesh_ops.py     # suavizado laplaciano, edge split
├── mesh_repair.py  # soldadura de vértices, orientación, relleno de huecos
├── mesh_metrics.py # área, volumen, bounding box, calidad, non-manifold
├── viewer.py       # ventana única con PyVista
└── app.py          # orquestación / entry point
```
