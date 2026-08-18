# -*- coding: utf-8 -*-
"""主窗口。

- 左侧：学生表格（学号+姓名，权重 0 置灰）
- 右侧：结果标签（蓝色）+ 抽取按钮 + 性别筛选 + 操作日志区
- 安全加权随机：secrets.SystemRandom().choices() 放回抽取
- 快捷键：F5 / Ctrl+1/2/3 / Ctrl+O / Ctrl+E / Ctrl+R / F1 / Ctrl+Q
- 窗口记忆：位置 / 分割条 / 筛选模式（QSettings）
- 菜单悬停：状态栏左侧显示当前菜单项描述
- 日志：每一次正常 / 非正常操作（含取消、空状态、失败）均记录
"""

import secrets

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QBrush, QColor, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QMenuBar,
    QPushButton,
    QRadioButton,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config import (
    APP_NAME,
    APP_TITLE,
    APP_VERSION,
    DEFAULT_WEIGHT,
    LOG_KEEP_DAYS,
    LOG_UI_VISIBLE,
    ORG_NAME,
    RESULT_BLUE,
    RESULT_FONT_PT,
    SEX_ALL,
    SEX_MAN,
    SEX_WOMAN,
    WEIGHT_DECIMALS,
    format_weight_short,
)
from logger import OpLogger
from models import RosterError, Student, import_csv as import_csv_file
from storage import DataStore
from ui.weight_dialog import WeightDialog


