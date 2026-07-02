"""Generación de mallas STL (ball-and-stick) desde moléculas RDKit 3D."""

from __future__ import annotations

import math
from io import StringIO

import trimesh
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath
from rdkit import Chem
from rdkit.Chem import AllChem
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

# Radios de van der Waals (Å) — escala reducida para impresión 3D
VDW_RADIUS: dict[str, float] = {
    "H": 0.25,
    "C": 0.40,
    "N": 0.38,
    "O": 0.36,
    "F": 0.35,
    "P": 0.50,
    "S": 0.48,
    "Cl": 0.50,
    "Br": 0.55,
    "I": 0.60,
}
DEFAULT_RADIUS = 0.40

# Radios y separación por orden de enlace (geometría distinguible en impresión 3D)
BOND_STYLE: dict[str, dict[str, float]] = {
    "SINGLE": {"radius": 0.12, "offset": 0.0, "count": 1},
    "DOUBLE": {"radius": 0.09, "offset": 0.22, "count": 2},
    "TRIPLE": {"radius": 0.08, "offset": 0.20, "count": 3},
    "AROMATIC": {"radius": 0.085, "offset": 0.18, "count": 2},
}
BOND_SHRINK_FACTOR = 0.72  # recorte en extremos para no enterrar el enlace en el átomo

# Etiquetas en STL 3D (ball-and-stick): texto en plano XY, extruido hacia +Z
STL_ATOM_FONT_SIZE = 0.42
STL_ATOM_LABEL_HEIGHT = 0.07
STL_ATOM_TEXT_CORNER_RADIUS = 0.015


def _cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _normalize(v: tuple[float, float, float]) -> tuple[float, float, float]:
    length = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    if length < 1e-12:
        return (0.0, 0.0, 1.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def _triangle_normal(
    v0: tuple[float, float, float],
    v1: tuple[float, float, float],
    v2: tuple[float, float, float],
) -> tuple[float, float, float]:
    u = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
    w = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])
    return _normalize(_cross(u, w))


def _write_facet(
    buf: StringIO,
    v0: tuple[float, float, float],
    v1: tuple[float, float, float],
    v2: tuple[float, float, float],
) -> None:
    n = _triangle_normal(v0, v1, v2)
    buf.write(
        f"  facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}\n"
        "    outer loop\n"
    )
    for v in (v0, v1, v2):
        buf.write(f"      vertex {v[0]:.6e} {v[1]:.6e} {v[2]:.6e}\n")
    buf.write("    endloop\n  endfacet\n")


def _sphere_mesh(
    center: tuple[float, float, float],
    radius: float,
    lat_steps: int = 10,
    lon_steps: int = 16,
) -> list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]]:
    cx, cy, cz = center
    triangles: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]] = []

    for i in range(lat_steps):
        theta0 = math.pi * i / lat_steps
        theta1 = math.pi * (i + 1) / lat_steps
        for j in range(lon_steps):
            phi0 = 2 * math.pi * j / lon_steps
            phi1 = 2 * math.pi * (j + 1) / lon_steps

            def sph(theta: float, phi: float) -> tuple[float, float, float]:
                x = cx + radius * math.sin(theta) * math.cos(phi)
                y = cy + radius * math.sin(theta) * math.sin(phi)
                z = cz + radius * math.cos(theta)
                return (x, y, z)

            v00 = sph(theta0, phi0)
            v01 = sph(theta0, phi1)
            v10 = sph(theta1, phi0)
            v11 = sph(theta1, phi1)

            if i > 0:
                triangles.append((v00, v10, v01))
            if i < lat_steps - 1:
                triangles.append((v01, v10, v11))

    return triangles


def _add(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
    scale: float = 1.0,
) -> tuple[float, float, float]:
    return (a[0] + scale * b[0], a[1] + scale * b[1], a[2] + scale * b[2])


def _scale(v: tuple[float, float, float], s: float) -> tuple[float, float, float]:
    return (v[0] * s, v[1] * s, v[2] * s)


def _distance(p1: tuple[float, float, float], p2: tuple[float, float, float]) -> float:
    return math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2 + (p2[2] - p1[2]) ** 2)


def _perpendicular_basis(
    p1: tuple[float, float, float],
    p2: tuple[float, float, float],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    axis = _normalize((p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]))
    ref = (1.0, 0.0, 0.0) if abs(axis[0]) < 0.9 else (0.0, 1.0, 0.0)
    u = _normalize(_cross(axis, ref))
    v = _normalize(_cross(axis, u))
    return u, v


