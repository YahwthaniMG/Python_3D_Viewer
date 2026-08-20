"""Herramientas de reparación de malla: soldadura de vértices, orientación
consistente de triángulos y relleno de huecos.

A diferencia de mesh_ops.py (que genera variantes académicas de la malla),
estos algoritmos arreglan defectos comunes de mallas escaneadas/exportadas.
"""

import math
from collections import deque


def drop_unreferenced_vertices(vertices, faces):
    """Elimina vértices que ninguna cara usa, sin fundir posiciones
    coincidentes (eso lo hace weld_vertices).

    Algunos .obj traen líneas "v" declaradas que ninguna "f" referencia
    (p.ej. Bunny.obj trae 116 así). Eso hace fallar en silencio filtros de
    VTK como la subdivisión Loop, que esperan que todo punto tenga alguna
    cara alrededor — por eso el visor llama esto siempre antes de decimar o
    subdividir, independientemente de si "Soldar vértices" está activo."""
    used = {v for face in faces for v in face}
    old_to_new = {}
    new_vertices = []
    for old_index, vertex in enumerate(vertices):
        if old_index in used:
            old_to_new[old_index] = len(new_vertices)
            new_vertices.append(vertex)
    new_faces = [[old_to_new[v] for v in face] for face in faces]
    return new_vertices, new_faces


