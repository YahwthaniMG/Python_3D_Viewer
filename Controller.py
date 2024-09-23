from OBJLoader import OBJLoader
from RendererOriginal import Renderer
from RendererSmoothing import RendererSmoothing
from RendererEdgeSplit import RendererEdgeSplit
import OBJData
import OBJOptions
import OBJWrite
from multiprocessing import Process, Manager
import sys
import time


"""
    Controller.py
    Se dedica a administar los procesos necesarios para el renderizado y gestion de las decidiones del
    usuario.
    Se importan los demas codigos para leer y escribir OBJ, asi como los codigos encargados de
    renderizar un proceso de local remeshing asignado.
"""

def load_and_render_model_original(obj_file_path, nv, nf, ne, np, npt, nef, ncc, ng):
    obj_loader = OBJLoader()
    vertices, faces, edges, nvs, nfs, nes, nps, npts, nefs, nccs = obj_loader.load_obj(obj_file_path)
    nv.value = nvs
    nf.value = nfs
    np.value = nps
    npt.value = npts
    nef.value = nefs
    ncc.value = nccs
    new_edges = calculate_edges(faces)
    ne.value = len(new_edges)
    ng.value = obj_loader.calculate_genus(vertices,new_edges,faces)
    carpeta, objeto = obj_file_path.split("/")
    objeto, extension = objeto.split(".")
    carpeta="OBJsExport"
    file_path = carpeta + "/" + objeto + "Original." + extension
    print(file_path)
    obj_writer = OBJWrite.OBJWriter()
    obj_writer.write_obj(file_path, vertices, faces)
    renderer = Renderer()
    tam=renderer.calculate_model_size(vertices)
    renderer.render_normal_scene(vertices, faces, new_edges, tam)
    
    

def load_and_render_model_smoothin_laplace(obj_file_path, nv, nf, ne, np, npt, nef, ncc, ng):
    obj_loader = OBJLoader()
    vertices, faces, edges, nvs, nfs, nes, nps, npts, nefs, nccs = obj_loader.load_obj(obj_file_path)
    nv.value = nvs
    nf.value = nfs
    np.value = nps
    npt.value = npts
    nef.value = nefs
    ncc.value = nccs
    
    renderer = RendererSmoothing()
    smooth_vertices=renderer.apply_laplacian_smoothing(vertices, faces, iterations=1, factor=0.5)
    
    new_edges = calculate_edges(faces)
    ne.value = len(new_edges)
    ng.value = obj_loader.calculate_genus(smooth_vertices,new_edges,faces)
    carpeta, objeto = obj_file_path.split("/")
    objeto, extension = objeto.split(".")
    carpeta="OBJsExport"
    file_path = carpeta + "/" + objeto + "Suavizado." + extension
    print(file_path)
    obj_writer = OBJWrite.OBJWriter()
    obj_writer.write_obj(file_path, smooth_vertices, faces)
    tam = renderer.calculate_model_size(smooth_vertices)
    renderer.render_with_smoothing(smooth_vertices, faces, new_edges, tam)

def load_and_render_model_split_edges(obj_file_path, nv, nf, ne, np, npt, nef, ncc, ng):
    obj_loader = OBJLoader()
    vertices, faces, edges, nvs, nfs, nes, nps, npts, nefs, nccs = obj_loader.load_obj(obj_file_path)
    ne.value = nes
    np.value = nps
    npt.value = npts
    nef.value = nefs
    ncc.value = nccs
    
    renderer = RendererEdgeSplit()
    new_vertices, new_faces =renderer.apply_edge_split(vertices, faces)
    
    nv.value = len(new_vertices)
    nf.value = len(new_faces)
    new_edges = calculate_edges(new_faces)
    ne.value = len(new_edges)
    ng.value = obj_loader.calculate_genus(new_vertices,new_edges,new_faces)
    carpeta, objeto = obj_file_path.split("/")
    objeto, extension = objeto.split(".")
    carpeta="OBJsExport"
    file_path = carpeta + "/" + objeto + "EdgeSplit." + extension
    print(file_path)
    obj_writer = OBJWrite.OBJWriter()
    obj_writer.write_obj(file_path, new_vertices, new_faces)
    tam = renderer.calculate_model_size(new_vertices)
    renderer.render_with_edge_split(new_vertices, new_faces, new_edges, tam)

def calculate_edges(faces):
    edges = set()
    for face in faces:
        for i in range(len(face)):
            edge = (face[i], face[(i + 1) % len(face)])
            edges.add(tuple(sorted(edge)))  # Ordenamos para evitar duplicados de aristas
    return list(edges)

