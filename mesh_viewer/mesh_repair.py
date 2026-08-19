"""Herramientas de reparación de malla: soldadura de vértices, orientación
consistente de triángulos y relleno de huecos.

A diferencia de mesh_ops.py (que genera variantes académicas de la malla),
estos algoritmos arreglan defectos comunes de mallas escaneadas/exportadas.
"""

from collections import deque


def weld_vertices(vertices, faces, epsilon=1e-4):
    """Funde vértices coincidentes (dentro de `epsilon`) en uno solo, y
    descarta los vértices que ninguna cara termina usando.

    Agrupa vértices por celda de una grilla de tamaño `epsilon` (mismo
    enfoque simple que usa MeshLab por defecto en "Merge Close Vertices"):
    vértices que caen en la misma celda se funden al primero encontrado.
    Elimina además las caras que quedan degeneradas (con vértices repetidos)
    tras la soldadura, y los vértices que quedan sin ninguna cara (algunos
    .obj traen líneas "v" declaradas que ninguna "f" referencia — p.ej.
    Bunny.obj trae 116 así; eso hace fallar filtros de VTK como la
    subdivisión Loop, que esperan que todo punto tenga alguna cara alrededor).

    Devuelve (new_vertices, new_faces, num_merged).
    """
    merged_vertices = []
    old_to_merged = []
    cell_to_merged_index = {}

    for vertex in vertices:
        cell = tuple(round(c / epsilon) for c in vertex)
        merged_index = cell_to_merged_index.get(cell)
        if merged_index is None:
            merged_index = len(merged_vertices)
            cell_to_merged_index[cell] = merged_index
            merged_vertices.append(vertex)
        old_to_merged.append(merged_index)

    merged_faces = []
    for face in faces:
        remapped = [old_to_merged[v] for v in face]
        if len(set(remapped)) == len(remapped):  # descarta caras degeneradas
            merged_faces.append(remapped)

    used = {v for face in merged_faces for v in face}
    merged_to_new = {}
    new_vertices = []
    for merged_index, vertex in enumerate(merged_vertices):
        if merged_index in used:
            merged_to_new[merged_index] = len(new_vertices)
            new_vertices.append(vertex)
    new_faces = [[merged_to_new[v] for v in face] for face in merged_faces]

    num_merged = len(vertices) - len(new_vertices)
    return new_vertices, new_faces, num_merged


def _edge_owner_map(faces):
    """Mapa {arista_no_dirigida: [(cara_idx, arista_dirigida), ...]} — para
    cada arista de triángulo, qué caras la usan y en qué dirección."""
    owners = {}
    for face_index, face in enumerate(faces):
        n = len(face)
        for i in range(n):
            u, v = face[i], face[(i + 1) % n]
            key = (u, v) if u < v else (v, u)
            owners.setdefault(key, []).append((face_index, (u, v)))
    return owners


def unify_orientation(faces):
    """Voltea el winding de triángulos para que todos los de un mismo
    componente conexo (por arista compartida) giren en el mismo sentido.

    No garantiza que el sentido resultante sea "hacia afuera": solo hace
    que sea consistente dentro de cada componente, partiendo del winding
    de la primera cara visitada como referencia (misma limitación que la
    herramienta equivalente de MeshLab sin un paso adicional de normales
    globales).

    Solo propaga orientación a través de aristas manifold (compartidas por
    exactamente 2 caras). Una arista compartida por 3+ caras (non-manifold)
    es ambigua — no hay forma de que todas queden "opuestas" entre sí a la
    vez — así que esas caras se tratan como el inicio de su propio
    componente en vez de arriesgar una propagación incorrecta que termine
    generando más inconsistencias de las que había (se verificó
    empíricamente: sin este filtro, una sola arista non-manifold puede
    hacer que la malla completa quede peor que antes de repararla).

    Devuelve (new_faces, num_flipped).
    """
    owners = _edge_owner_map(faces)
    result = [list(face) for face in faces]
    visited = [False] * len(faces)
    num_flipped = 0

    for start_face in range(len(faces)):
        if visited[start_face]:
            continue
        visited[start_face] = True
        queue = deque([start_face])
        while queue:
            current = queue.popleft()
            face = result[current]
            n = len(face)
            for i in range(n):
                u, v = face[i], face[(i + 1) % n]
                key = (u, v) if u < v else (v, u)
                owner_list = owners[key]
                if len(owner_list) != 2:
                    continue  # arista de borde o non-manifold: no se propaga por ahí
                for neighbor_index, neighbor_edge in owner_list:
                    if neighbor_index == current:
                        continue
                    if not visited[neighbor_index]:
                        visited[neighbor_index] = True
                        if neighbor_edge == (u, v):
                            # Mismo sentido que la cara ya visitada -> inconsistente, se voltea.
                            result[neighbor_index] = list(reversed(result[neighbor_index]))
                            num_flipped += 1
                        queue.append(neighbor_index)

    return result, num_flipped