def _trim_bond_ends(
    p1: tuple[float, float, float],
    p2: tuple[float, float, float],
    r1: float,
    r2: float,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Acorta el cilindro para que empiece/termine en la superficie del átomo."""
    axis = _normalize((p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]))
    shrink1 = r1 * BOND_SHRINK_FACTOR
    shrink2 = r2 * BOND_SHRINK_FACTOR
    length = _distance(p1, p2)
    min_len = 0.08
    if length <= shrink1 + shrink2 + min_len:
        mid = (
            (p1[0] + p2[0]) / 2,
            (p1[1] + p2[1]) / 2,
            (p1[2] + p2[2]) / 2,
        )
        half = min_len / 2
        return _add(mid, axis, -half), _add(mid, axis, half)
    return _add(p1, axis, shrink1), _add(p2, axis, -shrink2)


def _cylinder_mesh(
    p1: tuple[float, float, float],
    p2: tuple[float, float, float],
    radius: float,
    segments: int = 10,
) -> list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]]:
    u, v = _perpendicular_basis(p1, p2)

    def ring_point(base: tuple[float, float, float], angle: float) -> tuple[float, float, float]:
        ca, sa = math.cos(angle), math.sin(angle)
        return (
            base[0] + radius * (ca * u[0] + sa * v[0]),
            base[1] + radius * (ca * u[1] + sa * v[1]),
            base[2] + radius * (ca * u[2] + sa * v[2]),
        )

    triangles: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]] = []
    for i in range(segments):
        a0 = 2 * math.pi * i / segments
        a1 = 2 * math.pi * (i + 1) / segments
        b0 = ring_point(p1, a0)
        b1 = ring_point(p1, a1)
        t0 = ring_point(p2, a0)
        t1 = ring_point(p2, a1)
        triangles.append((b0, t0, b1))
        triangles.append((b1, t0, t1))

    return triangles


def _bond_type_key(bond: Chem.Bond) -> str:
    bt = bond.GetBondType()
    if bt == Chem.rdchem.BondType.DOUBLE:
        return "DOUBLE"
    if bt == Chem.rdchem.BondType.TRIPLE:
        return "TRIPLE"
    if bt == Chem.rdchem.BondType.AROMATIC:
        return "AROMATIC"
    return "SINGLE"


def _bond_meshes(
    p1: tuple[float, float, float],
    p2: tuple[float, float, float],
    bond: Chem.Bond,
    r1: float,
    r2: float,
) -> list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]]:
    """Genera malla según orden de enlace: 1, 2 o 3 cilindros paralelos."""
    style = BOND_STYLE[_bond_type_key(bond)]
    p_start, p_end = _trim_bond_ends(p1, p2, r1, r2)
    radius = style["radius"]
    offset = style["offset"]
    count = int(style["count"])

    if count == 1:
        return _cylinder_mesh(p_start, p_end, radius)

    u, _ = _perpendicular_basis(p_start, p_end)
    meshes: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]] = []

    if count == 2:
        half = offset / 2
        for sign in (+1.0, -1.0):
            shift = _scale(u, sign * half)
            meshes.extend(_cylinder_mesh(_add(p_start, shift), _add(p_end, shift), radius))
        return meshes

    # Triple: cilindro central + dos laterales
    center_radius = radius * 0.85
    meshes.extend(_cylinder_mesh(p_start, p_end, center_radius))
    half = offset / 2
    for sign in (+1.0, -1.0):
        shift = _scale(u, sign * half)
        meshes.extend(_cylinder_mesh(_add(p_start, shift), _add(p_end, shift), radius))
    return meshes


def _embed_3d(mol: Chem.Mol) -> Chem.Mol | None:
    mol = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    params.randomSeed = 42
    if AllChem.EmbedMolecule(mol, params) != 0:
        if AllChem.EmbedMolecule(mol, AllChem.ETKDG()) != 0:
            return None
    AllChem.MMFFOptimizeMolecule(mol, maxIters=500)
    return mol


def mol_to_stl(mol: Chem.Mol, title: str = "molecule") -> str | None:
    """Convierte una molécula RDKit con conformador 3D a STL ASCII."""
    if mol.GetNumConformers() == 0:
        mol = _embed_3d(mol)
        if mol is None:
            return None

    heavy = Chem.RemoveHs(mol)
    conf_h = heavy.GetConformer()

    triangles: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]] = []

    for atom in heavy.GetAtoms():
        idx = atom.GetIdx()
        pos = conf_h.GetAtomPosition(idx)
        center = (pos.x, pos.y, pos.z)
        radius = VDW_RADIUS.get(atom.GetSymbol(), DEFAULT_RADIUS)
        triangles.extend(_sphere_mesh(center, radius))

    for bond in heavy.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        pi = conf_h.GetAtomPosition(i)
        pj = conf_h.GetAtomPosition(j)
        p1 = (pi.x, pi.y, pi.z)
        p2 = (pj.x, pj.y, pj.z)
        sym_i = heavy.GetAtomWithIdx(i).GetSymbol()
        sym_j = heavy.GetAtomWithIdx(j).GetSymbol()
        r_i = VDW_RADIUS.get(sym_i, DEFAULT_RADIUS)
        r_j = VDW_RADIUS.get(sym_j, DEFAULT_RADIUS)
        triangles.extend(_bond_meshes(p1, p2, bond, r_i, r_j))

    for atom in heavy.GetAtoms():
        idx = atom.GetIdx()
        pos = conf_h.GetAtomPosition(idx)
        radius = VDW_RADIUS.get(atom.GetSymbol(), DEFAULT_RADIUS)
        symbol = atom.GetSymbol()
        label_font = _fit_text_font_size(
            symbol,
            max_width=radius * 1.55,
            max_height=radius * 1.35,
            base_size=STL_ATOM_FONT_SIZE,
            weight="bold",
        )
        # Símbolo en la cúpula del átomo, legible desde +Z (plano XY, extrusión +Z)
        label_z = pos.z + radius - STL_ATOM_LABEL_HEIGHT * 0.35
        triangles.extend(
            _extruded_text_triangles(
                symbol,
                pos.x,
                pos.y,
                label_z,
                STL_ATOM_LABEL_HEIGHT,
                label_font,
                weight="bold",
                corner_radius=STL_ATOM_TEXT_CORNER_RADIUS,
            )
        )

    buf = StringIO()
    buf.write(f"solid {title}\n")
    for t in triangles:
        _write_facet(buf, t[0], t[1], t[2])
    buf.write("endsolid\n")
    return buf.getvalue()


def smiles_to_stl(smiles: str, title: str = "molecule") -> str | None:
    """Genera STL ball-and-stick desde un SMILES."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return mol_to_stl(mol, title=title)


# --- STL llavero: ball-and-stick plano + placa con nombre --------------------

KEYCHAIN_TARGET_WIDTH = 32.0
KEYCHAIN_ATOM_RADIUS = 1.15
KEYCHAIN_PLATE_MARGIN = 0.9
KEYCHAIN_PLATE_MOL_MARGIN = 0.85
KEYCHAIN_PLATE_SMOOTH_BUFFER = 0.55
KEYCHAIN_NAME_BAND_MARGIN_X = 0.85
KEYCHAIN_NAME_BAND_MARGIN_Y = 0.75
# Radio máx. de esquinas en placas no-estadio; la franja del nombre usa estadio (semicírculos = mitad de altura)
KEYCHAIN_NAME_PLATE_CORNER_RADIUS = 2.4
KEYCHAIN_PLATE_THICKNESS = 1.6
KEYCHAIN_NAME_BAND_HEIGHT = 5.8
KEYCHAIN_MOL_NAME_GAP = 0.65
# Distancia desde la cara superior de la placa hasta el punto más bajo de los átomos (mm)
KEYCHAIN_MOL_HEIGHT_ABOVE_PLATE = -0.6
KEYCHAIN_TEXT_HEIGHT = 0.65
KEYCHAIN_TEXT_CORNER_RADIUS = 0.16
KEYCHAIN_ATOM_TEXT_CORNER_RADIUS = 0.07
KEYCHAIN_ATOM_LABEL_HEIGHT = 0.28
KEYCHAIN_NAME_FONT_SIZE = 5.2
KEYCHAIN_ATOM_FONT_SIZE = 1.55
KEYCHAIN_KEYRING_OUTER = 3.0
KEYCHAIN_KEYRING_INNER = 1.1   # radio del agujero (no diámetro); dejar ~1 mm de pared mínima
KEYCHAIN_RING_MIN_WALL = 1.0
KEYCHAIN_RING_PAD_EXTRA = 1.0
KEYCHAIN_RING_TAB_WIDTH = 5.0
KEYCHAIN_RING_FLARE_RADIUS = 3.4
KEYCHAIN_RING_OVERLAP = 2.2
# Lado del aro respecto a la placa: "top" | "bottom" | "left" | "right"
KEYCHAIN_KEYRING_SIDE = "top"

# Enlaces más gruesos y con separación visible (doble/triple) en impresión
KEYCHAIN_BOND_STYLE: dict[str, dict[str, float]] = {
    "SINGLE": {"radius": 0.30, "offset": 0.0, "count": 1},
    "DOUBLE": {"radius": 0.24, "offset": 0.62, "count": 2},
    "TRIPLE": {"radius": 0.22, "offset": 0.58, "count": 3},
    "AROMATIC": {"radius": 0.23, "offset": 0.55, "count": 2},
}

_TEXT_FONT = FontProperties(family="DejaVu Sans", weight="bold")


def _triangles_to_stl(
    triangles: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]],
    title: str,
) -> str:
    buf = StringIO()
    buf.write(f"solid {title}\n")
    for t in triangles:
        _write_facet(buf, t[0], t[1], t[2])
    buf.write("endsolid\n")
    return buf.getvalue()


