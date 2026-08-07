import csv
import json
import os
import secrets
import shutil
import sys
from datetime import datetime
from typing import Dict, List

from PySide6.QtCore import Qt, Slot, QSharedMemory, QSettings
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtCore import QLockFile
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
    QRadioButton,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# ------------------------------------------------------------
# 常量
APP_NAME = "班级随机抽取系统"
VERSION = "2.2"
DEFAULT_DATA_DIR = os.path.join(os.getenv("APPDATA"), "ClassRandomSampling")
MAX_LOG_FILES = 1000

# ------------------------------------------------------------
class WeightEditDialog(QDialog):
    """修改权重的对话框（步长0.50，范围0.00~99.50）"""
    def __init__(self, students: List[Dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("修改学生权重（步长0.50，0为不参与抽取）")
        self.resize(450, 400)
        self.students = students

        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["学号", "姓名", "权重"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setRowCount(len(students))

        for row, s in enumerate(students):
            id_item = QTableWidgetItem(str(s["id"]).zfill(3))
            id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, id_item)

            name_item = QTableWidgetItem(s["name"])
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 1, name_item)

            spin = QDoubleSpinBox()
            spin.setRange(0.00, 99.50)
            spin.setSingleStep(0.50)
            spin.setDecimals(2)
            spin.setValue(s["weight"])
            spin.setProperty("student_id", s["id"])
            self.table.setCellWidget(row, 2, spin)

        layout.addWidget(self.table)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_updates(self) -> Dict[int, float]:
        updates = {}
        for row in range(self.table.rowCount()):
            spin = self.table.cellWidget(row, 2)
            if isinstance(spin, QDoubleSpinBox):
                sid = spin.property("student_id")
                updates[sid] = round(spin.value(), 2)
        return updates

# ------------------------------------------------------------
class ClassRandomSampling(QMainWindow):
    """班级随机抽取学生主窗口（v2.2）"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{VERSION}")
        self.setMinimumSize(800, 500)
        self.resize(900, 600)

        # 数据目录设置（从QSettings读取，无则使用默认）
        self.settings = QSettings("ClassRandomSampling", "App")
        custom_dir = self.settings.value("data_dir", "")
        if custom_dir and os.path.isdir(custom_dir):
            self.data_dir = custom_dir
        else:
            self.data_dir = DEFAULT_DATA_DIR

        # 确保目录存在
        self._check_data_dir()

        # 初始化路径
        self.class_file = os.path.join(self.data_dir, "class_data.json")
        self.backup_file = os.path.join(self.data_dir, "class_data.json.bak")

        self.sysrand = secrets.SystemRandom()
        self.students: List[Dict] = []
        self.current_log_path = self._get_new_log_path()

        self.draw_mode = "all"

        self._init_ui()
        self._init_shortcuts()
        self._load_data()
        self._populate_table()
        self._update_status_bar()
        self._log_operation("程序启动")

    # ----------------------------------------------------------
    # 数据目录管理
    # ----------------------------------------------------------
    def _check_data_dir(self):
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            test_file = os.path.join(self.data_dir, ".write_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
        except Exception as e:
            QMessageBox.critical(
                None, "致命错误",
                f"无法访问数据目录：{self.data_dir}\n请检查磁盘权限。\n\n错误详情：{e}"
            )
            sys.exit(1)

    def _switch_data_dir(self, new_dir: str):
        """切换数据目录：复制文件，更新设置，重新加载"""
        # 复制当前目录下所有文件到新目录
        try:
            os.makedirs(new_dir, exist_ok=True)
            for item in os.listdir(self.data_dir):
                src = os.path.join(self.data_dir, item)
                dst = os.path.join(new_dir, item)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                elif os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
        except Exception as e:
            QMessageBox.warning(self, "复制失败", f"无法将数据复制到新目录：{e}")
            return

        # 更新设置和路径
        self.settings.setValue("data_dir", new_dir)
        self.data_dir = new_dir
        self.class_file = os.path.join(self.data_dir, "class_data.json")
        self.backup_file = os.path.join(self.data_dir, "class_data.json.bak")
        self.current_log_path = self._get_new_log_path()

        # 重新加载数据并刷新界面
        self._load_data()
        self._populate_table()
        self._update_status_bar()
        self._log_operation(f"数据目录已切换至：{new_dir}")

        QMessageBox.information(self, "切换成功", f"数据目录已更改为：{new_dir}")

    @Slot()
    def _change_data_dir(self):
        """菜单动作：选择新数据目录"""
        new_dir = QFileDialog.getExistingDirectory(
            self, "选择数据存储文件夹", self.data_dir
        )
        if not new_dir:
            return
        if new_dir == self.data_dir:
            return

        # 询问是否复制数据
        reply = QMessageBox.question(
            self, "切换数据目录",
            f"要将现有数据复制到新目录并切换吗？\n\n新目录：{new_dir}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            self._switch_data_dir(new_dir)

    # ----------------------------------------------------------
    # 日志工具
    # ----------------------------------------------------------
    def _get_new_log_path(self) -> str:
        today = datetime.now().strftime("%Y%m%d")
        base = os.path.join(self.data_dir, f"{today}.log")
        if not os.path.exists(base):
            return base

        existing = []
        for fname in os.listdir(self.data_dir):
            if fname.startswith(f"{today}_") and fname.endswith(".log"):
                try:
                    num = int(fname[len(today)+1:-4])
                    existing.append(num)
                except ValueError:
                    pass

        for i in range(1, MAX_LOG_FILES + 1):
            if i not in existing:
                return os.path.join(self.data_dir, f"{today}_{i}.log")

        if existing:
            old_num = min(existing)
            old_path = os.path.join(self.data_dir, f"{today}_{old_num}.log")
            try:
                os.remove(old_path)
            except OSError:
                pass
            return os.path.join(self.data_dir, f"{today}_{old_num}.log")

        return os.path.join(self.data_dir, f"{today}_overflow.log")

    def _log_operation(self, message: str):
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_line = f"[{timestamp}] {message}"

        try:
            with open(self.current_log_path, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")
        except Exception as e:
            self._show_log_error(f"日志写入失败：{e}")

        if hasattr(self, "log_display"):
            self.log_display.append(log_line)

    def _show_log_error(self, msg: str):
        if hasattr(self, "status_label"):
            self.status_label.setStyleSheet("color: red;")
            self.status_label.setText(msg)
            QApplication.processEvents()
            from PySide6.QtCore import QTimer
            QTimer.singleShot(3000, lambda: self._update_status_bar())

    # ----------------------------------------------------------
    # UI 构建
    # ----------------------------------------------------------
    def _init_ui(self):
        menu_bar = self.menuBar()

        # 文件菜单
        file_menu = menu_bar.addMenu("文件(&F)")
        import_action = file_menu.addAction("导入 CSV 名册...(&I)")
        import_action.setShortcut(QKeySequence("Ctrl+O"))
        import_action.triggered.connect(self._import_csv)
        file_menu.addSeparator()
        # 新增：更改数据目录
        change_dir_action = file_menu.addAction("设置数据目录...")
        change_dir_action.triggered.connect(self._change_data_dir)
        file_menu.addSeparator()
        exit_action = file_menu.addAction("退出(&X)")
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)

        # 操作菜单
        action_menu = menu_bar.addMenu("操作(&A)")
        weight_action = action_menu.addAction("修改权重...(&W)")
        weight_action.setShortcut(QKeySequence("Ctrl+E"))
        weight_action.triggered.connect(self._edit_weights)
        reset_action = action_menu.addAction("重置权重(&R)")
        reset_action.setShortcut(QKeySequence("Ctrl+R"))
        reset_action.triggered.connect(self._reset_all_weights)

        # 帮助菜单
        help_menu = menu_bar.addMenu("帮助(&H)")
        about_action = help_menu.addAction("关于(&A)")
        about_action.setShortcut(QKeySequence("F1"))
        about_action.triggered.connect(self._show_about)

        splitter = QSplitter(Qt.Horizontal)

        # 左侧表格（列宽自适应）
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["学号", "姓名"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        splitter.addWidget(self.table)

        # 右侧面板
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 8, 8, 8)

        self.result_label = QLabel("点击下方按钮抽取")
        self.result_label.setAlignment(Qt.AlignCenter)
        font = self.result_label.font()
        font.setFamilies(["Microsoft YaHei"])
        font.setPointSize(48)
        self.result_label.setFont(font)
        self.result_label.setStyleSheet("font-weight: bold; color: #2c3e50; padding: 20px;")
        right_layout.addWidget(self.result_label)

        mode_layout = QHBoxLayout()
        mode_layout.addStretch()
        self.radio_all = QRadioButton("全部抽取")
        self.radio_male = QRadioButton("只抽男生")
        self.radio_female = QRadioButton("只抽女生")
        self.radio_all.setChecked(True)
        self.radio_all.toggled.connect(self._on_mode_changed)
        self.radio_male.toggled.connect(self._on_mode_changed)
        self.radio_female.toggled.connect(self._on_mode_changed)
        mode_layout.addWidget(self.radio_all)
        mode_layout.addWidget(self.radio_male)
        mode_layout.addWidget(self.radio_female)
        mode_layout.addStretch()
        right_layout.addLayout(mode_layout)

        btn_layout = QHBoxLayout()
        self.draw_btn = QPushButton("🎲 随机抽取 (F5)")
        self.draw_btn.setMinimumHeight(40)
        self.draw_btn.setStyleSheet("font-size: 16px; padding: 8px 24px;")
        self.draw_btn.clicked.connect(self._draw_student)
        btn_layout.addStretch()
        btn_layout.addWidget(self.draw_btn)
        btn_layout.addStretch()
        right_layout.addLayout(btn_layout)

        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet("font-family: Consolas, monospace; font-size: 12px;")
        self.log_display.setMaximumHeight(150)
        right_layout.addWidget(self.log_display)

        splitter.addWidget(right_widget)
        splitter.setSizes([280, 620])
        self.setCentralWidget(splitter)

        self.status_bar = QStatusBar()
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: black;")
        self.status_bar.addPermanentWidget(self.status_label)
        self.setStatusBar(self.status_bar)

    def _init_shortcuts(self):
        QShortcut(QKeySequence("F5"), self).activated.connect(self._draw_student)
        QShortcut(QKeySequence("Ctrl+1"), self).activated.connect(lambda: self._set_draw_mode("all"))
        QShortcut(QKeySequence("Ctrl+2"), self).activated.connect(lambda: self._set_draw_mode("male"))
        QShortcut(QKeySequence("Ctrl+3"), self).activated.connect(lambda: self._set_draw_mode("female"))

    def _set_draw_mode(self, mode: str):
        if not self.students:
            QMessageBox.information(self, "提示", "班级名单为空，无法切换模式。")
            return
        if mode == "all":
            self.radio_all.setChecked(True)
        elif mode == "male":
            self.radio_male.setChecked(True)
        elif mode == "female":
            self.radio_female.setChecked(True)

    # ----------------------------------------------------------
    # 数据持久化（JSON）
    # ----------------------------------------------------------
    def _load_data(self):
        if os.path.exists(self.class_file):
            try:
                with open(self.class_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.students = []
                for s in data:
                    if not all(k in s for k in ("id", "name", "sex", "weight")):
                        raise ValueError("学生数据字段缺失")
                    sid = s["id"]
                    if not isinstance(sid, int) or not (1 <= sid <= 999):
                        raise ValueError(f"学号数据异常：{sid}")
                    s["weight"] = round(float(s["weight"]), 2)
                    self.students.append(s)

                # 学号唯一性校验
                ids_set = set()
                for s in self.students:
                    if s["id"] in ids_set:
                        raise ValueError(f"检测到重复学号：{s['id']}")
                    ids_set.add(s["id"])

            except Exception as e:
                if os.path.exists(self.backup_file):
                    try:
                        with open(self.backup_file, "r", encoding="utf-8") as f:
                            self.students = json.load(f)
                        ids_set = set()
                        for s in self.students:
                            if s["id"] in ids_set:
                                raise ValueError(f"备份数据存在重复学号：{s['id']}")
                            ids_set.add(s["id"])
                        QMessageBox.warning(self, "数据恢复",
                                            f"班级数据文件损坏，已从备份恢复。\n错误：{e}")
                    except Exception:
                        QMessageBox.critical(self, "严重错误",
                                             "班级数据文件及备份均损坏，名单已被清空。")
                        self.students = []
                else:
                    QMessageBox.warning(self, "数据错误",
                                        f"班级数据文件损坏且无备份，名单已清空。\n错误：{e}")
                    self.students = []
        else:
            self.students = []

    def _save_data(self, backup: bool = True):
        try:
            if backup and os.path.exists(self.class_file):
                shutil.copy2(self.class_file, self.backup_file)
            with open(self.class_file, "w", encoding="utf-8") as f:
                json.dump(self.students, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._show_log_error(f"保存数据失败：{e}")

    def closeEvent(self, event):
        self._save_data(backup=False)
        super().closeEvent(event)

    # ----------------------------------------------------------
    # 表格显示与筛选
    # ----------------------------------------------------------
    def _get_filtered_students(self) -> List[Dict]:
        if self.draw_mode == "all":
            return self.students.copy()
        elif self.draw_mode == "male":
            return [s for s in self.students if s.get("sex") == "男"]
        elif self.draw_mode == "female":
            return [s for s in self.students if s.get("sex") == "女"]
        return []

    def _populate_table(self):
        filtered = self._get_filtered_students()
        self.table.setRowCount(len(filtered))
        for row, s in enumerate(filtered):
            display_id = str(s["id"]).zfill(3)
            id_item = QTableWidgetItem(display_id)
            id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, id_item)

            name_item = QTableWidgetItem(s["name"])
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 1, name_item)

        self.result_label.setText("点击下方按钮抽取")
        self.result_label.setStyleSheet("font-weight: bold; color: #2c3e50; padding: 20px;")

    def _on_mode_changed(self):
        if self.radio_all.isChecked():
            self.draw_mode = "all"
        elif self.radio_male.isChecked():
            self.draw_mode = "male"
        elif self.radio_female.isChecked():
            self.draw_mode = "female"
        self._populate_table()

    # ----------------------------------------------------------
    # 核心功能
    # ----------------------------------------------------------
    def _validate_weights(self, filtered: List[Dict]) -> bool:
        total = sum(s["weight"] for s in filtered)
        if total <= 0:
            QMessageBox.warning(self, "抽取错误", "当前抽取范围内所有学生的权重总和为0，无法抽取。")
            return False
        return True

    @Slot()
    def _draw_student(self):
        if not self.students:
            QMessageBox.information(self, "提示", "班级名单为空，请先导入 CSV 名册。")
            return

        filtered = [s for s in self._get_filtered_students() if s["weight"] > 0]
        if not filtered:
            mode_text = {"male": "男生", "female": "女生", "all": "学生"}[self.draw_mode]
            QMessageBox.information(self, "提示", f"没有可抽取的{mode_text}（权重均为0）。")
            return

        if not self._validate_weights(filtered):
            return

        names = [s["name"] for s in filtered]
        weights = [s["weight"] for s in filtered]

        try:
            chosen_idx = self.sysrand.choices(range(len(filtered)), weights=weights, k=1)[0]
            chosen_student = filtered[chosen_idx]
        except Exception as e:
            QMessageBox.critical(self, "抽取失败", f"随机抽取出错:\n{e}")
            return

        display_text = f"{str(chosen_student['id']).zfill(3)} {chosen_student['name']}"
        self.result_label.setText(display_text)
        self.result_label.setStyleSheet("font-weight: bold; color: blue; padding: 20px;")

        mode_text = {"male": "只抽男生", "female": "只抽女生", "all": "全部抽取"}[self.draw_mode]
        self._log_operation(
            f"模式: {mode_text} | "
            f"学号: {str(chosen_student['id']).zfill(3)} | "
            f"姓名: {chosen_student['name']} | "
            f"性别: {chosen_student['sex']} | "
            f"W: {chosen_student['weight']:.2f}"
        )

    @Slot()
    def _edit_weights(self):
        if not self.students:
            QMessageBox.information(self, "提示", "班级名单为空，无法修改权重。")
            return

        dialog = WeightEditDialog(self.students, self)
        if dialog.exec() == QDialog.Accepted:
            updates = dialog.get_updates()
            for s in self.students:
                if s["id"] in updates:
                    s["weight"] = round(updates[s["id"]], 2)
            self._save_data()
            self._log_operation("修改了学生权重")
            self._update_status_bar()
            self._populate_table()

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
        for s in self.students:
            s["weight"] = 1.0
        self._save_data()
        self._log_operation("重置所有学生权重为 1")
        self._update_status_bar()
        self._populate_table()

    @Slot()
    def _import_csv(self):
        QMessageBox.information(
            self, "导入提示",
            "CSV名册格式（UTF-8）：\n"
            "学号,姓名,性别,权重\n"
            "1,张三,男,1\n"
            "2,李四,女,2\n"
            "（学号、姓名、性别必填，权重可选默认为1）"
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

                id_col = name_col = sex_col = weight_col = None
                for col in reader.fieldnames:
                    if col is None:
                        continue
                    col_lower = col.strip().lower()
                    if col_lower in ("学号", "id"):
                        id_col = col
                    elif col_lower in ("姓名", "name"):
                        name_col = col
                    elif col_lower in ("性别", "sex"):
                        sex_col = col
                    elif col_lower in ("权重", "weight"):
                        weight_col = col

                if not id_col:
                    raise ValueError("CSV 文件必须包含“学号”列。")
                if not name_col:
                    raise ValueError("CSV 文件必须包含“姓名”列。")
                if not sex_col:
                    raise ValueError("CSV 文件必须包含“性别”列。")

                new_students = []
                ids_seen = set()
                weight_fixes = []

                for row in reader:
                    sid_str = (row.get(id_col) or "").strip()
                    if not sid_str:
                        raise ValueError("存在空学号，请检查。")
                    try:
                        sid_int = int(sid_str)
                    except ValueError:
                        raise ValueError(f"学号“{sid_str}”不是合法整数。")
                    if not (1 <= sid_int <= 999):
                        raise ValueError(f"学号 {sid_int} 超出范围（1~999）。")
                    if sid_int in ids_seen:
                        raise ValueError(f"学号 {sid_int} 重复，学号必须唯一。")

                    name = (row.get(name_col) or "").strip()
                    if not name:
                        raise ValueError(f"学号 {sid_int} 的学生姓名为空。")

                    sex_val = (row.get(sex_col) or "").strip()
                    if not sex_val:
                        raise ValueError(f"学号 {sid_int} 的性别为空。")
                    sex_str = sex_val.lower()
                    if sex_str in ("男", "m", "male"):
                        sex = "男"
                    elif sex_str in ("女", "f", "female"):
                        sex = "女"
                    else:
                        raise ValueError(f"学号 {sid_int} 的性别“{sex_val}”无效，请用男/女或m/f。")

                    weight = 1.0
                    if weight_col:
                        weight_str = (row.get(weight_col) or "").strip()
                        if weight_str:
                            try:
                                w = float(weight_str)
                                if w < 0.0:
                                    w = 0.0
                                    weight_fixes.append(f"学号 {sid_int} 权重为负，已设为0（不参与抽取）")
                                elif w > 99.50:
                                    w = 99.50
                                    weight_fixes.append(f"学号 {sid_int} 权重超过99.50，已调整为99.50")
                                original_w = w
                                w = round(w * 2) / 2
                                if w > 99.50: w = 99.50
                                elif w < 0.0: w = 0.0
                                if abs(w - original_w) > 0.001:
                                    weight_fixes.append(f"学号 {sid_int} 权重 {weight_str} 已调整为 {w:.2f}（步长0.50）")
                                weight = w
                            except ValueError:
                                weight = 0.0
                                weight_fixes.append(f"学号 {sid_int} 权重“{weight_str}”非法，已设为0（不参与抽取）")

                    new_students.append({
                        "id": sid_int,
                        "name": name,
                        "sex": sex,
                        "weight": weight
                    })
                    ids_seen.add(sid_int)

                if not new_students:
                    raise ValueError("文件中未解析到任何有效学生，请检查名册内容。")

                if weight_fixes:
                    msg = "以下权重已自动修正：\n" + "\n".join(weight_fixes[:10])
                    if len(weight_fixes) > 10:
                        msg += f"\n... 共 {len(weight_fixes)} 处修正，仅显示前10条。"
                    QMessageBox.information(self, "权重自动修正", msg)

        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"读取 CSV 文件时出错:\n{e}")
            return

        self.students = new_students
        self._populate_table()
        self._save_data()
        self._log_operation(f"导入班级名册，共 {len(self.students)} 名学生")
        self._update_status_bar()

    # ----------------------------------------------------------
    # 状态栏
    # ----------------------------------------------------------
    def _update_status_bar(self):
        count = len(self.students)
        male_count = sum(1 for s in self.students if s.get("sex") == "男")
        female_count = count - male_count
        total_weight = sum(s["weight"] for s in self.students)
        self.status_label.setStyleSheet("color: black;")
        self.status_label.setText(
            f"学生总数: {count}（男: {male_count} 女: {female_count}）   |   总权重: {total_weight:.2f}"
        )

    @Slot()
    def _show_about(self):
        QMessageBox.about(
            self, "关于",
            f"{APP_NAME} v{VERSION}\n\n"
            "基于 PySide6 的安全加权随机抽取系统。\n"
            "使用学号作为唯一标识，支持性别过滤、权重调节。\n"
            "权重步长0.50，设为0表示不参与抽取。\n\n"
            "快捷键：\n"
            "  Ctrl+O  导入名册\n"
            "  Ctrl+E  修改权重\n"
            "  Ctrl+R  重置权重\n"
            "  F5      随机抽取\n"
            "  Ctrl+1  全部抽取\n"
            "  Ctrl+2  只抽男生\n"
            "  Ctrl+3  只抽女生\n"
            "  F1      关于\n\n"
            "注意：同一天日志文件数量上限为1000个，超出将自动覆盖最早的日志文件。"
        )

# ------------------------------------------------------------
if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)

    # 使用锁文件检测单实例（数据目录下创建 .lock 文件）
    lock_file_path = os.path.join(
        os.getenv("APPDATA"), "ClassRandomSampling", "app.lock"
    )
    # 确保锁文件目录存在
    os.makedirs(os.path.dirname(lock_file_path), exist_ok=True)

    lock_file = QLockFile(lock_file_path)
    lock_file.setStaleLockTime(0)  # 禁用陈旧锁判定，完全依赖 OS 文件锁

    if not lock_file.tryLock(100):  # 尝试加锁，100ms 超时
        # 加锁失败 → 已有实例运行
        QMessageBox.warning(None, "提示", "程序已在运行中，请勿重复启动。")
        sys.exit(1)

    window = ClassRandomSampling()
    window.show()
    sys.exit(app.exec())