def nvnf(obj_file_path, nv, nf, ne, np, npt, nef, ncc, ng):
    obj_loader = OBJLoader()
    vertices, faces, edges, nvs, nfs, nes, nps, npts, nefs, nccs = obj_loader.load_obj(obj_file_path)
    nv.value = nvs
    nf.value = nfs
    ne.value = nes
    np.value = nps
    npt.value = npts
    nef.value = nefs
    ncc.value = nccs
    new_edges = calculate_edges(faces)
    ng.value = obj_loader.calculate_genus(vertices,new_edges,faces)
    viewer = OBJData.MeshDataViewer()
    viewer.display_data(nv.value, nf.value, ne.value, np.value, npt.value, nef.value, ncc.value, ng.value)

def nvnf1(obj_file_path, nv, nf, ne, np, npt, nef, ncc, ng):
    obj_loader = OBJLoader()
    vertices, faces, edges, nvs, nfs, nes, nps, npts, nefs, nccs = obj_loader.load_obj(obj_file_path)
    nv.value = nvs
    nf.value = nfs
    np.value = nps
    npt.value = npts
    nef.value = nefs
    ncc.value = nccs
    
    renderer = RendererSmoothing()
    smooth_vertices=renderer.apply_laplacian_smoothing(vertices, faces, iterations=1, factor=0.5)
    
    new_edges = calculate_edges(faces)
    ne.value = len(new_edges)
    ng.value = obj_loader.calculate_genus(vertices,new_edges,faces)
    
    viewer = OBJData.MeshDataViewer()
    viewer.display_data(nv.value, nf.value, ne.value, np.value, npt.value, nef.value, ncc.value, ng.value)

def nvnf2(obj_file_path, nv, nf, ne, np, npt, nef, ncc, ng):
    obj_loader = OBJLoader()
    vertices, faces, edges, nvs, nfs, nes, nps, npts, nefs, nccs = obj_loader.load_obj(obj_file_path)
    ne.value = nes
    np.value = nps
    npt.value = npts
    nef.value = nefs
    ncc.value = nccs
    
    renderer = RendererEdgeSplit()
    new_vertices, new_faces =renderer.apply_edge_split(vertices, faces)
    
    nv.value = len(new_vertices)
    nf.value = len(new_faces)
    new_edges = calculate_edges(new_faces)
    new_edges2 = calculate_edges(faces)
    ne.value = len(new_edges)
    ng.value = obj_loader.calculate_genus(vertices,new_edges2,faces)
    
    viewer = OBJData.MeshDataViewer()
    viewer.display_data(nv.value, nf.value, ne.value, np.value, npt.value, nef.value, ncc.value, ng.value)

def OBJOpt(opt1,opt2, obj_file_path, nv, nf, ne, np, npt, nef, ncc, ng):
    time.sleep(18)
    options = OBJOptions.MeshObjOptions()
    options.display_data(opt1,opt2)
    selected_option = options.get_selected_option()
    # 1==Smoothing 2==Split
    if selected_option == 1:
        smooth = Process(target=load_and_render_model_smoothin_laplace, args=(obj_file_path, nv, nf, ne, np, npt, nef, ncc, ng))
        dates= Process(target=nvnf1, args=(obj_file_path, nv, nf, ne, np, npt, nef, ncc, ng))
        smooth.start()
        dates.start()
        smooth.join()
        dates.join()
    elif selected_option == 2:
        split = Process(target=load_and_render_model_split_edges, args=(obj_file_path, nv, nf, ne, np, npt, nef, ncc, ng))
        dates= Process(target=nvnf2, args=(obj_file_path, nv, nf, ne, np, npt, nef, ncc, ng))
        split.start()
        dates.start()
        split.join()
        dates.join()

if __name__ == "__main__":
    manager = Manager()
    nv = manager.Value('i', 0)  
    nf = manager.Value('i', 0)
    ne = manager.Value('i', 0)
    np = manager.Value('i', 0)
    npt = manager.Value('i', 0)
    nef = manager.Value('i', 0)
    ncc = manager.Value('i', 0)
    ng = manager.Value('i', 0)
    
    #obj_file_path = "OBJs/Car.obj"  
    #obj_file_path = "OBJs/C1018292A.obj"
    #obj_file_path= "OBJs/Gotenks_Budokai_3.obj"
    #obj_file_path= "OBJs/pumpkin.obj"
    obj_file_path = "OBJs/cup.obj"
    #obj_file_path = "OBJs/Bunny.obj"
    #obj_file_path = "OBJs/Heart.obj"
    
    # Crear procesos para cada renderizador
    process_original = Process(target=load_and_render_model_original, args=(obj_file_path, nv, nf, ne, np, npt, nef, ncc, ng))
    ps = Process(target=nvnf, args=(obj_file_path, nv, nf, ne, np, npt, nef, ncc, ng))
    opts = Process(target=OBJOpt, args=("Laplacian Smoothing","Edge Split", obj_file_path, nv, nf, ne, np, npt, nef, ncc, ng))
    
    
    
    # Iniciar proceso original
    process_original.start()
    ps.start()
    opts.start()
    
    process_original.join()
    ps.join()
    opts.join()
    