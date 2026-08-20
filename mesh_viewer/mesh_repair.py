"""Herramientas de reparación de malla: soldadura de vértices, orientación
consistente de triángulos y relleno de huecos.

A diferencia de mesh_ops.py (que genera variantes académicas de la malla),
estos algoritmos arreglan defectos comunes de mallas escaneadas/exportadas.
"""

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


def fill_holes(vertices, faces):
    """Rellena cada hueco triangulándolo por ear clipping (ver _ear_clip),
    que sigue la forma real del contorno en vez de un abanico desde un
    único centroide (que en huecos grandes o alargados deja triángulos
    enormes y mal formados comparados con el resto de la malla).

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

        fill_faces = _ear_clip(new_vertices, loop, flip, owner_count)
        new_faces.extend(fill_faces)

    return new_vertices, new_faces, len(loops)
