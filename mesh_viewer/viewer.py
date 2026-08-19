"""Visor 3D de mallas con PyVista: una sola ventana con menú de variantes.

Reemplaza las antiguas clases RendererOriginal/Smoothing/EdgeSplit (OpenGL en
modo inmediato, una ventana por variante) y los diálogos de tkinter
(OBJOptions, OBJData). La cámara orbital, el zoom y la iluminación los
resuelve PyVista de fábrica; el rotado por teclado/mouse manual ya no hace
falta.
"""

from dataclasses import dataclass
from enum import Enum

import numpy as np
import pyvista as pv

from . import mesh_ops, obj_io, topology


class Variant(Enum):
    ORIGINAL = "Original"
    SMOOTHING = "Laplacian Smoothing"
    EDGE_SPLIT = "Edge Split"


_EXPORT_SUFFIX = {
    Variant.ORIGINAL: "Original",
    Variant.SMOOTHING: "Suavizado",
    Variant.EDGE_SPLIT: "EdgeSplit",
}

_SOLID_COLORS = {
    "Azul": (0.2, 0.4, 1.0),
    "Rojo": (0.85, 0.2, 0.2),
    "Verde": (0.2, 0.75, 0.3),
    "Amarillo": (0.9, 0.8, 0.1),
    "Gris": (0.6, 0.6, 0.6),
}
_COLOR_BY_COMPONENT = "Por Componente"
_COLOR_MODES = [*_SOLID_COLORS, _COLOR_BY_COMPONENT]


@dataclass
class VariantData:
    vertices: list
    faces: list
    stats: topology.MeshStats


def _points_polydata(vertices):
    return pv.PolyData(np.asarray(vertices, dtype=float))


def _edges_polydata(vertices, edges):
    pd = pv.PolyData()
    pd.points = np.asarray(vertices, dtype=float)
    padded = np.hstack([np.full((len(edges), 1), 2, dtype=np.int64), np.asarray(edges, dtype=np.int64)])
    pd.lines = padded.ravel()
    return pd


def _surface_polydata(vertices, faces):
    padded = np.hstack([np.full((len(faces), 1), 3, dtype=np.int64), np.asarray(faces, dtype=np.int64)])
    return pv.PolyData(np.asarray(vertices, dtype=float), padded.ravel())


def _format_stats(stats: topology.MeshStats) -> str:
    return (
        f"Vertices: {stats.num_vertices}\n"
        f"Poligonos: {stats.num_polygons}\n"
        f"Triangulos_Pol: {stats.num_triangle_polygons}\n"
        f"Aristas_Pol: {stats.num_polygon_edges}\n"
        f"Triangulos: {stats.num_faces}\n"
        f"Aristas_Tri: {stats.num_triangle_edges}\n"
        f"Componentes_Conectados: {stats.num_connected_components}\n"
        f"Genus: {stats.genus}"
    )


