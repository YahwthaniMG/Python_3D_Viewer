"""Orquestación de la aplicación (ex Controller.py).

A diferencia de la versión original, no lanza procesos ni ventanas en
paralelo: `MeshViewer` corre en el proceso principal y gestiona las 3
variantes desde una sola ventana.
"""

import os

from .viewer import MeshViewer


def run(obj_file_path: str) -> None:
    if not os.path.isfile(obj_file_path):
        raise FileNotFoundError(f"No se encontró el archivo OBJ: {obj_file_path}")

    viewer = MeshViewer(obj_file_path)
    viewer.show()
