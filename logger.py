# -*- coding: utf-8 -*-
"""操作日志模块。

- 按天生成 yyyyMMdd.log 文件
- 每条日志精确到毫秒
- 每日序号递增、无上限（跨天重新计数）
- 当日累计超过 LOG_DAILY_LIMIT 条时通过回调弹窗提醒（仅提醒一次）
- 支持导出全部日志合并文件、清理旧日志
"""

from datetime import datetime
from pathlib import Path
from typing import Callable

from config import APP_TITLE, LOG_DAILY_LIMIT, LOG_KEEP_DAYS, LOG_SEQ_WIDTH

LOG_SUBDIR = "logs"
LOG_EXPORT_PREFIX = "日志导出"


class OpLogger:
    """操作日志写入器。"""

    def __init__(self, data_dir: Path,
                 on_daily_limit: Callable[[int], None] | None = None):
        self.log_dir = Path(data_dir) / LOG_SUBDIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._on_daily_limit = on_daily_limit
        self._day: str = ""
        self._seq: int = 0
        self._limit_notified: bool = False
        self._roll()

    # ---------- 内部 ----------
    def _today_path(self) -> Path:
        return self.log_dir / f"{self._day}.log"

    def _roll(self) -> None:
        """跨天切换文件：重置序号，并续读当日已有行数。"""
        day = datetime.now().strftime("%Y%m%d")
        if day == self._day:
            return
        self._day = day
        self._seq = 0
        self._limit_notified = False
        path = self._today_path()
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    self._seq = sum(1 for _ in fh)
            except OSError:
                self._seq = 0

    # ---------- 写入 ----------
    def log(self, action: str, detail: str = "") -> str:
        """写入一条日志，返回完整日志行文本。"""
        self._roll()
        self._seq += 1
        now = datetime.now()
        ts = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # 毫秒
        line = f"{self._seq:0{LOG_SEQ_WIDTH}d}  {ts}  {action}"
        if detail:
            line += f"  {detail}"
        try:
            with open(self._today_path(), "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            pass
        # 当日超过 500 条弹窗提醒（仅提醒一次）
        if (self._on_daily_limit is not None
                and self._seq >= LOG_DAILY_LIMIT
                and not self._limit_notified):
            self._limit_notified = True
            try:
                self._on_daily_limit(self._seq)
            except Exception:
                pass
        return line

    def today_count(self) -> int:
        """当日已记录条数。"""
        self._roll()
        return self._seq

    def recent_lines(self, limit: int) -> list[str]:
        """返回最近若干条日志（供右侧日志区显示）。"""
        path = self._today_path()
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.read().splitlines()
        except OSError:
            return []
        return lines[-limit:]

    # ---------- 导出 / 清理 ----------
    def export_all(self, target: Path | str | None = None) -> Path:
        """合并所有日志文件为一个导出文件，返回导出路径。"""
        if target is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            target = self.log_dir / f"{LOG_EXPORT_PREFIX}_{ts}.txt"
        target = Path(target)   # 兼容 QFileDialog 返回的 str 路径
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as out:
            out.write(f"# {APP_TITLE} 全部日志导出（{datetime.now():%Y-%m-%d %H:%M:%S}）\n")
            for p in sorted(self.log_dir.glob("*.log")):
                out.write(f"\n# ============ {p.stem} ============\n")
                try:
                    content = p.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                out.write(content)
                if content and not content.endswith("\n"):
                    out.write("\n")
        return target

    def cleanup_old(self, keep_days: int = LOG_KEEP_DAYS) -> int:
        """删除超过 keep_days 天的日志文件，返回删除数量。"""
        import time
        cutoff = time.time() - keep_days * 86400
        removed = 0
        for p in self.log_dir.glob("*.log"):
            try:
                if p.stat().st_mtime < cutoff:
                    p.unlink()
                    removed += 1
            except OSError:
                continue
        return removed
