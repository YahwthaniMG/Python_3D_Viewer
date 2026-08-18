"""Lectura y escritura de archivos OBJ.

Convierte caras con más de 3 vértices a triángulos mediante fan
triangulation, y conserva el conteo de aristas/polígonos originales
(antes de triangular) para las estadísticas de la malla.
"""

import os
from dataclasses import dataclass


@dataclass
class PolygonStats:
    """Conteos derivados de las caras del .obj tal como fueron leídas,
    antes de la fan triangulation."""
    num_polygon_edges: int      # aristas de los polígonos originales
    num_polygons: int           # total de caras leídas del archivo
    num_triangle_polygons: int  # de esas caras, cuántas ya eran triángulos


def load_obj(file_path):
    """Lee un archivo .obj y devuelve (vertices, faces, polygon_stats).

    `faces` está completamente triangulado (fan triangulation para
    polígonos con más de 3 vértices).
    """
    vertices = []
    faces = []
    polygon_edges = set()
    num_polygons = 0
    num_triangle_polygons = 0

    with open(file_path, "r") as f:
        for line in f:
            if line.startswith("v "):
                vertex = list(map(float, line.strip().split()[1:]))
                vertices.append(vertex)
            elif line.startswith("f "):
                raw_face = line.strip().split()[1:]
                face_vertices = [int(v.split("/")[0]) - 1 for v in raw_face]
                num_polygons += 1

                num_face_vertices = len(face_vertices)
                for i in range(num_face_vertices):
                    edge = tuple(sorted((face_vertices[i], face_vertices[(i + 1) % num_face_vertices])))
                    polygon_edges.add(edge)

                if num_face_vertices > 3:
                    for i in range(1, num_face_vertices - 1):
                        faces.append([face_vertices[0], face_vertices[i], face_vertices[i + 1]])
                else:
                    num_triangle_polygons += 1
                    faces.append(face_vertices)

    stats = PolygonStats(
        num_polygon_edges=len(polygon_edges),
        num_polygons=num_polygons,
        num_triangle_polygons=num_triangle_polygons,
    )
    return vertices, faces, stats


def write_obj(file_path, vertices, faces):
    """Escribe una malla a un archivo .obj."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        f.write("Autor: Yahwthani Morales Gómez\n")
        for vertex in vertices:
            f.write(f"v {' '.join(map(str, vertex))}\n")
        for face in faces:
            f.write("f")
            for vertex_index in face:
                f.write(f" {vertex_index + 1}")  # OBJ indexa desde 1
            f.write("\n")


def export_path(obj_file_path, suffix):
    """Construye la ruta de exportación en OBJsExport/ para una variante,
    p.ej. export_path("OBJs/cup.obj", "EdgeSplit") -> "OBJsExport/cupEdgeSplit.obj"
    """
    name, ext = os.path.splitext(os.path.basename(obj_file_path))
    return os.path.join("OBJsExport", f"{name}{suffix}{ext}")
