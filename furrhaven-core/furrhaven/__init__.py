"""Furrhaven Toolbox — multi-platform role-card authoring engine.

L1 核心引擎：纯 Python + 标准库 + PyYAML，不依赖 DSH。
CLI 入口：`fh`（见 cli.py）。
"""

__version__ = "1.1.0"
ENGINE_NAME = "furrhaven-core"

IR_SCHEMA_VERSION = "1.0"
PLATFORMS_SCHEMA_VERSION = "1.0"

SUPPORTED_PLATFORMS = ("fd", "fc", "fb", "st", "risu", "leinao")
SUPPORTED_CARD_TYPES = ("character", "character.activity", "simulator", "bigworld", "custom")
