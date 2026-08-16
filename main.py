# -*- coding: utf-8 -*-
"""班级随机抽取系统 - 应用入口。

用法:
    python main.py                  # 使用默认数据目录 %APPDATA%\\ClassRandomSampling
    python main.py --data-dir DIR   # 使用自定义数据目录

负责: 参数解析、单实例锁、日志初始化、窗口启动。
"""

import argparse
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from config import APP_NAME, APP_TITLE, APP_VERSION, LOG_DAILY_LIMIT, default_data_dir
from logger import OpLogger
from storage import DataStore
from ui.main_window import MainWindow


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=f"{APP_TITLE} v{APP_VERSION}")
    ap.add_argument(
        "--data-dir", dest="data_dir", default=None,
        help="自定义数据目录（默认 %APPDATA%\\ClassRandomSampling）")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    data_dir = Path(args.data_dir) if args.data_dir else default_data_dir()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setApplicationDisplayName(APP_TITLE)
    app.setApplicationVersion(APP_VERSION)

    store = DataStore(data_dir)

    # ---- 单实例锁 ----
    if not store.acquire_lock():
        QMessageBox.critical(
            None, APP_TITLE,
            "程序已在运行中，请勿重复启动。\n\n"
            "（单实例锁定，同一数据目录只能运行一个实例。）\n"
            f"数据目录: {data_dir}")
        return 1

    # ---- 日志：当日超过 500 条弹窗提醒 ----
    def _on_daily_limit(count: int) -> None:
        QMessageBox.information(
            None, "日志提醒",
            f"今日操作日志已达 {count} 条（阈值 {LOG_DAILY_LIMIT} 条），\n"
            "建议及时导出日志文件。")

    logger = OpLogger(data_dir, on_daily_limit=_on_daily_limit)

    window = MainWindow(store, logger, str(data_dir))
    window.show()

    code = app.exec()
    store.release_lock()
    return code


if __name__ == "__main__":
    sys.exit(main())