def weld_vertices(vertices, faces, epsilon=1e-4):
    """Funde vértices coincidentes (dentro de `epsilon`) en uno solo, y
    descarta los vértices que ninguna cara termina usando.

    Agrupa vértices por celda de una grilla de tamaño `epsilon` (mismo
    enfoque simple que usa MeshLab por defecto en "Merge Close Vertices"):
    vértices que caen en la misma celda se funden al primero encontrado.
    Elimina además las caras que quedan degeneradas (con vértices repetidos)
    tras la soldadura.

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

    new_vertices, new_faces = drop_unreferenced_vertices(merged_vertices, merged_faces)
    num_merged = len(vertices) - len(new_vertices)
    return new_vertices, new_faces, num_merged


def edge_owner_map(faces):
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
    owners = edge_owner_map(faces)
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
    owners = edge_owner_map(faces)
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


def _edge_length(vertices, a, b):
    ax, ay, az = vertices[a]
    bx, by, bz = vertices[b]
    return math.sqrt((bx - ax) ** 2 + (by - ay) ** 2 + (bz - az) ** 2)


def _average_edge_length(vertices, faces):
    if not faces:
        return 0.0
    total, count = 0.0, 0
    for face in faces:
        n = len(face)
        for i in range(n):
            total += _edge_length(vertices, face[i], face[(i + 1) % n])
            count += 1
    return total / count if count else 0.0


def _polygon_centroid(vertices, loop):
    return [sum(vertices[v][axis] for v in loop) / len(loop) for axis in range(3)]


def _distance(p, q):
    return math.sqrt(sum((p[k] - q[k]) ** 2 for k in range(3)))


def _fan_faces(loop, centroid_index, flip):
    n = len(loop)
    faces = []
    for i in range(n):
        u, v = loop[i], loop[(i + 1) % n]
        faces.append([u, v, centroid_index] if flip else [v, u, centroid_index])
    return faces


def _polygon_area_estimate(vertices, loop):
    """Área aproximada del polígono (suma de triángulos centroide-arista;
    exacta si es plano, una estimación razonable si no). Sirve para
    detectar cortes degenerados: un corte que cae sobre un tramo de borde
    colineal deja un lado con área ~0."""
    centroid = _polygon_centroid(vertices, loop)
    n = len(loop)
    total = 0.0
    for i in range(n):
        a, b = vertices[loop[i]], vertices[loop[(i + 1) % n]]
        ux, uy, uz = a[0] - centroid[0], a[1] - centroid[1], a[2] - centroid[2]
        vx, vy, vz = b[0] - centroid[0], b[1] - centroid[1], b[2] - centroid[2]
        cx, cy, cz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        total += math.sqrt(cx * cx + cy * cy + cz * cz)
    return total / 2


def _fill_polygon(vertices, loop, flip, target_length, depth=0):
    """Rellena el polígono `loop` (índices de vértice ya existentes, en el
    orden de winding correcto según `flip`) con triángulos.

    Si el abanico desde un solo centroide daría triángulos mucho más
    grandes que `target_length`, en vez de subdividirlos (lo que
    obligaría a partir también las aristas del borde original, dejándolas
    sin coincidir con la cara vecina real al otro lado — se verificó que
    eso crea huecos fantasma) se parte el polígono en dos mitades con una
    diagonal nueva entre dos vértices que YA existen en el borde, y se
    recurre en cada mitad. Así el borde original nunca se toca."""
    n = len(loop)
    if n == 3:
        return [[loop[0], loop[1], loop[2]] if flip else [loop[0], loop[2], loop[1]]]

    centroid = _polygon_centroid(vertices, loop)
    spoke_max = max(_distance(vertices[v], centroid) for v in loop)

    if depth >= 8 or target_length <= 0 or spoke_max <= target_length * 1.5:
        centroid_index = len(vertices)
        vertices.append(centroid)
        return _fan_faces(loop, centroid_index, flip)

    # Elegir el punto de corte que maximiza el área mínima entre las dos
    # mitades resultantes, en vez de partir siempre por la mitad de la
    # lista de índices: un corte por posición puede caer sobre un tramo de
    # borde colineal (común en mallas tipo grilla) y dejar un lado con área
    # ~0 -- un triángulo degenerado más adelante. Coordinar por área evita
    # ese caso sin necesitar detectar colinealidad explícitamente.
    total_area = _polygon_area_estimate(vertices, loop)
    best_i, best_score = None, -1.0
    for i in range(2, n - 1):
        loop_a = loop[: i + 1]
        loop_b = loop[i:] + [loop[0]]
        score = min(_polygon_area_estimate(vertices, loop_a), _polygon_area_estimate(vertices, loop_b))
        if score > best_score:
            best_score, best_i = score, i

    if total_area <= 0 or best_score / total_area < 1e-6:
        # Ningún corte disponible evita la degeneración (tramo casi/del
        # todo colineal, p.ej. el borde recto de una grilla): mejor un
        # abanico más grande pero válido que forzar un triángulo de área ~0.
        centroid_index = len(vertices)
        vertices.append(centroid)
        return _fan_faces(loop, centroid_index, flip)

    loop_a = loop[: best_i + 1]           # loop[0]..loop[best_i], cierra con la nueva diagonal (loop[best_i], loop[0])
    loop_b = loop[best_i:] + [loop[0]]    # loop[best_i]..loop[0], la misma diagonal del otro lado
    return (
        _fill_polygon(vertices, loop_a, flip, target_length, depth + 1)
        + _fill_polygon(vertices, loop_b, flip, target_length, depth + 1)
    )


def fill_holes(vertices, faces):
    """Rellena cada hueco con triángulos, apuntando a un tamaño parecido al
    promedio de la malla existente (ver _fill_polygon) en vez de un solo
    abanico desde el centroide, que en huecos grandes deja unos pocos
    triángulos enormes comparados con el resto de la malla.

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

    Limitación conocida: en mallas con aristas non-manifold cerca de un
    hueco (ver unify_orientation), muy ocasionalmente un hueco chico no
    termina de cerrar del todo — verificado en ~1 de cada docena de huecos
    en algunos archivos reales (Batman, Heart), nunca en los huecos grandes
    que motivaron el refinamiento. Queda visible en el contador "Huecos"
    del visor en vez de fallar en silencio.

    Devuelve (new_vertices, new_faces, num_holes_filled).
    """
    owners = edge_owner_map(faces)
    loops = boundary_loops(faces)
    target_length = _average_edge_length(vertices, faces)
    new_vertices = list(vertices)
    new_faces = list(faces)

    for loop in loops:
        u0, v0 = loop[0], loop[1]
        key = (u0, v0) if u0 < v0 else (v0, u0)
        neighbor_index, _ = owners[key][0]
        neighbor_normal = _face_normal(vertices, faces[neighbor_index])

        probe_centroid_index = len(new_vertices)
        new_vertices.append(_polygon_centroid(vertices, loop))
        candidate_normal = _face_normal(new_vertices, [v0, u0, probe_centroid_index])
        flip = _dot(candidate_normal, neighbor_normal) < 0
        del new_vertices[probe_centroid_index]  # solo era para decidir el sentido; el relleno real crea los suyos

        new_faces.extend(_fill_polygon(new_vertices, loop, flip, target_length))

    return new_vertices, new_faces, len(loops)
