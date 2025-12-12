"""
STP → цилиндрический профиль для токарного прототипа.

Попытка использовать pythonocc-core; если недоступен, простой парсер STEP
по CARTESIAN_POINT для оценки bounding box. Для цилиндров этого достаточно.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


try:  # Опционально: полноценное чтение через Open Cascade
    from OCC.Core.BRepBndLib import brepbndlib_Add  # type: ignore
    from OCC.Core.Bnd import Bnd_Box  # type: ignore
    from OCC.Core.IFSelect import IFSelect_RetDone  # type: ignore
    from OCC.Core.STEPControl import STEPControl_Reader  # type: ignore

    HAVE_OCC = True
except Exception:
    HAVE_OCC = False


Point = Tuple[float, float, float]


@dataclass
class CylinderProfile:
    length: float
    diameter: float
    axis: str  # 'x' | 'y' | 'z'
    bbox: Dict[str, float]

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


def _bbox_from_occ(stp_path: Path) -> Tuple[float, float, float, float, float, float]:
    reader = STEPControl_Reader()
    status = reader.ReadFile(str(stp_path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"STEP read failed: {stp_path}")

    reader.TransferRoots()
    shape = reader.Shape()

    bbox = Bnd_Box()
    brepbndlib_Add(shape, bbox, True)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    return xmin, xmax, ymin, ymax, zmin, zmax


def _bbox_from_points(points: Iterable[Point]) -> Tuple[float, float, float, float, float, float]:
    xs, ys, zs = zip(*points)
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


def _parse_points_fallback(step_text: str) -> List[Point]:
    """Простой разбор CARTESIAN_POINT (...) из STEP."""
    pattern = re.compile(
        r"CARTESIAN_POINT\('.*?',\(\s*([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)\s*\)\)",
        re.MULTILINE,
    )
    pts: List[Point] = []
    for m in pattern.finditer(step_text):
        x, y, z = map(float, m.groups())
        pts.append((x, y, z))
    if not pts:
        raise RuntimeError("Не удалось найти CARTESIAN_POINT в STEP (fallback).")
    return pts


def _extents_to_profile(bounds: Tuple[float, float, float, float, float, float]) -> CylinderProfile:
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    dims = {
        "x": xmax - xmin,
        "y": ymax - ymin,
        "z": zmax - zmin,
    }
    axis = max(dims, key=dims.get)  # самая длинная сторона считаем осью
    length = dims[axis]
    radial_dims = [v for k, v in dims.items() if k != axis]
    diameter = max(radial_dims)

    bbox = {
        "xmin": xmin,
        "xmax": xmax,
        "ymin": ymin,
        "ymax": ymax,
        "zmin": zmin,
        "zmax": zmax,
    }
    return CylinderProfile(length=length, diameter=diameter, axis=axis, bbox=bbox)


def stp_to_profile(stp_path: Path) -> CylinderProfile:
    if HAVE_OCC:
        bounds = _bbox_from_occ(stp_path)
        return _extents_to_profile(bounds)

    # Fallback: текстовый парсер STEP
    text = stp_path.read_text(errors="ignore")
    points = _parse_points_fallback(text)
    bounds = _bbox_from_points(points)
    return _extents_to_profile(bounds)


def main() -> None:
    parser = argparse.ArgumentParser(description="STP → профиль цилиндра для токарки.")
    parser.add_argument("stp", type=Path, help="Путь к STP файлу.")
    parser.add_argument("-o", "--out", type=Path, help="Куда сохранить JSON с профилем.")
    args = parser.parse_args()

    profile = stp_to_profile(args.stp)
    if args.out:
        args.out.write_text(profile.to_json())
    else:
        print(profile.to_json())


if __name__ == "__main__":
    main()

