import csv
import json
import os
import secrets
import sys
from datetime import datetime

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class WeightEditDialog(QDialog):
    """修改权重的对话框"""
    def __init__(self, students, parent=None):
        super().__init__(parent)
        self.setWindowTitle("修改学生权重")
        self.resize(400, 400)
        self.students = students

        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["姓名", "权重"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.setRowCount(len(students))

        for row, s in enumerate(students):
            name_item = QTableWidgetItem(s["name"])
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, name_item)

            spin = QDoubleSpinBox()
            spin.setRange(0.01, 9999.99)
            spin.setDecimals(2)
            spin.setValue(s["weight"])
            self.table.setCellWidget(row, 1, spin)

        layout.addWidget(self.table)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_weights(self):
        weights = []
        for row in range(self.table.rowCount()):
            spin = self.table.cellWidget(row, 1)
            if isinstance(spin, QDoubleSpinBox):
                weights.append(spin.value())
            else:
                weights.append(1.0)
        return weights


class ClassRandomSampling(QMainWindow):
    """班级随机抽取学生主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("班级随机抽取系统")
        self.resize(900, 600)

        self.data_dir = os.path.join(os.getenv("APPDATA"), "ClassRandomSampling")
        os.makedirs(self.data_dir, exist_ok=True)
        self.class_file = os.path.join(self.data_dir, "class_data.json")

        self.sysrand = secrets.SystemRandom()
        self.students = []

        self.current_log_path = self._get_new_log_path()

        self._init_ui()
        self._load_data()
        self._populate_table()
        self._update_status_bar()
        self._log_operation("程序启动")

    def _get_new_log_path(self) -> str:
        today = datetime.now().strftime("%Y%m%d")
        base = os.path.join(self.data_dir, f"{today}.log")
        if not os.path.exists(base):
            return base
        i = 1
        while True:
            candidate = os.path.join(self.data_dir, f"{today}_{i}.log")
            if not os.path.exists(candidate):
                return candidate
            i += 1

    def _log_operation(self, message: str):
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_line = f"[{timestamp}] {message}"

        try:
            with open(self.current_log_path, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")
        except Exception as e:
            print(f"写入日志失败: {e}")

        if hasattr(self, "log_display"):
            self.log_display.append(log_line)

    def _init_ui(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("文件")
        file_menu.addAction("导入 CSV 名册...", self._import_csv)
        file_menu.addSeparator()
        file_menu.addAction("退出", self.close)

        action_menu = menu_bar.addMenu("操作")
        action_menu.addAction("修改权重...", self._edit_weights)
        action_menu.addAction("一键重置所有权重为 1", self._reset_all_weights)

        help_menu = menu_bar.addMenu("帮助")
        help_menu.addAction("关于", self._show_about)

        splitter = QSplitter(Qt.Horizontal)

        # 左侧：学生姓名列表
        self.table = QTableWidget()
        self.table.setColumnCount(1)
        self.table.setHorizontalHeaderLabels(["姓名"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        splitter.addWidget(self.table)

        # 右侧区域
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 8, 8, 8)

        # 抽取结果显示标签 —— 微软雅黑
        self.result_label = QLabel("点击下方按钮抽取")
        self.result_label.setAlignment(Qt.AlignCenter)
        font = self.result_label.font()
        font.setFamilies(["Microsoft YaHei"])
        font.setPointSize(48)
        self.result_label.setFont(font)
        self.result_label.setStyleSheet(
            "font-weight: bold; color: #2c3e50; padding: 20px;"
        )
        right_layout.addWidget(self.result_label)

        # 抽取按钮
        btn_layout = QHBoxLayout()
        self.draw_btn = QPushButton("🎲 随机抽取")
        self.draw_btn.setMinimumHeight(40)
        self.draw_btn.setStyleSheet("font-size: 16px; padding: 8px 24px;")
        self.draw_btn.clicked.connect(self._draw_student)
        btn_layout.addStretch()
        btn_layout.addWidget(self.draw_btn)
        btn_layout.addStretch()
        right_layout.addLayout(btn_layout)

        # 日志显示区域
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet("font-family: Consolas, monospace; font-size: 12px;")
        self.log_display.setMaximumHeight(150)
        right_layout.addWidget(self.log_display)

        splitter.addWidget(right_widget)
        splitter.setSizes([220, 680])

        self.setCentralWidget(splitter)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._update_status_bar()

    def _load_data(self):
        if os.path.exists(self.class_file):
            try:
                with open(self.class_file, "r", encoding="utf-8") as f:
                    self.students = json.load(f)
                for s in self.students:
                    s["weight"] = float(s["weight"])
            except Exception as e:
                QMessageBox.warning(self, "加载数据失败", f"无法读取班级数据文件:\n{e}")
                self.students = []
        else:
            self.students = []

    def _save_data(self):
        try:
            with open(self.class_file, "w", encoding="utf-8") as f:
                json.dump(self.students, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "保存数据失败", f"无法写入班级数据文件:\n{e}")

    def _populate_table(self):
        self.table.setRowCount(len(self.students))
        for row, student in enumerate(self.students):
            name_item = QTableWidgetItem(student["name"])
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, name_item)

    @Slot()
    def _draw_student(self):
        if not self.students:
            QMessageBox.information(self, "提示", "班级名单为空，请先导入 CSV 名册。")
            return

        names = [s["name"] for s in self.students]
        weights = [s["weight"] for s in self.students]

        try:
            chosen = self.sysrand.choices(names, weights=weights, k=1)[0]
        except Exception as e:
            QMessageBox.critical(self, "抽取失败", f"随机抽取出错:\n{e}")
            return

        self.result_label.setText(chosen)
        self.result_label.setStyleSheet(
            "font-weight: bold; color: #e74c3c; padding: 20px;"
        )

        weight = self.students[names.index(chosen)]["weight"]
        self._log_operation(f"抽取结果: {chosen}（权重: {weight}）")

    @Slot()
    def _edit_weights(self):
        if not self.students:
            QMessageBox.information(self, "提示", "班级名单为空，请先导入 CSV 名册。")
            return

        dialog = WeightEditDialog(self.students, self)
        if dialog.exec() == QDialog.Accepted:
            new_weights = dialog.get_weights()
            for i, w in enumerate(new_weights):
                if i < len(self.students):
                    self.students[i]["weight"] = w
            self._save_data()
            self._log_operation("修改了学生权重")
            self._update_status_bar()

    @Slot()
    def _reset_all_weights(self):
        if not self.students:
            return

        reply = QMessageBox.question(
            self, "确认重置",
            "确定要将所有学生的权重重置为 1 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        for student in self.students:
            student["weight"] = 1.0

        self._save_data()
        self._log_operation("重置所有权重为 1")
        self._update_status_bar()

    @Slot()
    def _import_csv(self):
        """导入 CSV 班级名册，已修复 NoneType 错误"""
        QMessageBox.information(
            self,
            "导入提示",
            "第一次使用请先导入CSV格式名册，名册格式：表头为姓名、权重（可不指定权重，默认为1）。当班级人员有改动时需重新导入名册"
        )

        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择 CSV 名册文件", "", "CSV 文件 (*.csv);;所有文件 (*)"
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames is None:
                    raise ValueError("CSV 文件为空或格式错误")

                # 查找姓名列和权重列（跳过可能的 None 列名）
                name_col = None
                weight_col = None
                for col in reader.fieldnames:
                    if col is not None:
                        col_lower = col.strip().lower()
                        if col_lower in ("姓名", "name"):
                            name_col = col
                        elif col_lower in ("权重", "weight"):
                            weight_col = col

                if name_col is None:
                    raise ValueError("CSV 文件中未找到“姓名”列，请确保包含该列。")

                new_students = []
                for row in reader:
                    # 安全地获取姓名（可能为 None）
                    name_val = row.get(name_col)
                    name = name_val.strip() if name_val else ""
                    if not name:
                        continue

                    weight = 1.0
                    if weight_col:
                        weight_val = row.get(weight_col)
                        if weight_val is not None and weight_val.strip():
                            try:
                                weight = float(weight_val.strip())
                                if weight <= 0:
                                    weight = 1.0
                            except ValueError:
                                weight = 1.0
                    new_students.append({"name": name, "weight": weight})

                if not new_students:
                    raise ValueError("未能从文件中解析到任何有效学生。")

        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"读取 CSV 文件时出错:\n{e}")
            return

        self.students = new_students
        self._populate_table()
        self._save_data()
        self._log_operation(f"导入班级名册，共 {len(self.students)} 名学生")
        self._update_status_bar()

    def _update_status_bar(self):
        count = len(self.students)
        total_weight = sum(s["weight"] for s in self.students)
        self.status_bar.showMessage(f"学生总数: {count}   |   总权重: {total_weight:.2f}")

    @Slot()
    def _show_about(self):
        QMessageBox.about(
            self,
            "关于",
            "班级随机抽取系统 v1.0\n\n"
            "使用系统安全随机数发生器，支持加权随机抽取。\n"
            "数据自动保存在 %APPDATA%\\ClassRandomSampling 目录下。",
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ClassRandomSampling()
    window.show()
    sys.exit(app.exec())