# -*- coding: utf-8 -*-
"""数据模型与 CSV 名册导入。

- Student：学生数据模型（id / name / sex / weight）
- import_csv()：UTF-8 / GBK 自动探测、逐行严格校验，
  任何一行出错即抛出 RosterError，调用方不替换数据即为回滚。
"""

import csv
import io
from dataclasses import asdict, dataclass
from pathlib import Path

from config import (
    CSV_ENCODINGS,
    CSV_HEADER_ALIASES,
    CSV_REQUIRED_FIELDS,
    CSV_OPTIONAL_FIELDS,
    DEFAULT_WEIGHT,
    SEX_MALE,
    SEX_FEMALE,
    STUDENT_ID_MIN,
    STUDENT_ID_MAX,
    WEIGHT_MIN,
    WEIGHT_MAX,
    WEIGHT_DECIMALS,
)


class RosterError(Exception):
    """名册相关错误（导入失败等）。"""


@dataclass
class Student:
    """班级学生数据模型。"""

    id: int          # 学号，1~999 整型
    name: str        # 姓名
    sex: str         # "男" / "女"
    weight: float    # 权重，0 = 不参与抽取

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Student":
        """从字典构造，容错缺失/非法字段（非法条目抛 RosterError）。"""
        if not isinstance(data, dict):
            raise RosterError("无效的学生记录（非字典）")
        sid = data.get("id")
        try:
            sid = int(sid)
        except (TypeError, ValueError):
            raise RosterError(f"无效学号: {sid!r}")
        name = str(data.get("name", "")).strip()
        if not name:
            raise RosterError(f"学号 {sid} 缺少姓名")
        sex = normalize_sex(data.get("sex"))
        try:
            weight = float(data.get("weight", DEFAULT_WEIGHT))
        except (TypeError, ValueError):
            weight = DEFAULT_WEIGHT
        if weight < WEIGHT_MIN or weight > WEIGHT_MAX:
            weight = DEFAULT_WEIGHT
        return cls(sid, name, sex, round(weight, WEIGHT_DECIMALS))


def normalize_sex(raw) -> str:
    """性别归一化：男/m/male -> 男；女/f/female -> 女。"""
    text = str(raw).strip().lower()
    if text in SEX_MALE:
        return "男"
    if text in SEX_FEMALE:
        return "女"
    raise RosterError(f"无法识别的性别: {raw!r}（仅支持 男/女/m/f）")


def parse_weight(raw, line_no: int) -> float:
    """解析权重，缺省/空 -> 默认权重；非法数字抛错。"""
    text = str(raw).strip()
    if text == "":
        return DEFAULT_WEIGHT
    try:
        value = float(text)
    except ValueError:
        raise RosterError(f"第 {line_no} 行权重不是有效数字: {raw!r}")
    if not (WEIGHT_MIN <= value <= WEIGHT_MAX):
        raise RosterError(f"第 {line_no} 行权重超出范围 [{WEIGHT_MIN}, {WEIGHT_MAX}]: {raw!r}")
    return round(value, WEIGHT_DECIMALS)


def _normalize_header(row) -> dict:
    """将表头行映射为 {内部字段名: 列索引}。返回 None 表示无法识别。"""
    mapping = {}
    for idx, cell in enumerate(row):
        key = str(cell).strip().lower()
        field = CSV_HEADER_ALIASES.get(key)
        if field and field not in mapping:
            mapping[field] = idx
    return mapping