def _extruded_box(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    z0: float,
    z1: float,
) -> list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]]:
    corners_bot = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)]
    corners_top = [(x, y, z1) for x, y, _ in corners_bot]

    def quad(a, b, c, d):
        return [(a, b, c), (a, c, d)]

    tris: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]] = []
    tris.extend(quad(corners_bot[0], corners_bot[1], corners_bot[2], corners_bot[3]))
    tris.extend(quad(corners_top[0], corners_top[3], corners_top[2], corners_top[1]))
    for i in range(4):
        j = (i + 1) % 4
        tris.extend(quad(corners_bot[i], corners_bot[j], corners_top[j], corners_top[i]))
    return tris


def _annulus_mesh(
    cx: float,
    cy: float,
    outer_r: float,
    inner_r: float,
    z0: float,
    z1: float,
    segments: int = 24,
) -> list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]]:
    triangles: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]] = []
    for i in range(segments):
        a0 = 2 * math.pi * i / segments
        a1 = 2 * math.pi * (i + 1) / segments
        ob0 = (cx + outer_r * math.cos(a0), cy + outer_r * math.sin(a0), z0)
        ob1 = (cx + outer_r * math.cos(a1), cy + outer_r * math.sin(a1), z0)
        ib0 = (cx + inner_r * math.cos(a0), cy + inner_r * math.sin(a0), z0)
        ib1 = (cx + inner_r * math.cos(a1), cy + inner_r * math.sin(a1), z0)
        ot0 = (ob0[0], ob0[1], z1)
        ot1 = (ob1[0], ob1[1], z1)
        it0 = (ib0[0], ib0[1], z1)
        it1 = (ib1[0], ib1[1], z1)

        triangles.append((ob0, ib0, ob1))
        triangles.append((ob1, ib0, ib1))
        triangles.append((ot0, ot1, it0))
        triangles.append((ot1, it1, it0))
        triangles.append((ob0, ob1, ot0))
        triangles.append((ob1, ot1, ot0))
        triangles.append((ib0, it0, ib1))
        triangles.append((ib1, it0, it1))
    return triangles


