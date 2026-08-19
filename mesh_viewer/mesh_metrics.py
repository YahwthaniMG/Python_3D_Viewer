"""Medidas geométricas y de calidad de malla: área, volumen, bounding box,
calidad de triángulos y aristas non-manifold.

A diferencia de topology.py (propiedades combinatorias: genus, componentes
conectados) estas medidas dependen de las posiciones reales de los vértices.
"""

import math

from . import mesh_repair

_HISTOGRAM_BLOCKS = " .:-=+*#%@"


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(a):
    return math.sqrt(_dot(a, a))


def surface_area(vertices, faces):
    """Suma del área de cada triángulo (mitad de la magnitud del producto
    cruz de dos de sus aristas)."""
    total = 0.0
    for face in faces:
        a, b, c = (vertices[i] for i in face[:3])
        total += 0.5 * _norm(_cross(_sub(b, a), _sub(c, a)))
    return total


def bounding_box(vertices):
    """Dimensiones (dx, dy, dz) del bounding box axis-aligned."""
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    zs = [v[2] for v in vertices]
    return (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))


def volume(vertices, faces):
    """Volumen encerrado, vía el teorema de la divergencia aplicado a la
    malla triangulada: V = (1/6) |Σ v0 · (v1 × v2)|.

    Solo es físicamente significativo si la malla es watertight (sin
    huecos) — el llamador decide si mostrarlo según boundary_loops."""
    total = 0.0
    for face in faces:
        a, b, c = (vertices[i] for i in face[:3])
        total += _dot(a, _cross(b, c))
    return abs(total) / 6.0


def triangle_quality(vertices, face):
    """Calidad normalizada de un triángulo: 1.0 = equilátero, -> 0 = degenerado.

    quality = 4*sqrt(3)*área / (a² + b² + c²), con a,b,c las longitudes de
    sus aristas (métrica estándar de calidad de malla, p.ej. usada en
    generación de mallas FEM)."""
    a, b, c = (vertices[i] for i in face[:3])
    ab, bc, ca = _sub(b, a), _sub(c, b), _sub(a, c)
    edge_sq_sum = _dot(ab, ab) + _dot(bc, bc) + _dot(ca, ca)
    if edge_sq_sum == 0:
        return 0.0
    area = 0.5 * _norm(_cross(ab, _sub(c, a)))
    return (4 * math.sqrt(3) * area) / edge_sq_sum


def quality_stats(vertices, faces, bins=10):
    """Calidad promedio y un histograma (lista de `bins` conteos, 0 a 1) de
    la calidad de todos los triángulos."""
    if not faces:
        return 0.0, [0] * bins
    qualities = [triangle_quality(vertices, face) for face in faces]
    histogram = [0] * bins
    for q in qualities:
        index = min(int(q * bins), bins - 1)
        histogram[index] += 1
    return sum(qualities) / len(qualities), histogram


def format_histogram(histogram):
    """Convierte un histograma (lista de conteos) en una barra compacta de
    caracteres de bloque Unicode, p.ej. "▂▅█▇▄▂▁▁ "."""
    peak = max(histogram) if histogram else 0
    if peak == 0:
        return " " * len(histogram)
    levels = len(_HISTOGRAM_BLOCKS) - 1
    return "".join(_HISTOGRAM_BLOCKS[round(count / peak * levels)] for count in histogram)


def non_manifold_edge_count(faces):
    """Cuenta aristas compartidas por 3 o más caras (topológicamente
    ambiguas — ver la nota en mesh_repair.unify_orientation)."""
    owners = mesh_repair.edge_owner_map(faces)
    return sum(1 for owner_list in owners.values() if len(owner_list) > 2)