class MeshViewer:
    """Ventana única: carga un .obj y permite alternar entre Original,
    Laplacian Smoothing y Edge Split sin volver a parsear el archivo."""

    def __init__(self, obj_file_path):
        self.obj_file_path = obj_file_path
        self._polygon_stats = None
        self._cache: dict[Variant, VariantData] = {}
        self._current_variant = Variant.ORIGINAL
        self._visible = {"vertices": True, "edges": True, "surface": True}
        self._color_mode = "Azul"
        self.plotter = pv.Plotter(title="Python 3D Viewer", window_size=(900, 700))
        self._setup_ui()

    def _get_or_compute(self, variant: Variant) -> VariantData:
        if variant not in self._cache:
            self._cache[variant] = self._compute(variant)
        return self._cache[variant]

    def _compute(self, variant: Variant) -> VariantData:
        if variant is Variant.ORIGINAL:
            vertices, faces, self._polygon_stats = obj_io.load_obj(self.obj_file_path)
        else:
            base = self._get_or_compute(Variant.ORIGINAL)
            if variant is Variant.SMOOTHING:
                vertices = mesh_ops.apply_laplacian_smoothing(base.vertices, base.faces, iterations=1, factor=0.5)
                faces = base.faces
            else:
                vertices, faces = mesh_ops.apply_edge_split(base.vertices, base.faces)

        stats = topology.compute_stats(vertices, faces, self._polygon_stats)
        export_path = obj_io.export_path(self.obj_file_path, _EXPORT_SUFFIX[variant])
        obj_io.write_obj(export_path, vertices, faces)
        print(f"Exportado: {export_path}")
        return VariantData(vertices=vertices, faces=faces, stats=stats)

    def _show_variant(self, variant: Variant):
        self._current_variant = variant
        data = self._get_or_compute(variant)
        edges = topology.triangle_edges(data.faces)

        points_actor = self.plotter.add_points(
            _points_polydata(data.vertices), color="red", point_size=6,
            render_points_as_spheres=True, name="vertices",
        )
        edges_actor = self.plotter.add_mesh(
            _edges_polydata(data.vertices, edges), color="green", line_width=1.5, name="edges",
        )
        points_actor.visibility = self._visible["vertices"]
        edges_actor.visibility = self._visible["edges"]
        self._add_surface_actor(data)

        self.plotter.add_text(
            _format_stats(data.stats), position="upper_left", font_size=10, name="stats_overlay",
        )

    def _add_surface_actor(self, data: VariantData):
        """(Re)crea el actor de superficie con el modo de color actual,
        reemplazando el anterior in-place (mismo `name="surface"`)."""
        surface_pd = _surface_polydata(data.vertices, data.faces)
        if self._color_mode == _COLOR_BY_COMPONENT:
            labels = np.asarray(topology.connected_component_labels(data.faces))
            actor = self.plotter.add_mesh(
                surface_pd, scalars=labels, cmap="tab10", show_scalar_bar=False, name="surface",
            )
        else:
            actor = self.plotter.add_mesh(
                surface_pd, color=_SOLID_COLORS[self._color_mode], name="surface",
            )
        actor.visibility = self._visible["surface"]
        return actor

    def _toggle_visibility(self, key: str, state: bool):
        self._visible[key] = state
        actor = self.plotter.actors.get(key)
        if actor is not None:
            actor.visibility = state

    def _set_color_mode(self, value: str):
        self._color_mode = value
        self._add_surface_actor(self._get_or_compute(self._current_variant))

    def _setup_ui(self):
        self.plotter.add_text(
            "Arrastrar = rotar | Rueda = zoom | 1/2/3 = variante",
            position="upper_right", font_size=8, name="help",
        )

        variant_positions = [(15, 15), (15, 70), (15, 125)]
        variants = [Variant.ORIGINAL, Variant.SMOOTHING, Variant.EDGE_SPLIT]
        for pos, variant in zip(variant_positions, variants):
            self.plotter.add_radio_button_widget(
                lambda v=variant: self._show_variant(v),
                radio_button_group="mesh_variant",
                value=(variant is Variant.ORIGINAL),
                title=variant.value,
                position=pos,
            )

        self.plotter.add_key_event("1", lambda: self._show_variant(Variant.ORIGINAL))
        self.plotter.add_key_event("2", lambda: self._show_variant(Variant.SMOOTHING))
        self.plotter.add_key_event("3", lambda: self._show_variant(Variant.EDGE_SPLIT))

        visibility_positions = [(660, 15), (660, 70), (660, 125)]
        visibility_items = [("vertices", "Vértices"), ("edges", "Aristas"), ("surface", "Superficie")]
        for pos, (key, label) in zip(visibility_positions, visibility_items):
            self.plotter.add_checkbox_button_widget(
                lambda state, k=key: self._toggle_visibility(k, state),
                value=True,
                position=pos,
                size=28,
            )
            self.plotter.add_text(label, position=(pos[0] + 40, pos[1] + 6), font_size=9)

        self.plotter.add_text("Color:", position=(0.32, 0.955), font_size=9, viewport=True)
        self.plotter.add_text_slider_widget(
            self._set_color_mode, data=_COLOR_MODES, value=_COLOR_MODES.index(self._color_mode),
            pointa=(0.4, 0.95), pointb=(0.78, 0.95),
        )

    def show(self):
        self._show_variant(Variant.ORIGINAL)
        self.plotter.reset_camera()
        self.plotter.show()
