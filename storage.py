# -*- coding: utf-8 -*-
"""数据持久化。

- JSON 名册保存 / 加载（原子写入，防崩溃损坏）
- 保存前自动轮换备份（保留 BACKUP_KEEP 份）
- 名册导出备份为 CSV（菜单“备份名册”）
- QLockFile 单实例锁
"""

import csv
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QLockFile

from config import BACKUP_KEEP
from models import RosterError, Student

ROSTER_FILENAME = "roster.json"
LOCK_FILENAME = "app.lock"
BACKUP_SUBDIR = "backups"
CSV_BACKUP_PREFIX = "名册备份"


class DataStore:
    """负责数据目录内的所有文件操作。"""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.backup_dir = self.data_dir / BACKUP_SUBDIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.lock = QLockFile(str(self.data_dir / LOCK_FILENAME))
        # 默认 staleLockTime=30s：进程崩溃残留锁文件 30 秒后新实例可接管

    # ---------- 单实例锁 ----------
    def acquire_lock(self) -> bool:
        return self.lock.tryLock(0)

    def release_lock(self) -> None:
        if self.lock.isLocked():
            self.lock.unlock()

    # ---------- 名册 JSON ----------
    @property
    def roster_path(self) -> Path:
        return self.data_dir / ROSTER_FILENAME

    def load_roster(self) -> list[Student]:
        """加载名册 JSON；文件缺失返回空列表，损坏时自动尝试备份恢复。"""
        if not self.roster_path.exists():
            return []
        try:
            raw = json.loads(self.roster_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return self._recover_roster()
        if not isinstance(raw, list):
            return self._recover_roster()
        students: list[Student] = []
        for item in raw:
            try:
                students.append(Student.from_dict(item))
            except RosterError:
                continue  # 跳过损坏条目
        return students

    def _recover_roster(self) -> list[Student]:
        """roster.json 损坏时，尝试从最新轮换备份恢复。"""
        backups = sorted(self.backup_dir.glob("roster_*.json"))
        if not backups:
            return []
        for bp in reversed(backups):
            try:
                raw = json.loads(bp.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if not isinstance(raw, list):
                continue
            students: list[Student] = []
            for d in raw:
                try:
                    students.append(Student.from_dict(d))
                except RosterError:
                    continue    # 跳过损坏条目，不放弃整个备份
            if students:
                # 恢复成功：把备份写回主文件
                self._atomic_write_json(self.roster_path, [s.to_dict() for s in students])
                return students
        return []

    def save_roster(self, students: list[Student], auto_backup: bool = True) -> None:
        """保存名册 JSON（原子写入）；保存前自动轮换备份旧文件。"""
        if auto_backup and self.roster_path.exists():
            self._rotate_backup(self.roster_path)
        payload = [s.to_dict() for s in students]
        self._atomic_write_json(self.roster_path, payload)

    def _rotate_backup(self, src: Path) -> None:
        """把现有文件复制为带时间戳的备份，并清理只保留最近 BACKUP_KEEP 份。"""
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            dst = self.backup_dir / f"roster_{ts}.json"
            shutil.copy2(src, dst)
        except OSError:
            return
        self._trim_backups("roster_*.json")

    def _trim_backups(self, pattern: str) -> None:
        backups = sorted(self.backup_dir.glob(pattern))
        for old in backups[:-BACKUP_KEEP]:
            try:
                old.unlink()
            except OSError:
                pass

    @staticmethod
    def _atomic_write_json(path: Path, payload) -> None:
        """先写临时文件再原子替换，避免中途崩溃产生半截 JSON。"""
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        os.replace(tmp, path)

    # ---------- 名册备份为 CSV ----------
    def export_roster_csv(self, students: list[Student],
                          target: Path | str | None = None) -> Path:
        """把当前名册导出为 CSV（含表头），默认存到 backups/ 目录。"""
        if target is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            target = self.backup_dir / f"{CSV_BACKUP_PREFIX}_{ts}.csv"
        target = Path(target)   # 兼容字符串路径
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh)
            writer.writerow(["学号", "姓名", "性别", "权重"])
            for s in students:
                writer.writerow([s.id, s.name, s.sex, s.weight])
        return target

    def open_backup_dir(self) -> None:
        """打开备份目录（仅记录路径，由调用方决定是否系统打开）。"""
        return str(self.backup_dir)
