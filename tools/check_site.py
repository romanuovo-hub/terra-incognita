#!/usr/bin/env python3
"""Проверка пакета сайта перед публикацией на GitHub Pages.

Запуск:  python3 tools/check_site.py
Код возврата 0 — всё в порядке, 1 — есть ошибки (они перечислены).
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors: list[str] = []
warnings: list[str] = []
ok = 0


def good(msg: str) -> None:
    global ok
    ok += 1
    print(f"OK   — {msg}")


def bad(msg: str) -> None:
    errors.append(msg)
    print(f"ОШИБКА — {msg}")


def warn(msg: str) -> None:
    warnings.append(msg)
    print(f"ВНИМАНИЕ — {msg}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# 1. Обязательные файлы
required = [
    "index.html", "materials.html", "404.html", ".nojekyll", "README.md",
    "assets/terra-incognita-rules-v48.pdf", "assets/terra-incognita-token-catalog.pdf",
]
for rel in required:
    p = ROOT / rel
    if p.is_file() and (rel == ".nojekyll" or p.stat().st_size > 0):
        good(f"на месте {rel}")
    else:
        bad(f"нет файла {rel} (или он пуст)")

# 2. Игра целиком и нужного вида
game = ROOT / "index.html"
if game.is_file():
    html = game.read_text("utf-8", "replace")
    size = game.stat().st_size
    if 900_000 <= size <= 1_500_000:
        good(f"index.html размером {size} байт — целая сборка")
    else:
        bad(f"index.html неожиданного размера {size} байт (ожидается ≈1 001 172)")
    if "<title>Terra Incognita" in html and "lang=\"ru\"" in html:
        good("index.html — это игра Terra Incognita на русском")
    else:
        bad("index.html не похож на игру (нет заголовка или lang=ru)")
    if html.rstrip().endswith("</html>"):
        good("index.html закрыт корректно (</html> в конце)")
    else:
        bad("index.html обрезан — нет закрывающего </html>")
    if "sha256:" not in html and "local" + "Storage" not in html:
        good("игра не тянет состояние с сервера (localStorage не используется)")

# 3. Никаких внешних ресурсов
external = re.findall(r'(?:src|href)\s*=\s*"(https?:)?//([^"/]+)', html if game.is_file() else "")
hosts = {h for _, h in external if h not in {"www.w3.org"}}
if hosts:
    bad(f"внешние ресурсы в игре: {', '.join(sorted(hosts))}")
else:
    good("внешних CDN, шрифтов и скриптов нет — сайт работает офлайн")

# 4. Ссылки внутри статических страниц резолвятся
for page in ("materials.html", "404.html"):
    p = ROOT / page
    if not p.is_file():
        continue
    text = p.read_text("utf-8")
    links = re.findall(r'(?:href|src)="([^"#][^"]*)"', text)
    missing = [l for l in links if not l.startswith(("http", "mailto:")) and not (p.parent / l.split("?")[0]).exists()]
    if missing:
        bad(f"{page}: битые ссылки {missing}")
    else:
        good(f"{page}: все локальные ссылки ведут на существующие файлы ({len(links)} шт.)")

# 5. Имена файлов только ASCII (иначе ломаются URL на Pages)
cyr = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*")
       if p.is_file() and ".git" not in p.parts and any(ord(c) > 127 for c in p.as_posix())]
if cyr:
    bad(f"нелатинские имена файлов: {cyr}")
else:
    good("все имена файлов латиницей — URL на Pages будут чистыми")

# 6. Контрольные суммы
sums = ROOT / "SHA256SUMS.txt"
if sums.is_file():
    text = sums.read_text("utf-8")
    expected = {}
    for line in text.splitlines():
        if "  " in line:
            h, rel = line.split("  ", 1)
            expected[rel] = h
    actual = {p.relative_to(ROOT).as_posix(): sha256(p) for p in ROOT.rglob("*")
              if p.is_file() and ".git" not in p.parts and p.name not in {"SHA256SUMS.txt"}}
    mismatch = [r for r in expected if r in actual and expected[r] != actual[r]]
    absent = [r for r in expected if r not in actual]
    extra = [r for r in actual if r not in expected]
    if mismatch or absent:
        bad(f"SHA256SUMS.txt расходится: изменены {mismatch}, отсутствуют {absent}")
    elif extra:
        warn(f"в SHA256SUMS.txt не попали новые файлы: {extra} — запустите tools/make_site.py")
    else:
        good(f"SHA256SUMS.txt совпадает с файлами ({len(expected)} шт.)")
else:
    bad("нет SHA256SUMS.txt — запустите tools/make_site.py")

# 7. Объём и состав
files = [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts]
total = sum(p.stat().st_size for p in files)
if total < 900 * 1024 * 1024:
    good(f"объём пакета {total / 1048576:.1f} МБ — в пределах лимита Pages (1 ГБ)")
else:
    bad(f"пакет слишком тяжёлый: {total / 1048576:.0f} МБ")
big = [p.relative_to(ROOT).as_posix() for p in files if p.stat().st_size > 100 * 1024 * 1024]
if big:
    bad(f"файлы больше 100 МБ Pages не примет: {big}")
else:
    good("ни один файл не превышает лимит GitHub в 100 МБ")

# 8. Мусор в пакете
junk = [p.relative_to(ROOT).as_posix() for p in files
        if p.suffix.lower() in {".zip", ".rar", ".7z"} or p.name.startswith(("~$", ".DS_Store"))]
if junk:
    warn(f"лишние файлы в пакете: {junk}")
else:
    good("архивов и системного мусора нет")

print()
print("ИТОГ:", f"{ok} проверок пройдено, {len(warnings)} предупреждений, {len(errors)} ошибок")
if errors:
    print("Публиковать рано — исправьте ошибки выше.")
    sys.exit(1)
print("Пакет готов к публикации на GitHub Pages.")