class MainWindow(QMainWindow):
    """班级随机抽取系统主窗口。"""

    def __init__(self, store: DataStore, logger: OpLogger,
                 data_dir: str, parent=None):
        super().__init__(parent)
        self.store = store
        self.logger = logger
        self.data_dir = str(data_dir)

        self.students: list[Student] = store.load_roster()
        self.sex_filter: str = SEX_ALL      # 全部 / 男 / 女
        self._result_text: str = ""

        self._rng = secrets.SystemRandom()          # 密码学安全随机
        self._result_text: str = ""
        self._hover_tip: str = ""                   # 菜单悬停时的临时提示

        self._build_ui()
        self._build_menus()
        self._build_shortcuts()
        self._restore_window_state()
        self.refresh_table()
        self.refresh_status()
        self.log_action("启动", f"应用启动，当前名册 {len(self.students)} 人")

    # ================= UI =================
    def _build_ui(self) -> None:
        self.setWindowTitle(f"{APP_TITLE} v{APP_VERSION}")
        self.resize(900, 620)
        self.setMinimumSize(720, 460)

        splitter = QSplitter(Qt.Horizontal, self)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([260, 640])
        self.splitter = splitter
        self.setCentralWidget(splitter)

        # 状态栏
        sb = QStatusBar(self)
        self.setStatusBar(sb)
        self.status_left = QLabel()
        self.status_right = QLabel()
        sb.addWidget(self.status_left, 1)
        sb.addPermanentWidget(self.status_right)

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(8, 8, 4, 8)
        lay.setSpacing(4)

        # 学生表格：学号 + 姓名
        self.table = QTableWidget(0, 2, self)
        self.table.setHorizontalHeaderLabels(["学号", "姓名"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        lay.addWidget(self.table, 1)
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        # 结果标签（蓝色，超大字号，居中，占据上部主要空间）
        self.result_label = QLabel("等待抽取...")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setStyleSheet(
            f"color:#999999; font-size:{RESULT_FONT_PT}pt; font-weight:bold;")
        lay.addWidget(self.result_label, 3)

        # 抽取按钮（居中，位于结果下方）
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.btn_draw = QPushButton("随机抽取 (F5)")
        self.btn_draw.setMinimumHeight(40)
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.btn_draw.setFont(font)
        self.btn_draw.clicked.connect(self.draw)
        btn_row.addWidget(self.btn_draw)
        btn_row.addStretch(1)
        lay.addLayout(btn_row)

        # 性别筛选（位于抽取按钮之下、日志记录区之上）
        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)
        self.radio_all = QRadioButton("全部")
        self.radio_man = QRadioButton("男生")
        self.radio_woman = QRadioButton("女生")
        self.radio_all.setChecked(True)
        self.sex_group = QButtonGroup(self)
        self.sex_group.addButton(self.radio_all, 0)
        self.sex_group.addButton(self.radio_man, 1)
        self.sex_group.addButton(self.radio_woman, 2)
        self.sex_group.idClicked.connect(self._on_sex_clicked)
        filter_row.addWidget(self.radio_all)
        filter_row.addWidget(self.radio_man)
        filter_row.addWidget(self.radio_woman)
        filter_row.addStretch(1)   # 仅右侧弹性，按钮组左对齐
        lay.addLayout(filter_row)

        # 日志区（占据下半部分）
        self.log_list = QListWidget()
        self.log_list.setWordWrap(True)
        self.log_list.setMaximumHeight(200)
        lay.addWidget(self.log_list, 2)

        self.info_label = QLabel()
        lay.addWidget(self.info_label)

        row = QHBoxLayout()
        btn_export = QPushButton("导出日志")
        btn_clean = QPushButton("清理旧日志")
        btn_export.clicked.connect(self.export_logs)
        btn_clean.clicked.connect(self.cleanup_logs)
        row.addWidget(btn_export)
        row.addWidget(btn_clean)
        lay.addLayout(row)
        return panel

    def _build_menus(self) -> None:
        bar: QMenuBar = self.menuBar()

        menu_file = bar.addMenu("文件(&F)")
        act_import = QAction("导入名册(&I)...", self)
        act_import.setShortcut("Ctrl+O")
        act_import.setStatusTip("导入 CSV 班级名册文件（Ctrl+O）")
        act_import.triggered.connect(self.import_csv)
        menu_file.addAction(act_import)

        act_backup = QAction("备份名册(&B)", self)
        act_backup.setStatusTip("将当前名册导出为 CSV 备份文件")
        act_backup.triggered.connect(self.backup_roster)
        menu_file.addAction(act_backup)
        menu_file.addSeparator()

        act_export = QAction("导出日志(&E)...", self)
        act_export.setStatusTip("将全部操作日志合并导出为文本文件")
        act_export.triggered.connect(self.export_logs)
        menu_file.addAction(act_export)
        act_clean = QAction("清理旧日志(&C)", self)
        act_clean.setStatusTip(f"删除超过 {LOG_KEEP_DAYS} 天的旧日志文件")
        act_clean.triggered.connect(self.cleanup_logs)
        menu_file.addAction(act_clean)
        menu_file.addSeparator()

        act_quit = QAction("退出(&Q)", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.setStatusTip("退出程序（Ctrl+Q）")
        act_quit.triggered.connect(self.close)
        menu_file.addAction(act_quit)

        menu_weight = bar.addMenu("操作(&W)")
        act_edit = QAction("修改权重(&E)...", self)
        act_edit.setShortcut("Ctrl+E")
        act_edit.setStatusTip("打开权重管理对话框，调整学生权重（Ctrl+E）")
        act_edit.triggered.connect(self.edit_weights)
        menu_weight.addAction(act_edit)
        act_reset = QAction("重置权重(&R)", self)
        act_reset.setShortcut("Ctrl+R")
        act_reset.setStatusTip("将所有学生权重恢复为 1（Ctrl+R）")
        act_reset.triggered.connect(self.reset_all_weights)
        menu_weight.addAction(act_reset)

        menu_help = bar.addMenu("帮助(&H)")
        act_about = QAction("关于(&A)", self)
        act_about.setShortcut("F1")
        act_about.setStatusTip("查看关于信息（F1）")
        act_about.triggered.connect(self.show_about)
        menu_help.addAction(act_about)

        # 菜单悬停时在状态栏显示该选项的描述，菜单关闭后恢复统计信息
        for menu in (menu_file, menu_weight, menu_help):
            menu.hovered.connect(self._on_menu_hovered)
            menu.aboutToHide.connect(self._on_menu_hidden)

    def _build_shortcuts(self) -> None:
        # 仅注册无菜单 QAction 对应的快捷键；
        # Ctrl+O/E/R/Q、F1 已在 _build_menus 中通过 QAction.setShortcut 注册，
        # 此处重复会导致 "Ambiguous shortcut overload"。
        QShortcut(QKeySequence("F5"), self, activated=self.draw)
        QShortcut(QKeySequence("Ctrl+1"), self, activated=lambda: self._set_sex(SEX_ALL))
        QShortcut(QKeySequence("Ctrl+2"), self, activated=lambda: self._set_sex(SEX_MAN))
        QShortcut(QKeySequence("Ctrl+3"), self, activated=lambda: self._set_sex(SEX_WOMAN))

    # ================= 菜单悬停状态栏 =================
    def _on_menu_hovered(self, action: QAction) -> None:
        """鼠标悬停在菜单项上时，状态栏左侧显示该选项描述。"""
        tip = action.statusTip()
        if tip:
            self._hover_tip = tip
            self.status_left.setText(tip)

    def _on_menu_hidden(self) -> None:
        """菜单关闭后恢复状态栏左侧的统计信息。"""
        self._hover_tip = ""
        self.refresh_status()

    # ================= 数据视图 =================
    def filtered_students(self) -> list[Student]:
        if self.sex_filter == SEX_MAN:
            return [s for s in self.students if s.sex == SEX_MAN]
        if self.sex_filter == SEX_WOMAN:
            return [s for s in self.students if s.sex == SEX_WOMAN]
        return list(self.students)

    def refresh_table(self) -> None:
        pool = self.filtered_students()
        self.table.setRowCount(len(pool))
        gray = QBrush(QColor("#9E9E9E"))
        for row, stu in enumerate(pool):
            id_item = QTableWidgetItem(f"{stu.id:03d}")
            name_item = QTableWidgetItem(stu.name)
            if stu.weight <= 0:
                id_item.setForeground(gray)   # 权重 0 置灰
                name_item.setForeground(gray)
            self.table.setItem(row, 0, id_item)
            self.table.setItem(row, 1, name_item)

    def refresh_status(self) -> None:
        pool = self.filtered_students()
        men = sum(1 for s in pool if s.sex == SEX_MAN)
        women = len(pool) - men
        active = sum(1 for s in pool if s.weight > 0)
        weight_sum = sum(s.weight for s in pool if s.weight > 0)
        mode = {SEX_ALL: "全部", SEX_MAN: "男生", SEX_WOMAN: "女生"}[self.sex_filter]
        stats = (f"筛选：{mode} | {len(pool)} 人（男 {men} / 女 {women}）| "
                 f"可抽取 {active} 人")
        # 菜单悬停期间优先显示悬停提示，否则显示统计信息
        self.status_left.setText(self._hover_tip or stats)
        self.status_right.setText(
            f"权重合计 {format_weight_short(weight_sum)} | "
            f"数据目录: {self.data_dir}")
        self.info_label.setText(
            f"当前视图 {len(pool)} 人，其中参与抽取 {active} 人。")

    def save_and_refresh(self) -> None:
        """保存 JSON 并刷新界面。"""
        self.store.save_roster(self.students)
        self.refresh_table()
        self.refresh_status()

    # ================= 日志 =================
    def log_action(self, action: str, detail: str = "") -> None:
        line = self.logger.log(action, detail)
        if self.log_list.count() >= LOG_UI_VISIBLE:
            self.log_list.takeItem(0)   # 超出上限时移除最旧（顶部）一条
        self.log_list.addItem(line)     # 新日志追加到底部
        self.log_list.scrollToBottom()

    # ================= 抽取 =================
    def draw(self) -> None:
        pool = self.filtered_students()
        eligible = [s for s in pool if s.weight > 0]
        if not pool:
            self.log_action("抽取", "失败：名册为空")
            QMessageBox.information(self, "抽取", "当前没有学生，请先导入名册（Ctrl+O）。")
            return
        if not eligible:
            self.log_action("抽取", "失败：无可抽取学生（权重均≤0）")
            QMessageBox.information(
                self, "抽取", "当前筛选下没有可抽取的学生（所有权重均为 0）。")
            return
        if len(eligible) == 1:
            # 单一学生抽取时提示
            stu = eligible[0]
            ret = QMessageBox.question(
                self, "抽取提示",
                f"当前可抽取的学生仅 1 人：{stu.id:03d} {stu.name}\n"
                f"权重 {stu.weight:g}。是否仍要抽取？")
            if ret != QMessageBox.Yes:
                self.log_action("抽取", "取消：可抽取学生仅 1 人")
                return
            chosen = stu
        else:
            weights = [s.weight for s in eligible]
            chosen = self._rng.choices(eligible, weights=weights, k=1)[0]

        self.show_result(chosen)
        mode = {SEX_ALL: "全部", SEX_MAN: "男生", SEX_WOMAN: "女生"}[self.sex_filter]
        self.log_action("抽取",
                        f"[模式：{mode}] 抽中 {chosen.id:03d} {chosen.name}"
                        f"（{chosen.sex}，权重 {chosen.weight:g}）")

    def show_result(self, student: Student) -> None:
        text = f"{student.id:03d} {student.name}"
        self._result_text = text
        self.result_label.setText(text)
        self.result_label.setStyleSheet(
            f"color:{RESULT_BLUE}; font-size:{RESULT_FONT_PT}pt; font-weight:bold;")
        # 不自动清除，结果一直保留直到下次抽取

    # ================= 性别筛选 =================
    def _set_sex(self, mode: str, silent: bool = False) -> None:
        self.sex_filter = mode
        if mode == SEX_ALL:
            self.radio_all.setChecked(True)
        elif mode == SEX_MAN:
            self.radio_man.setChecked(True)
        else:
            self.radio_woman.setChecked(True)
        self.refresh_table()
        self.refresh_status()
        if not silent:
            self.log_action("切换筛选", f"性别筛选 -> {mode}")

    def _on_sex_clicked(self, _btn_id: int) -> None:
        btn = self.sex_group.checkedButton()
        mode = SEX_ALL if btn is self.radio_all else (
            SEX_MAN if btn is self.radio_man else SEX_WOMAN)
        if mode == self.sex_filter:
            return
        self._set_sex(mode)

    # ================= 菜单动作 =================
    def import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "导入名册", "", "CSV 文件 (*.csv);;所有文件 (*.*)")
        if not path:
            self.log_action("导入名册", "取消：未选择文件")
            return
        self.log_action("导入名册", f"开始导入文件 {path}")
        try:
            new_students, encoding = import_csv_file(path)
        except RosterError as exc:
            self.log_action("导入名册", f"失败（已回滚）：{exc}")
            QMessageBox.warning(self, "导入失败",
                                f"导入未执行，原有名册保持不变。\n\n原因：{exc}")
            return
        # 覆盖前备份现有名册，防止误操作
        if self.students:
            try:
                self.store.export_roster_csv(self.students)
            except OSError:
                pass
        self.students = new_students
        self.save_and_refresh()
        self.log_action("导入名册",
                        f"成功导入 {len(new_students)} 人（编码 {encoding}）")
        QMessageBox.information(
            self, "导入成功",
            f"成功导入 {len(new_students)} 人（编码 {encoding}）。")

    def backup_roster(self) -> None:
        if not self.students:
            self.log_action("备份名册", "跳过：当前名册为空")
            QMessageBox.information(self, "备份名册", "当前名册为空，无需备份。")
            return
        try:
            target = self.store.export_roster_csv(self.students)
        except OSError as exc:
            self.log_action("备份名册", f"失败：{exc}")
            QMessageBox.warning(self, "备份失败", str(exc))
            return
        self.log_action("备份名册", f"已备份到 {target}")
        QMessageBox.information(
            self, "备份名册", f"名册已备份为 CSV：\n{target}")

    def edit_weights(self) -> None:
        pool = self.filtered_students()
        if not pool:
            self.log_action("编辑权重", "跳过：当前筛选视图无学生")
            QMessageBox.information(self, "权重管理", "当前筛选视图没有学生。")
            return
        dlg = WeightDialog(pool, self, log_callback=self.log_action)
        if dlg.exec() != WeightDialog.Accepted:
            self.log_action("编辑权重", "取消：未保存修改")
            return
        weights = dlg.result_weights()
        changed = 0
        for stu in self.students:
            if stu.id in weights and weights[stu.id] != stu.weight:
                stu.weight = round(weights[stu.id], WEIGHT_DECIMALS)
                changed += 1
        self.save_and_refresh()
        self.log_action("编辑权重",
                        f"基于筛选视图 {len(pool)} 人，修改 {changed} 人")
        if changed == 0:
            QMessageBox.information(self, "权重管理", "未修改任何权重。")

    def reset_all_weights(self) -> None:
        if not self.students:
            self.log_action("重置权重", "跳过：名册为空")
            return
        ret = QMessageBox.question(
            self, "重置权重",
            f"确定将所有 {len(self.students)} 名学生的权重重置为 {DEFAULT_WEIGHT:g} 吗？")
        if ret != QMessageBox.Yes:
            self.log_action("重置权重", "取消：用户取消")
            return
        for stu in self.students:
            stu.weight = DEFAULT_WEIGHT
        self.save_and_refresh()
        self.log_action("重置权重",
                        f"全部 {len(self.students)} 名学生权重重置为 {DEFAULT_WEIGHT:g}")

    def export_logs(self) -> None:
        default = self.logger.log_dir / f"全部日志导出.txt"
        path, _ = QFileDialog.getSaveFileName(
            self, "导出全部日志", str(default), "文本文件 (*.txt);;所有文件 (*.*)")
        if not path:
            self.log_action("导出日志", "取消：未选择保存位置")
            return
        try:
            target = self.logger.export_all(path)
        except OSError as exc:
            self.log_action("导出日志", f"失败：{exc}")
            QMessageBox.warning(self, "导出失败", str(exc))
            return
        self.log_action("导出日志", f"导出全部日志到 {target}")
        QMessageBox.information(self, "导出完成", f"日志已导出到：\n{target}")

    def cleanup_logs(self) -> None:
        ret = QMessageBox.question(
            self, "清理旧日志",
            f"将删除 {LOG_KEEP_DAYS} 天前的日志文件，是否继续？")
        if ret != QMessageBox.Yes:
            self.log_action("清理旧日志", "取消：用户取消")
            return
        removed = self.logger.cleanup_old(LOG_KEEP_DAYS)
        self.log_action("清理旧日志", f"删除 {removed} 个过期日志文件")
        QMessageBox.information(
            self, "清理完成", f"已删除 {removed} 个过期日志文件。")

    def show_about(self) -> None:
        self.log_action("关于", "打开关于对话框")
        QMessageBox.about(
            self, "关于",
            f"<b>{APP_TITLE} v{APP_VERSION}</b><br><br>"
            "基于 Python 3.13 + PySide6 的班级随机抽取系统。<br><br>"
            "快捷键：<br>"
            "&nbsp;&nbsp;F5 抽取 &nbsp;|&nbsp; Ctrl+1/2/3 筛选 全部/男生/女生<br>"
            "&nbsp;&nbsp;Ctrl+O 导入 &nbsp;|&nbsp; Ctrl+E 编辑权重<br>"
            "&nbsp;&nbsp;Ctrl+R 重置权重 &nbsp;|&nbsp; Ctrl+Q 退出<br><br>"
            "数据目录：<br>" + self.data_dir)

    # ================= 窗口记忆 =================
    def _settings(self) -> QSettings:
        return QSettings(ORG_NAME, APP_NAME)

    def _restore_window_state(self) -> None:
        s = self._settings()
        geo = s.value("window/geometry")
        if geo is not None:
            self.restoreGeometry(geo)
        split = s.value("window/splitter")
        if split is not None:
            self.splitter.restoreState(split)
        mode = s.value("window/sex_filter", SEX_ALL)
        if mode in (SEX_ALL, SEX_MAN, SEX_WOMAN):
            self._set_sex(mode, silent=True)   # 恢复记忆不记日志

    def _save_window_state(self) -> None:
        s = self._settings()
        s.setValue("window/geometry", self.saveGeometry())
        s.setValue("window/splitter", self.splitter.saveState())
        s.setValue("window/sex_filter", self.sex_filter)

    def closeEvent(self, event) -> None:
        self._save_window_state()
        self.log_action("退出", "应用退出")
        super().closeEvent(event)