def _trimesh_to_triangles(mesh: trimesh.Trimesh) -> list[
    tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]
]:
    triangles: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]] = []
    for face in mesh.faces:
        v0, v1, v2 = mesh.vertices[face[0]], mesh.vertices[face[1]], mesh.vertices[face[2]]
        triangles.append((tuple(v0), tuple(v1), tuple(v2)))
    return triangles


def _textpath_polygons_with_holes(polys_raw: list) -> list[Polygon]:
    """Agrupa contornos internos como huecos (O, P, R, B, etc.)."""
    polys = [Polygon(p) for p in polys_raw if len(p) >= 3]
    if not polys:
        return []

    polys.sort(key=lambda p: p.area, reverse=True)
    used: set[int] = set()
    result: list[Polygon] = []

    for i, outer in enumerate(polys):
        if i in used:
            continue
        holes: list[list[tuple[float, float]]] = []
        for j, inner in enumerate(polys):
            if i == j or j in used:
                continue
            if outer.contains(inner.centroid) and inner.area < outer.area:
                holes.append(list(inner.exterior.coords))
                used.add(j)
        used.add(i)
        result.append(Polygon(outer.exterior.coords, holes))

    return result


def _fit_text_font_size(
    text: str,
    max_width: float,
    max_height: float,
    base_size: float,
    *,
    weight: str = "bold",
) -> float:
    prop = FontProperties(family="DejaVu Sans", weight=weight)
    path = TextPath((0.0, 0.0), text, size=base_size, prop=prop)
    bbox = path.get_extents()
    width = max(bbox.x1 - bbox.x0, 1e-6)
    height = max(bbox.y1 - bbox.y0, 1e-6)
    scale = min(max_width / width, max_height / height, 1.0)
    return base_size * scale * 0.92


def _round_polygon_2d(geom: Polygon, radius: float) -> Polygon:
    """Esquinas redondeadas en contornos 2D (exterior e interior)."""
    if radius <= 0 or geom.is_empty:
        return geom
    expanded = geom.buffer(radius, join_style=2)
    return expanded.buffer(-radius * 0.5, join_style=2)


def _extruded_text_triangles(
    text: str,
    center_x: float,
    center_y: float,
    z_base: float,
    height: float,
    font_size: float,
    *,
    weight: str = "bold",
    corner_radius: float = 0.0,
) -> list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]]:
    """Texto continuo extruido (matplotlib TextPath + trimesh), respetando huecos."""
    if not text.strip():
        return []

    prop = FontProperties(family="DejaVu Sans", weight=weight)
    path = TextPath((0.0, 0.0), text, size=font_size, prop=prop)
    parts = _textpath_polygons_with_holes(path.to_polygons())
    if not parts:
        return []

    meshes: list[trimesh.Trimesh] = []
    for geom in parts:
        if geom.is_empty or geom.area < 1e-8:
            continue
        if corner_radius > 0:
            geom = _round_polygon_2d(geom, corner_radius)
            if geom.is_empty or geom.area < 1e-8:
                continue
        meshes.append(trimesh.creation.extrude_polygon(geom, height=height))

    if not meshes:
        return []

    mesh = trimesh.util.concatenate(meshes) if len(meshes) > 1 else meshes[0]
    bbox = path.get_extents()
    mesh.apply_translation((
        center_x - (bbox.x0 + bbox.x1) / 2,
        center_y - (bbox.y0 + bbox.y1) / 2,
        z_base,
    ))
    return _trimesh_to_triangles(mesh)


