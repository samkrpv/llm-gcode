"""
Простой генератор Fanuc G-code для цилиндра на основе профиля из STP.

Принимает CylinderProfile (длина, диаметр) и выпускает строковый NC.
Цель — быстрый прототип, не промышленные режимы.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

from .stp_to_profile import CylinderProfile, stp_to_profile


@dataclass
class TurnParams:
    rpm: int = 1200
    f_rough: float = 0.20
    f_finish: float = 0.10
    f_face: float = 0.10
    f_part: float = 0.05
    stock_allow: float = 1.0  # припуск на сторону (мм) по диаметру
    finish_allow: float = 0.2  # припуск перед чистовым (мм) по диаметру
    rough_step: float = 1.0  # шаг по диаметру между черновыми проходами
    safe_z: float = 3.0
    cutoff_extra: float = 1.5  # дополнительное смещение по Z для отрезки


def _format(lines: Iterable[str]) -> str:
    return "\n".join(lines) + ("\n" if lines else "")


def _pass_diameters(stock_d: float, finish_d: float, params: TurnParams) -> List[float]:
    diameters: List[float] = []
    d = stock_d
    target = finish_d + params.finish_allow
    while d - params.rough_step > target:
        d -= params.rough_step
        diameters.append(round(d, 3))
    return diameters


def generate_cylinder_nc(profile: CylinderProfile, params: TurnParams = TurnParams()) -> str:
    finish_d = round(profile.diameter, 3)
    stock_d = round(finish_d + params.stock_allow * 2.0, 3)  # припуск на сторону → по диаметру
    start_d = round(stock_d + 2.0, 3)  # небольшой отступ для подачи в холостую
    z_end = -round(profile.length, 3)

    rough_diams = _pass_diameters(stock_d, finish_d, params)
    lines: List[str] = []
    add = lines.append

    # Пролог
    add("%")
    add("O0001")
    add("G21")
    add("G18")
    add("G40")
    add("G80")
    add("G97")

    # Черновая/чистовая одним инструментом T0101
    add("G0T0101")
    add(f"G97S{params.rpm}M03")
    add(f"G0G54X{start_d:.3f}Z{params.safe_z:.3f}M8")

    # Подрезка
    add(f"G99G1Z0.F{params.f_face:.3f}")
    add("X0.")
    add(f"G0X{start_d:.3f}Z{params.safe_z:.3f}")

    # Черновые проходы
    for d in rough_diams:
        add(f"G0X{d:.3f}Z{params.safe_z:.3f}")
        add(f"G1Z{z_end:.3f}F{params.f_rough:.3f}")
        add(f"G0Z{params.safe_z:.3f}")

    # Чистовой проход
    add(f"G0X{finish_d + params.finish_allow:.3f}Z{params.safe_z:.3f}")
    add(f"G1Z{z_end:.3f}F{params.f_finish:.3f}")
    add(f"G1X{finish_d:.3f}")
    add(f"G0Z{params.safe_z:.3f}")
    add("G28U0.V0.W0.M05")
    add("T0100")
    add("M01")

    # Отрезка простым ходом (тем же инструментом, для прототипа)
    add("G0T0303")
    add(f"G97S{params.rpm}M03")
    part_z = z_end - params.cutoff_extra
    add(f"G0G54X{start_d:.3f}Z{part_z:.3f}")
    add(f"G1X-1.0F{params.f_part:.3f}")
    add(f"G0Z{params.safe_z:.3f}")
    add("G28U0.V0.W0.M05")
    add("T0300")
    add("M30")
    add("%")

    return _format(lines)


def pipeline_from_stp(stp_path: Path, params: TurnParams = TurnParams()) -> str:
    profile = stp_to_profile(stp_path)
    return generate_cylinder_nc(profile, params)


def save_nc(nc_text: str, out_path: Path) -> None:
    out_path.write_text(nc_text)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="STP → Fanuc NC (цилиндр).")
    parser.add_argument("stp", type=Path, help="Путь к STP файлу.")
    parser.add_argument("-o", "--out", type=Path, default=None, help="Куда сохранить .NC (stdout если не указано).")
    parser.add_argument("--rpm", type=int, default=TurnParams.rpm)
    parser.add_argument("--f-rough", type=float, default=TurnParams.f_rough)
    parser.add_argument("--f-finish", type=float, default=TurnParams.f_finish)
    parser.add_argument("--f-face", type=float, default=TurnParams.f_face)
    parser.add_argument("--f-part", type=float, default=TurnParams.f_part)
    parser.add_argument("--stock-allow", type=float, default=TurnParams.stock_allow)
    parser.add_argument("--finish-allow", type=float, default=TurnParams.finish_allow)
    parser.add_argument("--rough-step", type=float, default=TurnParams.rough_step)
    parser.add_argument("--safe-z", type=float, default=TurnParams.safe_z)
    parser.add_argument("--cutoff-extra", type=float, default=TurnParams.cutoff_extra)
    args = parser.parse_args()

    params = TurnParams(
        rpm=args.rpm,
        f_rough=args.f_rough,
        f_finish=args.f_finish,
        f_face=args.f_face,
        f_part=args.f_part,
        stock_allow=args.stock_allow,
        finish_allow=args.finish_allow,
        rough_step=args.rough_step,
        safe_z=args.safe_z,
        cutoff_extra=args.cutoff_extra,
    )

    nc = pipeline_from_stp(args.stp, params)
    if args.out:
        save_nc(nc, args.out)
    else:
        print(nc)


if __name__ == "__main__":
    main()