def boundary_loops(faces):
    """Encuentra los huecos de la malla como listas de índices de vértice
    (uno por hueco), siguiendo las aristas de borde (usadas por una sola
    cara) en el sentido en que su única cara dueña las recorre."""
    owners = _edge_owner_map(faces)
    next_vertex = {}
    for edge_key, owner_list in owners.items():
        if len(owner_list) == 1:
            _, (u, v) = owner_list[0]
            next_vertex[u] = v

    loops = []
    visited_starts = set()
    for start in list(next_vertex):
        if start in visited_starts:
            continue
        loop = []
        current = start
        while current not in visited_starts:
            visited_starts.add(current)
            loop.append(current)
            current = next_vertex.get(current)
            if current is None:
                loop = []  # no cerró en ciclo (borde abierto irregular) -> se descarta
                break
        if loop and current == start:
            loops.append(loop)

    return loops


def _face_normal(vertices, face):
    ax, ay, az = vertices[face[0]]
    bx, by, bz = vertices[face[1]]
    cx, cy, cz = vertices[face[2]]
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    return (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def fill_holes(vertices, faces):
    """Rellena cada hueco con un abanico de triángulos desde su centroide.

    Para una arista de borde (u, v), el orden "natural" de la cara de
    relleno es (v, u, centroide). Eso da la orientación correcta cuando el
    centroide cae del lado vacío del hueco (el caso típico: un gap chico en
    una superficie). Pero si el hueco es en realidad el borde exterior de
    una malla abierta (p.ej. el borde de una lámina, o el labio de una taza
    sin fondo), el centroide del lazo completo cae del lado donde YA hay
    superficie, y ese orden queda con la normal invertida.

    En vez de asumir un caso u otro, se verifica geométricamente: se compara
    la normal de la primera cara de relleno del hueco contra la normal de la
    cara real vecina que comparte esa arista, y si apuntan en direcciones
    opuestas, se voltea el abanico completo de ese hueco.

    Devuelve (new_vertices, new_faces, num_holes_filled).
    """
    owners = _edge_owner_map(faces)
    loops = boundary_loops(faces)
    new_vertices = list(vertices)
    new_faces = list(faces)

    for loop in loops:
        centroid = [sum(vertices[v][axis] for v in loop) / len(loop) for axis in range(3)]
        centroid_index = len(new_vertices)
        new_vertices.append(centroid)

        u0, v0 = loop[0], loop[1]
        key = (u0, v0) if u0 < v0 else (v0, u0)
        neighbor_index, _ = owners[key][0]
        neighbor_normal = _face_normal(vertices, faces[neighbor_index])
        candidate_normal = _face_normal(new_vertices, [v0, u0, centroid_index])
        flip = _dot(candidate_normal, neighbor_normal) < 0

        n = len(loop)
        for i in range(n):
            u, v = loop[i], loop[(i + 1) % n]
            new_faces.append([u, v, centroid_index] if flip else [v, u, centroid_index])

    return new_vertices, new_faces, len(loops)
