# -*- coding: utf-8 -*-
"""全局常量管理模块。

集中管理应用所有可调参数与路径规则，便于统一修改与维护。
"""

import os
import sys
from pathlib import Path

# ---- 应用信息 ----
APP_NAME = "ClassRandomSampling"          # 目录名 / 单例标识
APP_TITLE = "班级随机抽取系统"
APP_VERSION = "1.0.0"
ORG_NAME = APP_NAME                       # 用于 QSettings 存储窗口记忆

# ---- 权重规则 ----
DEFAULT_WEIGHT = 1.0        # 默认权重
WEIGHT_STEP = 0.50          # 权重编辑步长
WEIGHT_MIN = 0.0            # 0 = 不参与抽取
WEIGHT_MAX = 999999.0       # 权重上限
WEIGHT_DECIMALS = 2         # 权重显示小数位

# ---- 学号规则 ----
STUDENT_ID_MIN = 1
STUDENT_ID_MAX = 999

# ---- CSV 导入 ----
# 依次尝试的编码，utf-8-sig 兼容带 BOM 的 UTF-8
CSV_ENCODINGS = ("utf-8-sig", "utf-8", "gbk")
# 表头别名 -> 内部字段名（大小写统一为小写后匹配）
CSV_HEADER_ALIASES = {
    "学号": "id", "id": "id", "no": "id", "num": "id", "编号": "id", "序号": "id",
    "姓名": "name", "name": "name", "名字": "name",
    "性别": "sex", "sex": "sex", "gender": "sex",
    "权重": "weight", "weight": "weight", "权值": "weight",
}
CSV_REQUIRED_FIELDS = ("id", "name", "sex")   # 强制字段
CSV_OPTIONAL_FIELDS = ("weight",)             # 可选字段，缺省用默认权重

# ---- 性别归一化 ----
SEX_MALE = {"男", "m", "male", "boy", "man", "1"}
SEX_FEMALE = {"女", "f", "female", "girl", "woman", "0"}
SEX_ALL = "全部"
SEX_MAN = "男"
SEX_WOMAN = "女"

# ---- 抽取 ----
RESULT_BLUE = "#1565C0"     # 抽取结果蓝色字体
RESULT_FONT_PT = 36         # 结果字号

# ---- 日志 ----
LOG_KEEP_DAYS = 7           # 清理旧日志时保留的天数
LOG_DAILY_LIMIT = 500       # 当日超过该条数弹窗提醒
LOG_UI_VISIBLE = 100        # 右侧日志区最多显示条数
LOG_SEQ_WIDTH = 4           # 序号宽度（超过自然扩展，无上限）

# ---- 备份 ----
BACKUP_KEEP = 10            # JSON 自动轮换备份保留份数


def default_data_dir() -> Path:
    """默认数据目录：%APPDATA%\\ClassRandomSampling（可通过 --data-dir 覆盖）。"""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home())
        return Path(base) / APP_NAME
    return Path.home() / ("." + APP_NAME.lower())


def format_weight_short(value: float) -> str:
    """大权重简写：>=1e6 -> M，>=1e3 -> k，其余原样。"""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "0"
    if v >= 1_000_000:
        return f"{v / 1_000_000:.1f}M"
    if v >= 1_000:
        return f"{v / 1_000:.1f}k"
    if v == int(v):
        return str(int(v))
    return f"{v:.2f}".rstrip("0").rstrip(".")
