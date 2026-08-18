"""Operaciones de transformación de malla: suavizado laplaciano y edge split.

Funciones puras extraídas de las antiguas clases Renderer* — misma fórmula,
sin ninguna dependencia de renderizado.
"""

import numpy as np


def apply_laplacian_smoothing(vertices, faces, iterations=1, factor=0.5):
    """Suaviza los vértices promediando con sus vecinos directos (por arista
    de triángulo), `iterations` veces, mezclado con la posición original
    según `factor`."""
    smoothed_vertices = vertices.copy()
    vertices_np = np.array(vertices)
    faces_np = np.array(faces)

    adjacency = [[] for _ in range(len(vertices_np))]
    for face in faces_np:
        for i in range(3):
            v1 = face[i]
            v2 = face[(i + 1) % 3]
            adjacency[v1].append(v2)
            adjacency[v2].append(v1)

    for _ in range(iterations):
        for i, vertex in enumerate(vertices_np):
            neighbors = adjacency[i]
            num_neighbors = len(neighbors)
            if num_neighbors == 0:
                continue
            avg_neighbor_pos = sum(vertices_np[neighbor] for neighbor in neighbors) / num_neighbors
            smoothed_vertices[i] = (1 - factor) * vertex + factor * avg_neighbor_pos

    return smoothed_vertices


def apply_edge_split(vertices, triangles):
    """Subdivide cada triángulo en 4, insertando un vértice en el punto medio
    de cada arista."""
    new_vertices = vertices[:]
    new_triangles = []
    for tri in triangles:
        mid_points = []
        for i in range(3):
            start, end = tri[i], tri[(i + 1) % 3]
            mid_point = [(vertices[start][j] + vertices[end][j]) / 2 for j in range(3)]
            mid_index = len(new_vertices)
            new_vertices.append(mid_point)
            mid_points.append(mid_index)

        new_triangles.extend([
            [tri[0], mid_points[0], mid_points[2]],
            [tri[1], mid_points[1], mid_points[0]],
            [tri[2], mid_points[2], mid_points[1]],
            [mid_points[0], mid_points[1], mid_points[2]],
        ])
    return new_vertices, new_triangles