def _keychain_bond_meshes(
    p1: tuple[float, float, float],
    p2: tuple[float, float, float],
    bond: Chem.Bond,
    r1: float,
    r2: float,
) -> list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]]:
    """Cilindros de enlace gruesos (simple/doble/triple/aromático)."""
    style = KEYCHAIN_BOND_STYLE[_bond_type_key(bond)]
    radius = style["radius"]
    offset = style["offset"]
    count = int(style["count"])
    p_start, p_end = _trim_bond_ends(p1, p2, r1, r2)

    bond_len = _distance(p_start, p_end)
    if count > 1 and bond_len > 1e-6:
        max_sep = bond_len * 0.42
        offset = min(offset, max_sep)

    if count == 1:
        return _cylinder_mesh(p_start, p_end, radius, segments=12)

    u, _ = _perpendicular_basis(p_start, p_end)
    meshes: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]] = []

    if count == 2:
        half = offset / 2
        for sign in (+1.0, -1.0):
            shift = _scale(u, sign * half)
            meshes.extend(_cylinder_mesh(_add(p_start, shift), _add(p_end, shift), radius, segments=12))
        return meshes

    center_radius = radius * 0.88
    meshes.extend(_cylinder_mesh(p_start, p_end, center_radius, segments=12))
    half = offset / 2
    for sign in (+1.0, -1.0):
        shift = _scale(u, sign * half)
        meshes.extend(_cylinder_mesh(_add(p_start, shift), _add(p_end, shift), radius, segments=12))
    return meshes


def _normalize_label(text: str, max_len: int = 18) -> str:
    clean = "".join(c if c.isalnum() or c in "- " else " " for c in text.upper())
    return clean.strip()[:max_len] or "MOL"


def _normalize_keyring_side(side: str | None) -> str:
    key = (side or KEYCHAIN_KEYRING_SIDE).strip().lower()
    aliases = {
        "arriba": "top",
        "abajo": "bottom",
        "izquierda": "left",
        "izq": "left",
        "derecha": "right",
        "der": "right",
    }
    key = aliases.get(key, key)
    if key not in {"top", "bottom", "left", "right"}:
        return KEYCHAIN_KEYRING_SIDE.lower()
    return key


def _extruded_polygon_triangles(
    geom,
    z0: float,
    z1: float,
) -> list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]]:
    """Extruye un polígono shapely 2D entre z0 y z1."""
    if geom is None or geom.is_empty:
        return []

    polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    meshes: list[trimesh.Trimesh] = []
    height = z1 - z0
    for poly in polys:
        if poly.is_empty or poly.area < 1e-8:
            continue
        meshes.append(trimesh.creation.extrude_polygon(poly, height=height))

    if not meshes:
        return []

    mesh = trimesh.util.concatenate(meshes) if len(meshes) > 1 else meshes[0]
    mesh.apply_translation((0.0, 0.0, z0))
    return _trimesh_to_triangles(mesh)


def _capsule_polygon(
    p1: tuple[float, float],
    p2: tuple[float, float],
    width: float,
) -> Polygon:
    line = LineString([p1, p2])
    return line.buffer(width / 2, cap_style=2, join_style=2)


def _stadium_polygon(x0: float, y0: float, x1: float, y1: float) -> Polygon:
    """Píldora horizontal: semicírculos en los extremos (franja de texto)."""
    if x1 <= x0 or y1 <= y0:
        return Polygon()

    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    half_w = (x1 - x0) / 2
    half_h = (y1 - y0) / 2

    if half_w <= half_h + 1e-6:
        return Point(cx, cy).buffer(half_h, join_style=2)

    inner = box(x0 + half_h, y0, x1 - half_h, y1)
    left_cap = Point(x0 + half_h, cy).buffer(half_h, join_style=2)
    right_cap = Point(x1 - half_h, cy).buffer(half_h, join_style=2)
    return unary_union([inner, left_cap, right_cap])


def _rounded_rect_polygon(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    corner_r: float,
    segments: int = 14,
) -> Polygon:
    """Rectángulo con esquinas redondeadas (arcos explícitos)."""
    w, h = x1 - x0, y1 - y0
    if w <= 1e-6 or h <= 1e-6:
        return Polygon()

    # Franjas anchas y bajas → estadio (el truco buffer±r no redondea en ese caso)
    if w > h * 1.6:
        return _stadium_polygon(x0, y0, x1, y1)

    r = min(corner_r, w / 2, h / 2)
    if r <= 1e-6:
        return box(x0, y0, x1, y1)

    pts: list[tuple[float, float]] = []
    arcs = (
        (x0 + r, y0 + r, math.pi, math.pi / 2),
        (x1 - r, y0 + r, 3 * math.pi / 2, math.pi / 2),
        (x1 - r, y1 - r, 0.0, math.pi / 2),
        (x0 + r, y1 - r, math.pi / 2, math.pi / 2),
    )
    for cx, cy, start, sweep in arcs:
        for i in range(segments):
            ang = start + sweep * i / segments
            pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    pts.append(pts[0])
    return Polygon(pts)


