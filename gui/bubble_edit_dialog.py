from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QDialogButtonBox, QLabel
)


class BubbleEditDialog(QDialog):
    def __init__(self, bubble_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑标注信息")
        self.resize(300, 200)

        self.bubble_data = bubble_data or {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.edit_text = QLineEdit(self.bubble_data.get("text", ""))
        self.edit_dimension = QLineEdit(self.bubble_data.get("dimension", ""))
        self.edit_tolerance = QLineEdit(self.bubble_data.get("tolerance", ""))
        self.edit_remark = QLineEdit(self.bubble_data.get("remark", ""))

        form_layout.addRow(QLabel("序号:"), self.edit_text)
        form_layout.addRow(QLabel("尺寸:"), self.edit_dimension)
        form_layout.addRow(QLabel("公差:"), self.edit_tolerance)
        form_layout.addRow(QLabel("备注:"), self.edit_remark)

        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_result(self):
        return {
            "text": self.edit_text.text().strip(),
            "dimension": self.edit_dimension.text().strip(),
            "tolerance": self.edit_tolerance.text().strip(),
            "remark": self.edit_remark.text().strip()
        }