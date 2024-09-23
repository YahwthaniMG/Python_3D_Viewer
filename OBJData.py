import tkinter as tk

"""
    Esta clase se dedica a mostar los datos generales del OBJ, como vertices, aristas, 
    caras y componentes conectados.
"""

class MeshDataViewer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Datos del OBJ")
        self.root.geometry('250x250') 
        
        self.label_vertices = tk.Label(self.root, text="Vértices: ", anchor="w")
        self.label_space = tk.Label(self.root, text=" ", anchor="w")
        self.label_polygons = tk.Label(self.root, text="Poligonos: ", anchor="w")
        self.label_polygons_triangle = tk.Label(self.root, text="Triangulos_Pol:", anchor="w")
        self.label_edges = tk.Label(self.root, text="Aristas_Pol: ", anchor="w")
        self.label_space2 = tk.Label(self.root, text=" ", anchor="w")
        self.label_triangle = tk.Label(self.root, text="Triangulos: ", anchor="w")
        self.label_edges_triangle = tk.Label(self.root, text="Aristas_Tri: ", anchor="w")
        self.label_space3 = tk.Label(self.root, text=" ", anchor="w")
        self.label_connected_component = tk.Label(self.root, text="Componentes_Conectados: ", anchor="w")
        self.label_genus = tk.Label(self.root, text="Genus: ", anchor="w")
        
        self.label_vertices.pack(fill='x')  
        self.label_space.pack(fill='x')
        self.label_polygons.pack(fill='x') 
        self.label_polygons_triangle.pack(fill='x')   
        self.label_edges.pack(fill='x') 
        self.label_space2.pack(fill='x')
        self.label_triangle.pack(fill='x')    
        self.label_edges_triangle.pack(fill='x') 
        self.label_space3.pack(fill='x') 
        self.label_connected_component.pack(fill='x')
        self.label_genus.pack(fill='x')
        
    def display_data(self, num_vertices, num_triangle, num_edges, num_polygons,num_polygons_triangle , num_edges_triangle, num_connected_component, num_genus):
        self.label_vertices.config(text=f"Vértices: {num_vertices}")
        self.label_space.config(text=" ")
        self.label_polygons.config(text=f"Poligonos: {num_polygons}")
        self.label_polygons_triangle.config(text=f"Traingulos_Pol: {num_polygons_triangle}")
        self.label_edges.config(text=f"Aristas_Pol: {num_edges}")
        self.label_space2.config(text=" ")
        self.label_triangle.config(text=f"Triangulos: {num_triangle}")
        self.label_edges_triangle.config(text=f"Aristas_Tri: {num_edges_triangle}")
        self.label_space3.config(text=" ")
        self.label_connected_component.config(text=f"Componentes_Conectados: {num_connected_component}")
        self.label_genus.config(text=f"Genus: {num_genus}")
        
        self.root.mainloop()