def _name_plate_region(
    name_half_w: float,
    name_band_height: float,
    label: str,
    font_size: float,
) -> Polygon:
    """Franja de placa bajo el nombre: contorno curvo ajustado al texto."""
    path = TextPath((0.0, 0.0), label, size=font_size, prop=_TEXT_FONT)
    bbox = path.get_extents()
    text_half_w = (bbox.x1 - bbox.x0) / 2
    text_half_h = (bbox.y1 - bbox.y0) / 2
    name_cy = name_band_height / 2

    half_w = max(name_half_w, text_half_w + KEYCHAIN_NAME_BAND_MARGIN_X)
    half_h = max(
        name_band_height / 2,
        text_half_h + KEYCHAIN_NAME_BAND_MARGIN_Y,
    )
    # Asegurar que la placa cubra desde y=0 hasta la franja del nombre
    y0 = 0.0
    y1 = max(name_band_height, name_cy + half_h)
    x0, x1 = -half_w, half_w

    return _stadium_polygon(x0, y0, x1, y1)


def _build_adaptive_plate_polygon(
    atom_xy: list[tuple[float, float]],
    atom_r: float,
    name_half_w: float,
    name_band_height: float,
    label: str,
    font_size: float,
) -> Polygon:
    """Placa orgánica: franja de nombre con bordes curvos + contorno de la molécula."""
    name_half_w = max(name_half_w + KEYCHAIN_NAME_BAND_MARGIN_X, atom_r + 0.55)
    name_region = _name_plate_region(name_half_w, name_band_height, label, font_size)

    mol_margin = atom_r + KEYCHAIN_PLATE_MOL_MARGIN
    mol_blobs = unary_union([Point(x, y).buffer(mol_margin) for x, y in atom_xy])
    mol_outline = mol_blobs.buffer(
        KEYCHAIN_PLATE_SMOOTH_BUFFER + KEYCHAIN_PLATE_MARGIN,
        join_style=2,
    )

    # La franja del nombre conserva sus esquinas; solo la zona molecular se expande
    combined = unary_union([name_region, mol_outline])
    return combined.simplify(0.04, preserve_topology=True)


def _geom_to_points(geom) -> list[tuple[float, float]]:
    if geom.is_empty:
        return []
    gt = geom.geom_type
    if gt == "Point":
        return [(geom.x, geom.y)]
    if gt == "MultiPoint":
        return [(p.x, p.y) for p in geom.geoms]
    if gt == "LineString":
        return list(geom.coords)
    if gt == "GeometryCollection":
        pts: list[tuple[float, float]] = []
        for part in geom.geoms:
            pts.extend(_geom_to_points(part))
        return pts
    return []


def _plate_boundary_attach(
    plate: Polygon,
    side: str,
    ref_x: float = 0.0,
) -> tuple[float, float]:
    """Punto sobre el borde real de la placa, en la dirección del aro."""
    minx, miny, maxx, maxy = plate.bounds
    ref_y = plate.centroid.y
    coords = [c for c in plate.exterior.coords[:-1]]

    if side == "top":
        ray = LineString([(ref_x, miny - 1.0), (ref_x, maxy + 50.0)])
        pts = _geom_to_points(plate.boundary.intersection(ray))
        if pts:
            return max(pts, key=lambda p: p[1])
    elif side == "bottom":
        ray = LineString([(ref_x, maxy + 1.0), (ref_x, miny - 50.0)])
        pts = _geom_to_points(plate.boundary.intersection(ray))
        if pts:
            return min(pts, key=lambda p: p[1])
    elif side == "left":
        ray = LineString([(maxx + 1.0, ref_y), (minx - 50.0, ref_y)])
        pts = _geom_to_points(plate.boundary.intersection(ray))
        if pts:
            return min(pts, key=lambda p: p[0])
    else:
        ray = LineString([(minx - 1.0, ref_y), (maxx + 50.0, ref_y)])
        pts = _geom_to_points(plate.boundary.intersection(ray))
        if pts:
            return max(pts, key=lambda p: p[0])

    # Respaldo: punto extremo del contorno más cercano al eje de referencia
    if side == "top":
        y_ext = max(c[1] for c in coords)
        band = [c for c in coords if c[1] >= y_ext - 0.25]
        return min(band, key=lambda c: (abs(c[0] - ref_x), -c[1]))
    if side == "bottom":
        y_ext = min(c[1] for c in coords)
        band = [c for c in coords if c[1] <= y_ext + 0.25]
        return min(band, key=lambda c: (abs(c[0] - ref_x), c[1]))
    if side == "left":
        x_ext = min(c[0] for c in coords)
        band = [c for c in coords if c[0] <= x_ext + 0.25]
        return min(band, key=lambda c: (abs(c[1] - ref_y), c[0]))
    x_ext = max(c[0] for c in coords)
    band = [c for c in coords if c[0] >= x_ext - 0.25]
    return min(band, key=lambda c: (abs(c[1] - ref_y), -c[0]))


def _tab_start_inside(attach: tuple[float, float], side: str, inset: float = 1.2) -> tuple[float, float]:
    ax, ay = attach
    if side == "top":
        return ax, ay - inset
    if side == "bottom":
        return ax, ay + inset
    if side == "left":
        return ax + inset, ay
    return ax - inset, ay


