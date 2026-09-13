# -*- coding: utf-8 -*-
"""权重管理弹窗。

- 基于调用方传入的“当前筛选视图”学生列表（外部已过滤）
- 权重仅允许 0.0（不参与抽取）/ 1.0（参与）两个值，步长 1.0
- 校验：任何非法权重（非 0.0 / 1.0）弹窗报错并恢复为默认值 1.0
- 批量设置 / 批量置零（应用于选中行）
- 一键重置所有行为 1.0
- 编辑操作针对副本，取消不生效
- 每一次正常 / 非正常操作（含取消、未选择行、非法值纠正）均通过日志回调记录
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
    WEIGHT_ALLOWED,
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

        tip = QLabel("权重仅允许 0.0（不参与抽取）或 1.0（参与抽取）。"
                     f"编辑基于当前筛选视图（{len(self._editing)} 人）。")
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
        buttons.rejected.connect(self._on_reject)
        layout.addWidget(buttons)

    # ---------- 数据 ----------
    def _load_rows(self) -> None:
        order = sorted(self._editing.values(), key=lambda s: s.id)
        # 旧名册可能残留 0/1 之外的权重（如旧版步长 0.5 的数据），
        # 打开弹窗时统一纠正为默认值 1.0 并记录日志
        for stu in order:
            if stu.weight not in WEIGHT_ALLOWED:
                if self._log:
                    self._log("编辑权重",
                              f"纠正：学生 {stu.id:03d} {stu.name} 权重 "
                              f"{stu.weight:g} 非法（仅允许 0.0/1.0），已恢复为 1.0")
                stu.weight = DEFAULT_WEIGHT
        self.table.setRowCount(len(order))
        for row, stu in enumerate(order):
            id_item = QTableWidgetItem(f"{stu.id:03d}")
            id_item.setData(Qt.UserRole, stu.id)
            name_item = QTableWidgetItem(stu.name)
            sex_item = QTableWidgetItem(stu.sex)
            # 可选中（支持批量操作），不可编辑
            selectable = Qt.ItemIsEnabled | Qt.ItemIsSelectable
            id_item.setFlags(selectable)
            name_item.setFlags(selectable)
            sex_item.setFlags(selectable)
            if stu.weight <= WEIGHT_MIN:
                gray = QBrush(QColor("#999999"))
                for it in (id_item, name_item, sex_item):
                    it.setForeground(gray)
            self.table.setItem(row, 0, id_item)
            self.table.setItem(row, 1, name_item)
            self.table.setItem(row, 2, sex_item)

            spin = QDoubleSpinBox()
            spin.setRange(WEIGHT_MIN, WEIGHT_MAX)
            spin.setSingleStep(WEIGHT_STEP)          # 步长 1.0：0.0 <-> 1.0
            spin.setDecimals(WEIGHT_DECIMALS)
            spin.setValue(stu.weight)
            # 手动输入非法值（如 0.5）时：报错并恢复为默认值 1.0
            sid = stu.id
            name = stu.name
            spin.editingFinished.connect(
                lambda s=spin, i=sid, n=name: self._validate_spin(s, i, n))
            spin.valueChanged.connect(
                lambda v, i=sid: self._editing[i].__setattr__("weight", v))
            spin.valueChanged.connect(lambda *_: self._update_count_label())
            self.table.setCellWidget(row, 3, spin)

    def _validate_spin(self, spin: QDoubleSpinBox, sid: int, name: str) -> None:
        """单个权重输入框校验：非 0.0 / 1.0 -> 报错并恢复为 1.0。"""
        value = spin.value()
        if value in WEIGHT_ALLOWED:
            return
        QMessageBox.warning(
            self, "权重非法",
            f"学生 {sid:03d} {name} 的权重 {value:g} 非法：\n"
            f"权重仅允许 0.0（不参与抽取）或 1.0（参与抽取）。\n"
            f"已恢复为默认值 {DEFAULT_WEIGHT:g}。")
        spin.setValue(DEFAULT_WEIGHT)
        self._editing[sid].weight = DEFAULT_WEIGHT
        self._update_count_label()
        if self._log:
            self._log("编辑权重",
                      f"纠正：学生 {sid:03d} {name} 输入权重 {value:g} 非法，"
                      f"已恢复为默认值 {DEFAULT_WEIGHT:g}")

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
            if self._log:
                self._log("批量设置权重", "取消：未选择行")
            QMessageBox.information(self, "批量设置", "请先在表格中选择要设置的行。")
            return
        value, ok = QInputDialog.getDouble(
            self, "批量设置权重",
            f"为选中的 {len(ids)} 名学生设置权重（仅允许 0.0 或 1.0）:",
            DEFAULT_WEIGHT, WEIGHT_MIN, WEIGHT_MAX, WEIGHT_DECIMALS)
        if not ok:
            if self._log:
                self._log("批量设置权重", "取消：未输入值")
            return
        if value not in WEIGHT_ALLOWED:
            QMessageBox.warning(
                self, "权重非法",
                f"输入的权重 {value:g} 非法：仅允许 0.0（不参与抽取）或 1.0（参与抽取）。\n"
                f"已恢复为默认值 {DEFAULT_WEIGHT:g}。")
            if self._log:
                self._log("批量设置权重",
                          f"纠正：输入权重 {value:g} 非法（仅允许 0.0/1.0），"
                          f"已恢复为默认值 {DEFAULT_WEIGHT:g}")
            value = DEFAULT_WEIGHT
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
            if self._log:
                self._log("批量置零", "取消：未选择行")
            QMessageBox.information(self, "批量置零", "请先在表格中选择要置零的行。")
            return
        if QMessageBox.question(
                self, "批量置零",
                f"确定将选中的 {len(ids)} 名学生权重置为 0（不参与抽取）吗？") \
                != QMessageBox.Yes:
            if self._log:
                self._log("批量置零", "取消：用户取消")
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
            if self._log:
                self._log("重置权重", "取消：用户取消")
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
        """确定前最终校验：任何非法权重报错并恢复为默认值 1.0。"""
        bad = [(sid, stu) for sid, stu in self._editing.items()
               if stu.weight not in WEIGHT_ALLOWED]
        if bad:
            detail = "、".join(f"{sid:03d} {stu.name}（{stu.weight:g}）"
                               for sid, stu in sorted(bad)[:10])
            if len(bad) > 10:
                detail += f" 等 {len(bad)} 人"
            QMessageBox.warning(
                self, "权重非法",
                f"以下学生权重非法（仅允许 0.0 或 1.0），"
                f"已恢复为默认值 {DEFAULT_WEIGHT:g}：\n{detail}")
            for sid, _stu in bad:
                self._editing[sid].weight = DEFAULT_WEIGHT
            self._sync_spins([sid for sid, _ in bad])
            self._update_count_label()
            if self._log:
                self._log("编辑权重",
                          f"纠正：{len(bad)} 人权重非法（仅允许 0.0/1.0），"
                          f"确定时恢复为默认值 {DEFAULT_WEIGHT:g}")
        self.accept()

    def _on_reject(self) -> None:
        """取消按钮：记录未保存后关闭。"""
        if self._log:
            self._log("编辑权重", "取消：弹窗取消按钮")
        self.reject()

    def result_weights(self) -> dict[int, float]:
        """返回 {学号: 权重} 映射，供主窗口回写；非法值兜底为默认权重。"""
        return {sid: (stu.weight if stu.weight in WEIGHT_ALLOWED else DEFAULT_WEIGHT)
                for sid, stu in self._editing.items()}
