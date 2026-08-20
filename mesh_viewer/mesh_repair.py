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


def _polygon_centroid(vertices, loop):
    return [sum(vertices[v][axis] for v in loop) / len(loop) for axis in range(3)]


def _sub3(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _polygon_normal(vertices, loop):
    """Normal de referencia del polígono vía el método de Newell — a
    diferencia de un solo producto cruz de 3 vértices, da un resultado
    razonable incluso si el polígono no es perfectamente plano o si esos
    3 vértices en particular son casi colineales."""
    nx = ny = nz = 0.0
    n = len(loop)
    for i in range(n):
        ax, ay, az = vertices[loop[i]]
        bx, by, bz = vertices[loop[(i + 1) % n]]
        nx += (ay - by) * (az + bz)
        ny += (az - bz) * (ax + bx)
        nz += (ax - bx) * (ay + by)
    return (nx, ny, nz)


def _point_in_triangle(p, a, b, c):
    """¿`p` cae dentro (o muy cerca del borde) del triángulo (a,b,c)?
    Coordenadas baricéntricas proyectando sobre el plano del triángulo."""
    v0, v1, v2 = _sub3(c, a), _sub3(b, a), _sub3(p, a)
    dot00, dot01, dot02 = _dot(v0, v0), _dot(v0, v1), _dot(v0, v2)
    dot11, dot12 = _dot(v1, v1), _dot(v1, v2)
    denom = dot00 * dot11 - dot01 * dot01
    if abs(denom) < 1e-18:
        return False
    u = (dot11 * dot02 - dot01 * dot12) / denom
    v = (dot00 * dot12 - dot01 * dot02) / denom
    eps = 1e-7
    return u >= -eps and v >= -eps and (u + v) <= 1 + eps


def _fan_faces(loop, centroid_index, flip):
    n = len(loop)
    faces = []
    for i in range(n):
        u, v = loop[i], loop[(i + 1) % n]
        faces.append([u, v, centroid_index] if flip else [v, u, centroid_index])
    return faces


def _edge_key(u, v):
    return (u, v) if u < v else (v, u)


def _average_boundary_edge_length(vertices, loop):
    n = len(loop)
    total = sum(_dist3(vertices[loop[i]], vertices[loop[(i + 1) % n]]) for i in range(n))
    return total / n


def _dist3(a, b):
    return math.sqrt(sum((a[k] - b[k]) ** 2 for k in range(3)))


def _polygon_plane_basis(vertices, loop):
    """Origen (centroide) y una base ortonormal (normal, eje_u, eje_v) del
    plano que mejor ajusta al polígono. Devuelve None si el polígono es
    degenerado (normal ~0, p.ej. todos sus vértices colineales)."""
    origin = _polygon_centroid(vertices, loop)
    normal = _polygon_normal(vertices, loop)
    normal_len = math.sqrt(_dot(normal, normal))
    if normal_len < 1e-12:
        return None
    normal = tuple(c / normal_len for c in normal)

    seed = (1.0, 0.0, 0.0) if abs(normal[0]) < 0.9 else (0.0, 1.0, 0.0)
    u = _sub3(seed, tuple(c * _dot(seed, normal) for c in normal))
    u_len = math.sqrt(_dot(u, u))
    if u_len < 1e-12:
        return None
    u = tuple(c / u_len for c in u)
    v = _cross(normal, u)
    return origin, normal, u, v


def _to_plane_2d(point, origin, u, v):
    d = _sub3(point, origin)
    return (_dot(d, u), _dot(d, v))


def _point_in_polygon_2d(p, poly2d):
    """Ray casting estándar: ¿`p` cae dentro del polígono 2D `poly2d`?"""
    x, y = p
    inside = False
    n = len(poly2d)
    for i in range(n):
        x1, y1 = poly2d[i]
        x2, y2 = poly2d[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            x_intersect = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < x_intersect:
                inside = not inside
    return inside


def _dist_point_to_segment_2d(p, a, b):
    px, py = p
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    if length_sq < 1e-18:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _dist_point_to_polygon_2d(p, poly2d):
    n = len(poly2d)
    return min(_dist_point_to_segment_2d(p, poly2d[i], poly2d[(i + 1) % n]) for i in range(n))


def generate_interior_points(vertices, loop, spacing):
    """Genera puntos 3D nuevos adentro del polígono `loop`, en una grilla
    tipo hexagonal (filas alternadas desplazadas) espaciada ~`spacing`,
    proyectando sobre el plano que mejor ajusta al polígono. Descarta los
    puntos que caen fuera del polígono o muy cerca de su borde (para no
    dejar triángulos angostos pegados al borde).

    Devuelve una lista de puntos 3D nuevos (todavía no agregados a ninguna
    malla) — lista vacía si el polígono es muy chico/degenerado para que
    quepa ni un solo punto interior."""
    if spacing <= 0:
        return []
    basis = _polygon_plane_basis(vertices, loop)
    if basis is None:
        return []
    origin, normal, u, v = basis

    poly2d = [_to_plane_2d(vertices[i], origin, u, v) for i in loop]
    xs, ys = [p[0] for p in poly2d], [p[1] for p in poly2d]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)

    margin = spacing * 0.6
    row_height = spacing * 0.866  # ~sqrt(3)/2, filas tipo grilla triangular
    points = []
    y = min_y + spacing
    row = 0
    while y < max_y:
        x_offset = (spacing / 2) if row % 2 else 0.0
        x = min_x + spacing + x_offset
        while x < max_x:
            p2 = (x, y)
            if _point_in_polygon_2d(p2, poly2d) and _dist_point_to_polygon_2d(p2, poly2d) >= margin:
                points.append([origin[k] + p2[0] * u[k] + p2[1] * v[k] for k in range(3)])
            x += spacing
        y += row_height
        row += 1
    return points


def _ear_clip(vertices, loop, flip, owner_count):
    """Triangula el polígono `loop` (vértices ya existentes, en el orden de
    winding correcto según `flip`) por ear clipping: en cada paso busca 3
    vértices consecutivos que formen una "oreja" válida — convexa, sin
    ningún otro vértice del polígono adentro, y sin que ya exista una cara
    en la malla que use alguna de sus 3 aristas dos veces (lo que la
    volvería non-manifold al agregar esta) — y la recorta. Sigue la forma
    real del hueco en vez de cortar diagonales por posición en la lista, y
    nunca duplica una cara que ya esté en la malla.

    `owner_count` (compartido entre todos los huecos de la misma llamada a
    fill_holes) es un {arista: cantidad_de_dueños} que se va actualizando a
    medida que se aceptan caras nuevas, para detectar ese conflicto incluso
    entre huecos distintos o entre orejas del mismo hueco."""
    remaining = list(loop)
    ref_normal = _polygon_normal(vertices, loop)
    faces = []

    while len(remaining) > 3:
        n = len(remaining)
        clipped = False
        for i in range(n):
            prev_v = remaining[(i - 1) % n]
            cur_v = remaining[i]
            next_v = remaining[(i + 1) % n]
            a, b, c = vertices[prev_v], vertices[cur_v], vertices[next_v]

            tri_normal = _cross(_sub3(b, a), _sub3(c, a))
            if _dot(tri_normal, ref_normal) <= 1e-12:
                continue  # oreja cóncava o degenerada

            if (
                owner_count.get(_edge_key(prev_v, cur_v), 0) >= 2
                or owner_count.get(_edge_key(cur_v, next_v), 0) >= 2
                or owner_count.get(_edge_key(next_v, prev_v), 0) >= 2
            ):
                continue  # ya hay una cara real usando alguna de estas aristas -> duplicaria

            if any(
                v != prev_v and v != cur_v and v != next_v and _point_in_triangle(vertices[v], a, b, c)
                for v in remaining
            ):
                continue  # otro vertice del poligono cae adentro -> no es una oreja valida

            face = [prev_v, cur_v, next_v] if flip else [prev_v, next_v, cur_v]
            faces.append(face)
            for j in range(3):
                key = _edge_key(face[j], face[(j + 1) % 3])
                owner_count[key] = owner_count.get(key, 0) + 1
            del remaining[i]
            clipped = True
            break
        if not clipped:
            break  # ninguna oreja valida en toda una pasada -> fallback abajo

    if len(remaining) == 3:
        p, cu, nx = remaining
        faces.append([p, cu, nx] if flip else [p, nx, cu])
    elif len(remaining) > 3:
        # No debería pasar en la práctica (polígono muy degenerado): mejor
        # un abanico simple para lo que quede que dejar el hueco sin cerrar.
        centroid_index = len(vertices)
        vertices.append(_polygon_centroid(vertices, remaining))
        faces.extend(_fan_faces(remaining, centroid_index, flip))

    return faces


def _delaunay_fill(vertices, loop, flip, owner_count):
    """Intenta rellenar el hueco insertando puntos interiores nuevos (ver
    generate_interior_points) y retriangulando con Delaunay 2D restringido
    al borde (vtkDelaunay2D vía pyvista, con `edge_source` fijando el
    contorno) — da un patrón más parecido a una grilla regular que ear
    clipping, que solo conecta los vértices del borde ya existentes.

    Devuelve (nuevos_puntos, nuevas_caras), o None si algo no cuadra (no hay
    lugar para puntos interiores, el filtro no da triángulos limpios, o el
    resultado duplicaría una arista que ya tiene 2 dueños) — en ese caso el
    llamador cae de vuelta a ear clipping, ya validado como robusto."""
    import numpy as np
    import pyvista as pv

    spacing = _average_boundary_edge_length(vertices, loop)
    interior = generate_interior_points(vertices, loop, spacing)
    if not interior:
        return None

    n = len(loop)
    all_pts = np.asarray([list(vertices[i]) for i in loop] + interior, dtype=float)

    cloud = pv.PolyData(all_pts)
    edge_source = pv.PolyData()
    edge_source.points = all_pts
    edge_source.lines = np.array([x for i in range(n) for x in (2, i, (i + 1) % n)], dtype=np.int64)

    try:
        result = cloud.delaunay_2d(edge_source=edge_source)
    except Exception:
        return None
    if result.n_points == 0 or result.n_cells == 0:
        return None

    faces_arr = result.faces
    if faces_arr.size == 0 or faces_arr.size % 4 != 0:
        return None
    faces_local = faces_arr.reshape(-1, 4)
    if not np.all(faces_local[:, 0] == 3):
        return None  # algun output que no es triangulo puro -> no confiar

    # vtkDelaunay2D con edge_source (Delaunay restringido) puede devolver
    # triángulos con winding internamente inconsistente entre sí — se
    # verificó empíricamente (una grilla con hueco grande dio 6 aristas
    # inconsistentes en el resultado crudo). Se reutiliza unify_orientation
    # para forzar consistencia interna antes de decidir si hay que voltear
    # el lote completo.
    faces_local_list, _ = unify_orientation(faces_local[:, 1:].tolist())

    base_new_index = len(vertices)

    def remap(i):
        return loop[i] if i < n else base_new_index + (i - n)

    candidate_faces = [[remap(a), remap(b), remap(c)] for a, b, c in faces_local_list]

    # ¿Hay que voltear todo el resultado? Se compara UNA cara de muestra que
    # use la arista de borde (loop[0], loop[1]) contra el sentido esperado
    # según `flip` (mismo criterio que _ear_clip). Ahora que ya se forzó
    # consistencia interna arriba, alcanza con revisar una sola cara.
    u0, v0 = loop[0], loop[1]
    expected = (u0, v0) if flip else (v0, u0)
    reverse_all = None
    for face in candidate_faces:
        if u0 in face and v0 in face:
            k = face.index(u0)
            actual = (u0, v0) if face[(k + 1) % 3] == v0 else (v0, u0)
            reverse_all = actual != expected
            break
    if reverse_all is None:
        return None
    if reverse_all:
        candidate_faces = [list(reversed(f)) for f in candidate_faces]

    # Nunca duplicar una arista que ya tenga 2 dueños (mismo chequeo que
    # ear clipping) — si cualquier cara del resultado lo haría, se descarta
    # el intento completo (todo o nada) y se cae a ear clipping. Se valida
    # de forma incremental contra una copia temporal (no la real hasta el
    # final): si se comparara cada cara contra una sola foto fija del
    # estado, 3+ caras del propio lote que terminan compartiendo una arista
    # entre sí (posible si el filtro genera puntos casi coincidentes) se
    # colarían, porque cada una individualmente ve el conteo en 0 o 1.
    staged = dict(owner_count)
    for face in candidate_faces:
        for j in range(3):
            key = _edge_key(face[j], face[(j + 1) % 3])
            count = staged.get(key, 0) + 1
            if count > 2:
                return None
            staged[key] = count

    owner_count.clear()
    owner_count.update(staged)
    return interior, candidate_faces


def fill_holes(vertices, faces):
    """Rellena cada hueco, insertando puntos interiores nuevos y
    retriangulando con Delaunay 2D restringido al borde cuando hay lugar
    para eso (ver _delaunay_fill — da un patrón parecido a una grilla
    regular), o por ear clipping si no (ver _ear_clip — hueco chico, o el
    intento con Delaunay no dio un resultado confiable).

    Para una arista de borde (u, v), el orden "natural" de la cara de
    relleno es (v, u, ...). Eso da la orientación correcta cuando el hueco
    es un gap chico en una superficie. Pero si el hueco es en realidad el
    borde exterior de una malla abierta (p.ej. el borde de una lámina, o el
    labio de una taza sin fondo), ese orden queda con la normal invertida.
    En vez de asumir un caso u otro, se verifica geométricamente: se compara
    la normal de una cara de prueba contra la normal de la cara real vecina
    que comparte esa arista, y si apuntan en direcciones opuestas, se voltea
    el relleno completo de ese hueco.

    Devuelve (new_vertices, new_faces, num_holes_filled).
    """
    owners = edge_owner_map(faces)
    loops = boundary_loops(faces)
    new_vertices = list(vertices)
    new_faces = list(faces)
    owner_count = {key: len(owner_list) for key, owner_list in owners.items()}

    for loop in loops:
        u0, v0 = loop[0], loop[1]
        neighbor_index, _ = owners[_edge_key(u0, v0)][0]
        neighbor_normal = _face_normal(vertices, faces[neighbor_index])

        probe_centroid_index = len(new_vertices)
        new_vertices.append(_polygon_centroid(vertices, loop))
        candidate_normal = _face_normal(new_vertices, [v0, u0, probe_centroid_index])
        flip = _dot(candidate_normal, neighbor_normal) < 0
        del new_vertices[probe_centroid_index]  # solo era para decidir el sentido

        result = _delaunay_fill(new_vertices, loop, flip, owner_count)
        if result is not None:
            interior_points, fill_faces = result
            new_vertices.extend(interior_points)
        else:
            fill_faces = _ear_clip(new_vertices, loop, flip, owner_count)
        new_faces.extend(fill_faces)

    return new_vertices, new_faces, len(loops)