def _keyring_radii() -> tuple[float, float]:
    """Radios interior/exterior del aro, con pared mínima imprimible."""
    outer = KEYCHAIN_KEYRING_OUTER
    inner = min(KEYCHAIN_KEYRING_INNER, outer - KEYCHAIN_RING_MIN_WALL)
    inner = max(0.55, inner)
    return inner, outer


def _keyring_center_on_side(
    attach: tuple[float, float],
    side: str,
    outer_r: float,
    overlap: float,
) -> tuple[float, float]:
    ax, ay = attach
    if side == "top":
        return ax, ay + outer_r - overlap
    if side == "bottom":
        return ax, ay - outer_r + overlap
    if side == "left":
        return ax - outer_r + overlap, ay
    return ax + outer_r - overlap, ay


def _build_keyring_plate_union(
    plate: Polygon,
    side: str,
    ref_x: float = 0.0,
) -> tuple[Polygon, tuple[float, float], tuple[float, float]]:
    """Refuerzo curvo + pestaña que une la placa al aro (mayor área de contacto)."""
    attach = _plate_boundary_attach(plate, side, ref_x=ref_x)
    ring_c = _keyring_center_on_side(attach, side, KEYCHAIN_KEYRING_OUTER, KEYCHAIN_RING_OVERLAP)

    ax, ay = attach
    rx, ry = ring_c
    inner_r, outer_r = _keyring_radii()
    tab_start = _tab_start_inside(attach, side)

    if side == "top":
        bridge_y = ry - outer_r * 0.15
        side_off = inner_r + 0.55
        tab_r = _capsule_polygon(
            (ax + side_off, tab_start[1]),
            (rx + side_off, bridge_y),
            KEYCHAIN_RING_TAB_WIDTH,
        )
        tab_l = _capsule_polygon(
            (ax - side_off, tab_start[1]),
            (rx - side_off, bridge_y),
            KEYCHAIN_RING_TAB_WIDTH,
        )
        tab = unary_union([tab_r, tab_l])
    elif side == "bottom":
        bridge_y = ry + outer_r * 0.15
        side_off = inner_r + 0.55
        tab = unary_union([
            _capsule_polygon((ax + side_off, tab_start[1]), (rx + side_off, bridge_y), KEYCHAIN_RING_TAB_WIDTH),
            _capsule_polygon((ax - side_off, tab_start[1]), (rx - side_off, bridge_y), KEYCHAIN_RING_TAB_WIDTH),
        ])
    elif side == "left":
        bridge_x = rx - outer_r * 0.15
        side_off = inner_r + 0.55
        tab = unary_union([
            _capsule_polygon((tab_start[0], ay + side_off), (bridge_x, ry + side_off), KEYCHAIN_RING_TAB_WIDTH),
            _capsule_polygon((tab_start[0], ay - side_off), (bridge_x, ry - side_off), KEYCHAIN_RING_TAB_WIDTH),
        ])
    else:
        bridge_x = rx + outer_r * 0.15
        side_off = inner_r + 0.55
        tab = unary_union([
            _capsule_polygon((tab_start[0], ay + side_off), (bridge_x, ry + side_off), KEYCHAIN_RING_TAB_WIDTH),
            _capsule_polygon((tab_start[0], ay - side_off), (bridge_x, ry - side_off), KEYCHAIN_RING_TAB_WIDTH),
        ])

    inner_hole = Point(rx, ry).buffer(inner_r, join_style=2)
    outer_pad = Point(rx, ry).buffer(outer_r + KEYCHAIN_RING_PAD_EXTRA, join_style=2)
    flare_raw = Point(ax, ay).buffer(KEYCHAIN_RING_FLARE_RADIUS, join_style=2)
    # El refuerzo no debe tapar el hueco del aro
    flare = flare_raw.difference(inner_hole)
    ring_pad = outer_pad.difference(inner_hole)

    plate_cut = plate.difference(inner_hole)
    combined = unary_union([plate_cut, tab, flare, ring_pad])
    combined = combined.difference(inner_hole)
    combined = combined.buffer(0.25, join_style=2).simplify(0.04, preserve_topology=True)
    combined = combined.difference(inner_hole)
    return combined, attach, ring_c


