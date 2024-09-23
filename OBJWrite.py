"""
    Esta clase se encarga de esribir el archivo OBJ, con las nuevas caracteristicas de la malla.
"""

class OBJWriter:
    @staticmethod
    def write_obj(file_path, vertices, faces):
        with open(file_path, 'w') as f:
            f.write("Autor: Yahwthani Morales Gómez\n")
            # Escribir los vértices
            for vertex in vertices:
                f.write(f"v {' '.join(map(str, vertex))}\n")

            # Escribir las caras
            for face in faces:
                f.write("f")
                for vertex_index in face:
                    f.write(f" {vertex_index + 1}")  # Agregar 1 porque los índices en OBJ comienzan desde 1
                f.write("\n")
        print("Listo")