def _detect_encoding(raw: bytes) -> tuple[str, str]:
    """探测编码并校验表头可识别；返回 (text, encoding)。

    先按 UTF-8 系列解码，再按 GBK 解码；
    用“表头必须能识别出 学号+姓名 两列”作为正确解码的判据，
    避免 GBK 字节恰好构成合法 UTF-8 造成的乱码误判。
    """
    candidates = []
    for enc in CSV_ENCODINGS:
        try:
            text = raw.decode(enc)
        except UnicodeDecodeError:
            continue
        # 快速判据：解析首行表头
        first = text.splitlines()[0] if text.strip() else ""
        if not first:
            continue
        try:
            header = next(csv.reader(io.StringIO(first)))
        except Exception:
            header = []
        mapping = _normalize_header(header)
        if mapping and "id" in mapping and "name" in mapping:
            return text, enc
        candidates.append((enc, mapping, len(header)))
    # 兜底：尝试用首种可解码编码（表头可能用非常规名称）
    for enc in CSV_ENCODINGS:
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    raise RosterError("无法识别文件编码（已尝试 UTF-8 / GBK）")


def _load_text(path: Path) -> tuple[str, str]:
    """读取文件字节并探测编码。"""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise RosterError(f"无法读取文件: {exc}")
    if not raw.strip():
        raise RosterError(f"文件为空: {path.name}")
    return _detect_encoding(raw)


def import_csv(path) -> tuple[list[Student], str]:
    """从 CSV 导入名册。

    返回 (students, encoding)。整个文件解析成功后才返回；
    任何一行错误都会抛出 RosterError，且不会产生部分结果
    （调用方保持旧数据不替换即为“回滚”）。
    """
    path = Path(path)
    text, encoding = _load_text(path)

    try:
        rows = list(csv.reader(io.StringIO(text)))
    except csv.Error as exc:
        raise RosterError(f"CSV 解析失败: {exc}")

    if not rows:
        raise RosterError(f"CSV 文件无内容: {path.name}")

    mapping = _normalize_header(rows[0])
    if not mapping:
        raise RosterError(f"无法识别表头（需要包含：学号、姓名、性别；权重可选）")
    missing = [f for f in CSV_REQUIRED_FIELDS if f not in mapping]
    if missing:
        names = {"id": "学号", "name": "姓名", "sex": "性别", "weight": "权重"}
        raise RosterError("表头缺少必要列: " + "、".join(names[f] for f in missing))

    def get(row, field, default=""):
        idx = mapping.get(field)
        if idx is None:
            return default
        return row[idx] if idx < len(row) else default

    students: list[Student] = []
    seen_ids: set[int] = set()
    for line_no, row in enumerate(rows[1:], start=2):
        if not any(str(c).strip() for c in row):
            continue  # 跳过空行
        raw_id = get(row, "id")
        raw_name = get(row, "name")
        raw_sex = get(row, "sex")
        raw_weight = get(row, "weight", "")

        if raw_id.strip() == "" and raw_name.strip() == "":
            continue  # 完全空白的行

        # 学号：1~999 整型
        try:
            sid = int(str(raw_id).strip())
        except (TypeError, ValueError):
            raise RosterError(f"第 {line_no} 行学号不是整数: {raw_id!r}")
        if not (STUDENT_ID_MIN <= sid <= STUDENT_ID_MAX):
            raise RosterError(
                f"第 {line_no} 行学号超出范围 [{STUDENT_ID_MIN}, {STUDENT_ID_MAX}]: {sid}")
        if sid in seen_ids:
            raise RosterError(f"第 {line_no} 行学号重复: {sid}")
        seen_ids.add(sid)

        # 姓名
        name = str(raw_name).strip()
        if not name:
            raise RosterError(f"第 {line_no} 行（学号 {sid}）姓名为空")
        if len(name) > 50:
            raise RosterError(f"第 {line_no} 行（学号 {sid}）姓名过长")

        # 性别
        try:
            sex = normalize_sex(raw_sex)
        except RosterError as exc:
            raise RosterError(f"第 {line_no} 行（学号 {sid}）{exc}")

        # 权重（可选，默认 1）
        weight = parse_weight(raw_weight, line_no)

        students.append(Student(sid, name, sex, weight))

    if not students:
        raise RosterError(f"没有解析到任何学生记录: {path.name}")

    # 学号去重校验已做；返回新列表
    return students, encoding
