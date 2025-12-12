"""
CLI: STP → профиль цилиндра → Fanuc NC.

Пример:
  python -m proto.run_pipeline /path/to/model_nc/1/1.stp -o /tmp/out.NC
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .fanuc_lathe import TurnParams, pipeline_from_stp, save_nc


def main() -> None:
    parser = argparse.ArgumentParser(description="STP → Fanuc NC (цилиндр).")
    parser.add_argument("stp", type=Path, help="Путь к STP файлу.")
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=None,
        help="Куда сохранить .NC. Если не указано — файл <stem>_agent.NC рядом со входом.",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Вывести NC в stdout (кроме сохранения файла).",
    )
    parser.add_argument("--rpm", type=int, default=1200)
    parser.add_argument("--f-rough", type=float, default=0.20)
    parser.add_argument("--f-finish", type=float, default=0.10)
    parser.add_argument("--f-face", type=float, default=0.10)
    parser.add_argument("--f-part", type=float, default=0.05)
    parser.add_argument("--stock-allow", type=float, default=1.0)
    parser.add_argument("--finish-allow", type=float, default=0.2)
    parser.add_argument("--rough-step", type=float, default=1.0)
    parser.add_argument("--safe-z", type=float, default=3.0)
    parser.add_argument("--cutoff-extra", type=float, default=1.5)
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
    out_path = args.out or args.stp.with_name(f"{args.stp.stem}_agent.NC")
    save_nc(nc, out_path)
    if args.stdout:
        print(nc)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()

