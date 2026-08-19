"""Algoritmos de topología de malla: aristas, componentes conectados y genus.

Estos son los algoritmos académicos del proyecto (características de Euler,
BFS sobre el grafo de caras) y se mantienen conceptualmente idénticos a la
versión original — solo se optimiza la implementación de
`count_connected_components`, que antes era O(F²).
"""

from collections import deque
from dataclasses import dataclass


@dataclass
class MeshStats:
    num_vertices: int              # nv
    num_faces: int                 # nf (caras trianguladas)
    num_polygon_edges: int         # ne  (Aristas_Pol, fijo del .obj original)
    num_polygons: int              # np  (Polígonos, fijo del .obj original)
    num_triangle_polygons: int     # npt (Triangulos_Pol, fijo del .obj original)
    num_triangle_edges: int        # nef (Aristas_Tri, depende de la variante)
    num_connected_components: int  # ncc
    genus: float                   # ng


def triangle_edges(faces):
    """Aristas (deduplicadas) de una lista de caras trianguladas."""
    edges = set()
    for face in faces:
        for i in range(len(face)):
            edge = tuple(sorted((face[i], face[(i + 1) % len(face)])))
            edges.add(edge)
    return list(edges)


def connected_component_labels(faces):
    """Asigna a cada cara el id (0..k-1) de su componente conexo, donde dos
    caras son adyacentes si comparten al menos un vértice (mismo criterio
    que la versión original).

    Construye un índice invertido vértice -> caras una sola vez (O(F)) y lo
    usa para el BFS, en vez de recorrer todas las caras por cada cara (lo
    que hacía la versión original, O(F²)).
    """
    if not faces:
        return []

    vertex_to_faces = {}
    for face_index, face in enumerate(faces):
        for vertex in face:
            vertex_to_faces.setdefault(vertex, []).append(face_index)

    labels = [-1] * len(faces)
    next_label = 0
    for start_face in range(len(faces)):
        if labels[start_face] != -1:
            continue
        queue = deque([start_face])
        labels[start_face] = next_label
        while queue:
            current_face = queue.popleft()
            for vertex in faces[current_face]:
                for neighbor_face in vertex_to_faces[vertex]:
                    if labels[neighbor_face] == -1:
                        labels[neighbor_face] = next_label
                        queue.append(neighbor_face)
        next_label += 1

    return labels


def count_connected_components(vertices, faces):
    """Cuenta componentes conectados del grafo de caras (ver
    `connected_component_labels` para el criterio de adyacencia)."""
    labels = connected_component_labels(faces)
    return len(set(labels)) if labels else 0


def calculate_genus(vertices, edges, faces):
    """Genus vía característica de Euler (V - E + F). Mismo criterio que el
    original: fuera del rango [0, 10] se considera no representativo y
    devuelve -1."""
    num_vertices = len(vertices)
    num_edges = len(edges)
    num_faces = len(faces)

    if num_faces == 0:
        return -1  # sin caras, no se puede calcular el genus
    if num_vertices == 0 or num_edges == 0:
        return -1  # datos insuficientes

    euler_characteristic = num_vertices - num_edges + num_faces
    genus = 1 - (euler_characteristic / 2)
    if 0 <= genus <= 10:
        return genus
    return -1


def compute_stats(vertices, faces, polygon_stats) -> MeshStats:
    """Agregador único de estadísticas para una variante de la malla.

    `polygon_stats` siempre viene del .obj original (calculado una sola vez
    en obj_io.load_obj) — Aristas_Pol/Polígonos/Triangulos_Pol no cambian
    entre variantes, a diferencia de Aristas_Tri, que sí depende de la
    malla triangulada actual.
    """
    edges = triangle_edges(faces)
    return MeshStats(
        num_vertices=len(vertices),
        num_faces=len(faces),
        num_polygon_edges=polygon_stats.num_polygon_edges,
        num_polygons=polygon_stats.num_polygons,
        num_triangle_polygons=polygon_stats.num_triangle_polygons,
        num_triangle_edges=len(edges),
        num_connected_components=count_connected_components(vertices, faces),
        genus=calculate_genus(vertices, edges, faces),
    )
