"""PNG 角色卡嵌入：V1/V2 `chara` tEXt chunk + V3 `ccv3` tEXt chunk。

事实依据（2026-08-16 抓规范原文核实）：
- Character Card V1/V2（malfoyslastname/spec-v2）：JSON 以 base64 存入 PNG tEXt
  chunk `chara`（spec-v2 继承 V1 嵌入方式）。
- Character Card V3（kwaroran/character-card-spec-v3）：tEXt chunk 必须命名 `ccv3`，
  值为 JSON 字符串的 UTF-8 → base64。
为兼容酒馆（SillyTavern）与 RisuAI，本引擎导出的 PNG 同时写入两个 chunk。
"""
from __future__ import annotations

import base64
import binascii
import json
import struct
import zlib
from pathlib import Path
from typing import Any


# ── PNG 基础 ─────────────────────────────────────────────────────────────────
def _chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)
    )


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _pixel_png() -> bytes:
    """1x1 透明 PNG（无立绘时的兜底承载图）。"""
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)  # 8-bit RGBA
    raw = b"\x00" + b"\x00\x00\x00\x00"
    idat = zlib.compress(raw, 9)
    return PNG_SIGNATURE + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")


def _split_chunks(png: bytes) -> list[tuple[bytes, bytes]]:
    if not png.startswith(PNG_SIGNATURE):
        raise ValueError("不是 PNG 文件（签名不匹配）")
    chunks: list[tuple[bytes, bytes]] = []
    pos = len(PNG_SIGNATURE)
    while pos < len(png):
        length = struct.unpack(">I", png[pos : pos + 4])[0]
        kind = png[pos + 4 : pos + 8]
        data = png[pos + 8 : pos + 8 + length]
        pos += 12 + length
        chunks.append((kind, data))
        if kind == b"IEND":
            break
    return chunks


def _write_png(chunks: list[tuple[bytes, bytes]]) -> bytes:
    out = bytearray(PNG_SIGNATURE)
    for kind, data in chunks:
        out += _chunk(kind, data)
    return bytes(out)


def _text_chunk(keyword: str, text: str) -> tuple[bytes, bytes]:
    raw = keyword.encode("latin-1") + b"\x00" + text.encode("utf-8")
    return b"tEXt", raw


# ── 卡 PNG 读写 ──────────────────────────────────────────────────────────────
def write_card_png(
    card_obj: dict[str, Any] | str,
    out_path: str | Path,
    avatar: str | Path | None = None,
    include_v2: bool = True,
    include_v3: bool = True,
) -> Path:
    """把 V2/V3 卡对象嵌入 PNG（同时写 chara 与 ccv3 chunk）。"""
    obj = json.loads(card_obj) if isinstance(card_obj, str) else card_obj
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if avatar and Path(avatar).exists() and Path(avatar).suffix.lower() == ".png":
        png = Path(avatar).read_bytes()
        try:
            chunks = _split_chunks(png)
        except ValueError:
            chunks = _split_chunks(_pixel_png())
    else:
        chunks = _split_chunks(_pixel_png())

    inserts: list[tuple[bytes, bytes]] = []
    if include_v3 and obj.get("spec") == "chara_card_v3":
        payload = base64.b64encode(json.dumps(obj, ensure_ascii=False).encode("utf-8")).decode("ascii")
        inserts.append(_text_chunk("ccv3", payload))
    if include_v2 and obj.get("spec") == "chara_card_v2":
        payload = base64.b64encode(json.dumps(obj, ensure_ascii=False).encode("utf-8")).decode("ascii")
        inserts.append(_text_chunk("chara", payload))

    rebuilt: list[tuple[bytes, bytes]] = []
    for kind, data in chunks:
        if kind == b"IEND":
            rebuilt.extend(inserts)
        rebuilt.append((kind, data))
    out.write_bytes(_write_png(rebuilt))
    return out


def read_card_png(path: str | Path) -> dict[str, Any]:
    """从 PNG 读取 V3（ccv3 优先）或 V1/V2（chara）卡 JSON。"""
    png = Path(path).read_bytes()
    chunks = _split_chunks(png)
    found: dict[str, bytes] = {}
    for kind, data in chunks:
        if kind == b"tEXt":
            try:
                kw, _, value = data.partition(b"\x00")
                key = kw.decode("latin-1")
                if key in ("chara", "ccv3"):
                    found[key] = value
            except UnicodeDecodeError:
                continue
    for key in ("ccv3", "chara"):
        raw = found.get(key)
        if raw is None:
            continue
        try:
            payload = raw.decode("utf-8")
        except UnicodeDecodeError:
            payload = raw.decode("latin-1")
        if not payload.lstrip().startswith("{"):
            try:
                payload = base64.b64decode(payload).decode("utf-8")
            except Exception:
                continue
        try:
            obj = json.loads(payload)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    raise ValueError(f"PNG 中没有可识别的角色卡 chunk（ccv3/chara）：{path}")
