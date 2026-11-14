#!/usr/bin/env python3
"""Собирает пакет сайта GitHub Pages из проверенной standalone-сборки игры.

Что делает:
  1. Копирует игру как index.html (байт в байт, без правок).
  2. Кладёт PDF-материалы в assets/ под ASCII-именами.
  3. Рисует favicon.ico (браузер запрашивает его сам, правки HTML не нужны).
  4. Пишет SHA256SUMS.txt и печатает итоговую сводку.

Запуск:  python3 tools/make_site.py [--source /path/to/Terra_Incognita_22 4.html]
По умолчанию источник — /home/user/uploads/Terra_Incognita_22 4.html
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # .../terra-incognita-site
UPLOADS = Path("/home/user/uploads")

GAME_SRC = UPLOADS / "Terra_Incognita_22 4.html"
RULES_PDF = UPLOADS / "ПравилаRA_INCOGNITA_PRAVILA_v46_s_illyustratsiyami.pdf"
CATALOG_PDF = UPLOADS / "Каталог лого.pdf"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def copy(src: Path, dst: Path) -> None:
    if not src.exists():
        sys.exit(f"НЕТ ИСХОДНИКА: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    print(f"  {src.name} -> {dst.relative_to(ROOT)}  ({dst.stat().st_size} байт)")


def make_favicon() -> None:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("  ! Pillow не установлен — favicon.ico пропущен (сайт работает и без него)")
        return

    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    dark, cream, red = (20, 17, 14, 255), (239, 228, 200, 255), (190, 65, 49, 255)

    d.ellipse((4, 4, size - 4, size - 4), fill=dark, outline=cream, width=6)
    d.ellipse((26, 26, size - 26, size - 26), outline=cream, width=2)
    # четырёхлучевая роза ветров
    cx = cy = size / 2
    d.polygon([(cx, 44), (cx + 20, cy - 20), (cx + 92, cy), (cx + 20, cy + 20)], fill=cream)
    d.polygon([(cx, size - 44), (cx - 20, cy + 20), (cx - 92, cy), (cx - 20, cy - 20)], fill=cream)
    d.polygon([(cx, 44), (cx - 20, cy - 20), (cx, cy - 6)], fill=red)
    d.polygon([(cx, size - 44), (cx + 20, cy + 20), (cx, cy + 6)], fill=red)
    d.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), fill=dark, outline=cream, width=3)

    out = ROOT / "favicon.ico"
    img.save(out, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"  favicon.ico  ({out.stat().st_size} байт)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=GAME_SRC, help="путь к standalone-сборке игры")
    args = ap.parse_args()

    print("Сборка пакета terra-incognita-site:")
    copy(args.source, ROOT / "index.html")
    copy(RULES_PDF, ROOT / "assets" / "terra-incognita-rules-v48.pdf")
    copy(CATALOG_PDF, ROOT / "assets" / "terra-incognita-token-catalog.pdf")
    make_favicon()

    # .nojekyll обязателен: без него GitHub Pages прогоняет файлы через Jekyll
    (ROOT / ".nojekyll").write_bytes(b"")
    print("  .nojekyll")

    files = sorted(p for p in ROOT.rglob("*")
                   if p.is_file()
                   and p.name != "SHA256SUMS.txt"
                   and ".git" not in p.parts)
    lines = [f"{sha256(p)}  {p.relative_to(ROOT).as_posix()}" for p in files]
    (ROOT / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", "utf-8")

    total = sum(p.stat().st_size for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts)
    print("\nФайлов: %d, суммарно %.1f МБ" % (len(files), total / 1048576))
    print("index.html SHA-256:", sha256(ROOT / "index.html"))
    print("Готово. Проверка: python3 tools/check_site.py")


if __name__ == "__main__":
    main()
