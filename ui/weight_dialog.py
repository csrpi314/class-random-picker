# -*- coding: utf-8 -*-
"""权重管理弹窗。

- 基于调用方传入的“当前筛选视图”学生列表（外部已过滤）
- 每行一个 QDoubleSpinBox，步长 WEIGHT_STEP=0.50，0 表示不参与抽取
- 批量设置 / 批量置零（应用于选中行）
- 一键重置所有行为 1.0
- 编辑操作针对副本，取消不生效
"""

import copy

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config import (
    DEFAULT_WEIGHT,
    WEIGHT_DECIMALS,
    WEIGHT_MAX,
    WEIGHT_MIN,
    WEIGHT_STEP,
)
from models import Student


class WeightDialog(QDialog):
    """编辑当前筛选视图内所有学生的权重。"""

    def __init__(self, students: list[Student], parent: QWidget | None = None,
                 log_callback=None):
        super().__init__(parent)
        self._original = {s.id: s for s in students}
        # 在副本上编辑，取消不影响原数据
        self._editing = {s.id: copy.deepcopy(s) for s in students}
        self._log = log_callback          # 外部日志回调，签名 (action, detail) -> None
        self.setWindowTitle("权重管理")
        self.resize(520, 560)
        self._build_ui()
        self._load_rows()
        self._update_count_label()

    # ---------- UI ----------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        tip = QLabel("权重步长 0.50，0 表示不参与抽取。编辑基于当前筛选视图（"
                     f"{len(self._editing)} 人）。")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        self.table = QTableWidget(0, 4, self)
        self.table.setHorizontalHeaderLabels(["学号", "姓名", "性别", "权重"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        # 批量操作行
        btn_row = QHBoxLayout()
        btn_set = QPushButton("批量设置（选中行）")
        btn_zero = QPushButton("批量置零（选中行）")
        btn_reset = QPushButton("一键重置全部为 1.0")
        btn_set.clicked.connect(self._batch_set)
        btn_zero.clicked.connect(self._batch_zero)
        btn_reset.clicked.connect(self._reset_all)
        btn_row.addWidget(btn_set)
        btn_row.addWidget(btn_zero)
        btn_row.addWidget(btn_reset)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self.count_label = QLabel()
        layout.addWidget(self.count_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确定")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ---------- 数据 ----------
    def _load_rows(self) -> None:
        order = sorted(self._editing.values(), key=lambda s: s.id)
        self.table.setRowCount(len(order))
        for row, stu in enumerate(order):
            id_item = QTableWidgetItem(f"{stu.id:03d}")
            id_item.setData(Qt.UserRole, stu.id)
            name_item = QTableWidgetItem(stu.name)
            sex_item = QTableWidgetItem(stu.sex)
            id_item.setFlags(Qt.ItemIsEnabled)
            name_item.setFlags(Qt.ItemIsEnabled)
            sex_item.setFlags(Qt.ItemIsEnabled)
            if stu.weight <= WEIGHT_MIN:
                gray = QBrush(QColor("#999999"))
                for it in (id_item, name_item, sex_item):
                    it.setForeground(gray)
            self.table.setItem(row, 0, id_item)
            self.table.setItem(row, 1, name_item)
            self.table.setItem(row, 2, sex_item)

            spin = QDoubleSpinBox()
            spin.setRange(WEIGHT_MIN, WEIGHT_MAX)
            spin.setSingleStep(WEIGHT_STEP)          # 步长 0.50
            spin.setDecimals(WEIGHT_DECIMALS)
            spin.setValue(stu.weight)
            spin.valueChanged.connect(
                lambda v, sid=stu.id: self._editing[sid].__setattr__("weight", v))
            spin.valueChanged.connect(lambda *_: self._update_count_label())
            self.table.setCellWidget(row, 3, spin)

    def _update_count_label(self) -> None:
        total = len(self._editing)
        zero = sum(1 for s in self._editing.values() if s.weight <= WEIGHT_MIN)
        active = total - zero
        self.count_label.setText(f"共 {total} 人：参与抽取 {active} 人，"
                                 f"不参与（权重 0）{zero} 人")

    # ---------- 批量操作 ----------
    def _selected_ids(self) -> list[int]:
        ids = []
        for index in self.table.selectedIndexes():
            if index.column() == 0:
                sid = index.data(Qt.UserRole)
                if sid is not None:
                    ids.append(int(sid))
        return sorted(set(ids))

    def _batch_set(self) -> None:
        ids = self._selected_ids()
        if not ids:
            QMessageBox.information(self, "批量设置", "请先在表格中选择要设置的行。")
            return
        value, ok = QInputDialog.getDouble(
            self, "批量设置权重", f"为选中的 {len(ids)} 名学生设置权重（0 = 不参与抽取）:",
            DEFAULT_WEIGHT, WEIGHT_MIN, WEIGHT_MAX, WEIGHT_DECIMALS)
        if not ok:
            return
        for sid in ids:
            self._editing[sid].weight = round(value, WEIGHT_DECIMALS)
        self._sync_spins(ids)
        self._update_count_label()
        if self._log:
            names = ", ".join(self._editing[sid].name for sid in ids)
            self._log("批量设置权重",
                      f"设置 {len(ids)} 人权重为 {value:g}（{names}）")

    def _batch_zero(self) -> None:
        ids = self._selected_ids()
        if not ids:
            QMessageBox.information(self, "批量置零", "请先在表格中选择要置零的行。")
            return
        if QMessageBox.question(
                self, "批量置零",
                f"确定将选中的 {len(ids)} 名学生权重置为 0（不参与抽取）吗？") \
                != QMessageBox.Yes:
            return
        for sid in ids:
            self._editing[sid].weight = 0.0
        self._sync_spins(ids)
        self._update_count_label()
        if self._log:
            names = ", ".join(self._editing[sid].name for sid in ids)
            self._log("批量置零",
                      f"将 {len(ids)} 人权重置零（{names}）")

    def _reset_all(self) -> None:
        if not self._editing:
            return
        if QMessageBox.question(
                self, "重置权重", f"确定将所有 {len(self._editing)} 名学生权重重置为 1.0 吗？") \
                != QMessageBox.Yes:
            return
        for stu in self._editing.values():
            stu.weight = DEFAULT_WEIGHT
        self._sync_spins(list(self._editing.keys()))
        self._update_count_label()
        if self._log:
            self._log("重置权重",
                      f"弹窗内一键重置 {len(self._editing)} 人权重为 {DEFAULT_WEIGHT:g}")

    def _sync_spins(self, ids: list[int]) -> None:
        id_to_row = {}
        for row in range(self.table.rowCount()):
            sid = self.table.item(row, 0).data(Qt.UserRole)
            id_to_row[int(sid)] = row
        for sid in ids:
            row = id_to_row.get(sid)
            if row is None:
                continue
            spin = self.table.cellWidget(row, 3)
            if isinstance(spin, QDoubleSpinBox):
                spin.setValue(self._editing[sid].weight)

    # ---------- 结果 ----------
    def _on_accept(self) -> None:
        self.accept()

    def result_weights(self) -> dict[int, float]:
        """返回 {学号: 权重} 映射，供主窗口回写。"""
        return {sid: stu.weight for sid, stu in self._editing.items()}
