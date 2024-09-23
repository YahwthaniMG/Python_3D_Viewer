from collections import deque

"""
    Esa clase lee el OBJ, todas las caras que obtiene las convierte a triangulos, utilizando el Fan
    triangulation, crea un arbol, para hacer un bfs, de modo que se obtienen los componentes conectados 
    de la malla, asi como se calcula el genus.
"""

class OBJLoader:
    @staticmethod
    def load_obj(file_path):
        vertices = []
        faces = []
        edges = set()  
        ed = set()
        np = 0
        npt = 0
        
        with open(file_path, 'r') as f:
            for line in f:
                if line.startswith('v '):
                    vertex = list(map(float, line.strip().split()[1:]))
                    vertices.append(vertex)
                elif line.startswith('f '):
                    raw_face = line.strip().split()[1:]
                    face_vertices = [int(vertex.split('/')[0]) - 1 for vertex in raw_face]
                    np += 1
                    
                    num_vertices = len(face_vertices)
                    for i in range(num_vertices):
                        edge = tuple(sorted((face_vertices[i], face_vertices[(i + 1) % num_vertices])))
                        edges.add(edge)
                        ed.add(edge)
                    if num_vertices > 3:
                        for i in range(1, num_vertices - 1):
                            new_edge_1 = tuple(sorted((face_vertices[0], face_vertices[i])))
                            new_edge_2 = tuple(sorted((face_vertices[i], face_vertices[i + 1])))
                            edges.add(new_edge_1)
                            edges.add(new_edge_2)
                            faces.append([face_vertices[0], face_vertices[i], face_vertices[i + 1]])
                    else:
                        npt+=1
                        faces.append(face_vertices)

        nef = len(edges)
        nf = len(faces)
        nv = len(vertices)
        ne = len(ed)
        
        # Calcular el número de componentes conectados
        ncc = OBJLoader.count_connected_components(vertices, faces)
        return vertices, faces, list(ed), nv, nf, ne, np, npt, nef, ncc
    
    @staticmethod
    def count_connected_components(vertices, faces):
        visited = set()
        ncc = 0
        
        # Construir el grafo de caras
        graph = {i: [] for i in range(len(faces))}
        for i, face in enumerate(faces):
            for vertex in face:
                for neighbor_face_index in OBJLoader.find_adjacent_faces(vertex, faces, i):
                    if neighbor_face_index != i:
                        graph[i].append(neighbor_face_index)
        # Recorrer el grafo y contar los componentes conectados
        for vertex_index in range(len(faces)):
            if vertex_index not in visited:
                ncc += 1
                OBJLoader.bfs(vertex_index, graph, visited)
        
        return ncc
    
    @staticmethod
    def find_adjacent_faces(vertex, faces, current_face_index):
        adjacent_faces = []
        for i, face in enumerate(faces):
            if i != current_face_index and vertex in face:
                adjacent_faces.append(i)
        return adjacent_faces
    
    @staticmethod
    def bfs(start_vertex, graph, visited):
        queue = deque([start_vertex])
        visited.add(start_vertex)
        while queue:
            current_vertex = queue.popleft()
            for neighbor_vertex in graph[current_vertex]:
                if neighbor_vertex not in visited:
                    visited.add(neighbor_vertex)
                    queue.append(neighbor_vertex)  
                    
    @staticmethod
    def calculate_genus(vertices, edges, faces):
        num_vertices = len(vertices)
        num_edges = len(edges)
        num_faces = len(faces)

        if num_faces == 0:
            return -1  # El objeto no tiene caras, por lo que no se puede calcular el género
        if num_vertices == 0 or num_edges == 0:
            return -1  # No hay suficientes datos para calcular el género

        euler_characteristic = num_vertices - num_edges + num_faces
        genus = 1 - (euler_characteristic / 2)
        if genus >=0 and genus <=10:
            return genus
        else:
            return -1