def mol_to_stl_flat_keychain(
    mol: Chem.Mol,
    title: str = "molecule",
    label: str | None = None,
    *,
    mol_height_above_plate: float | None = None,
    keyring_side: str | None = None,
) -> str | None:
    """Llavero: ball-and-stick en plano + placa única (nombre + molécula) + aro arriba."""
    mol = Chem.Mol(mol)
    if AllChem.Compute2DCoords(mol) != 0:
        return None

    heavy = Chem.RemoveHs(mol)
    conf = heavy.GetConformer()
    if heavy.GetNumAtoms() == 0:
        return None

    xs, ys = [], []
    for atom in heavy.GetAtoms():
        pos = conf.GetAtomPosition(atom.GetIdx())
        xs.append(pos.x)
        ys.append(pos.y)

    span = max(max(xs) - min(xs), max(ys) - min(ys), 1e-6)
    scale = KEYCHAIN_TARGET_WIDTH / span
    mid_x = (min(xs) + max(xs)) / 2
    mid_y = (min(ys) + max(ys)) / 2

    def tx(x: float, y: float) -> tuple[float, float]:
        return ((x - mid_x) * scale, -(y - mid_y) * scale)

    scaled: dict[int, tuple[float, float]] = {}
    for atom in heavy.GetAtoms():
        idx = atom.GetIdx()
        pos = conf.GetAtomPosition(idx)
        scaled[idx] = tx(pos.x, pos.y)

    mol_ys = [p[1] for p in scaled.values()]
    mol_min_y = min(mol_ys)

    # Molécula sobre la franja del nombre
    y_shift = (KEYCHAIN_NAME_BAND_HEIGHT + KEYCHAIN_MOL_NAME_GAP) - mol_min_y
    scaled = {k: (x, y + y_shift) for k, (x, y) in scaled.items()}

    display_label = _normalize_label(label or title)
    name_probe = TextPath((0.0, 0.0), display_label, size=KEYCHAIN_NAME_FONT_SIZE, prop=_TEXT_FONT)
    name_bbox = name_probe.get_extents()
    name_half_w = (name_bbox.x1 - name_bbox.x0) / 2

    z_plate_top = KEYCHAIN_PLATE_THICKNESS
    mol_clearance = (
        KEYCHAIN_MOL_HEIGHT_ABOVE_PLATE
        if mol_height_above_plate is None
        else mol_height_above_plate
    )
    z_atom = z_plate_top + mol_clearance + KEYCHAIN_ATOM_RADIUS
    atom_r = KEYCHAIN_ATOM_RADIUS
    ring_side = _normalize_keyring_side(keyring_side)
    triangles: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]] = []

    atom_xy = list(scaled.values())
    plate_poly = _build_adaptive_plate_polygon(
        atom_xy,
        atom_r,
        name_half_w,
        KEYCHAIN_NAME_BAND_HEIGHT,
        display_label,
        KEYCHAIN_NAME_FONT_SIZE,
    )
    plate_poly, _attach, ring_center = _build_keyring_plate_union(plate_poly, ring_side, ref_x=0.0)

    triangles.extend(_extruded_polygon_triangles(plate_poly, 0.0, z_plate_top))

    # Nombre en relieve (parte inferior, conectado a la placa)
    name_cy = KEYCHAIN_NAME_BAND_HEIGHT / 2
    triangles.extend(
        _extruded_text_triangles(
            display_label,
            0.0,
            name_cy,
            z_plate_top,
            KEYCHAIN_TEXT_HEIGHT,
            KEYCHAIN_NAME_FONT_SIZE,
            corner_radius=KEYCHAIN_TEXT_CORNER_RADIUS,
        )
    )

    # Enlaces antes que átomos para mejor visibilidad en slicers
    for bond in heavy.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        x1, y1 = scaled[i]
        x2, y2 = scaled[j]
        p1 = (x1, y1, z_atom)
        p2 = (x2, y2, z_atom)
        triangles.extend(_keychain_bond_meshes(p1, p2, bond, atom_r, atom_r))

    for atom in heavy.GetAtoms():
        idx = atom.GetIdx()
        x, y = scaled[idx]
        triangles.extend(_sphere_mesh((x, y, z_atom), atom_r, lat_steps=8, lon_steps=12))
        symbol = atom.GetSymbol()
        label_font = _fit_text_font_size(
            symbol,
            max_width=atom_r * 1.55,
            max_height=atom_r * 1.35,
            base_size=KEYCHAIN_ATOM_FONT_SIZE,
            weight="bold",
        )
        # Base del relieve en la cúpula del átomo (ligero hundimiento para que no flote)
        label_z = z_atom + atom_r - KEYCHAIN_ATOM_LABEL_HEIGHT * 0.35
        triangles.extend(
            _extruded_text_triangles(
                symbol,
                x,
                y,
                label_z,
                KEYCHAIN_ATOM_LABEL_HEIGHT,
                label_font,
                weight="bold",
                corner_radius=KEYCHAIN_ATOM_TEXT_CORNER_RADIUS,
            )
        )

    # Aro 3D (pared entre radio interior y exterior)
    ring_cx, ring_cy = ring_center
    ring_inner, ring_outer = _keyring_radii()
    triangles.extend(
        _annulus_mesh(
            ring_cx,
            ring_cy,
            ring_outer,
            ring_inner,
            0.0,
            z_plate_top,
        )
    )

    return _triangles_to_stl(triangles, title)


def smiles_to_stl_flat_keychain(
    smiles: str,
    title: str = "molecule",
    label: str | None = None,
    *,
    mol_height_above_plate: float | None = None,
    keyring_side: str | None = None,
) -> str | None:
    """Genera STL de llavero ball-and-stick plano desde un SMILES."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return mol_to_stl_flat_keychain(
        mol,
        title=title,
        label=label or title,
        mol_height_above_plate=mol_height_above_plate,
        keyring_side=keyring_side,
    )
