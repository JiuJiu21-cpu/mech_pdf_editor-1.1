import fitz
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSpinBox, QColorDialog, QMessageBox, QListWidget,
    QScrollArea, QFrame, QListWidgetItem, QFileDialog, QDialog
)
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QBrush, QColor, QFont, QIcon
from PyQt6.QtCore import Qt, QRectF, QPointF, QSize

from core import PdfEngine, IntelligentRecognizer, BubbleManager, ExcelExporter
from .bubble_edit_dialog import BubbleEditDialog


class PdfCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color: #e5e5e5;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self.main_window or not self.main_window.current_pixmap:
            return

        page_rect = self.main_window.get_page_display_rect()
        painter.drawPixmap(
            int(page_rect.x()), int(page_rect.y()),
            int(page_rect.width()), int(page_rect.height()),
            self.main_window.current_pixmap
        )

        current_page = self.main_window.current_page
        bubbles = self.main_window.bubble_manager.get_page_bubbles(current_page)
        if not bubbles:
            return

        style = self.main_window.bubble_manager.style
        pen = QPen(QColor(style.border_color))
        pen.setWidth(1)
        brush = QBrush(QColor(style.fill_color))
        text_pen = QPen(QColor(style.text_color))
        font = QFont("Arial", style.font_size)

        painter.setPen(pen)
        painter.setBrush(brush)
        painter.setFont(font)

        for bubble in bubbles:
            screen_x, screen_y = self.main_window.pdf_to_screen(
                bubble["pdf_x"], bubble["pdf_y"], page_rect
            )
            radius = style.bubble_radius

            painter.drawEllipse(QPointF(screen_x, screen_y), radius, radius)

            painter.setPen(text_pen)
            text_rect = QRectF(screen_x - radius, screen_y - radius,
                              radius * 2, radius * 2)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, bubble["text"])
            painter.setPen(pen)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.main_window:
            self.main_window.handle_canvas_click(
                event.position().x(), event.position().y()
            )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("机械图纸智能气泡标注PDF编辑器 v2.0")
        self.resize(1400, 850)

        self.pdf_engine = PdfEngine()
        self.recognizer = IntelligentRecognizer()
        self.bubble_manager = BubbleManager()

        self.current_doc = None
        self.current_page = -1
        self.current_pixmap = None
        self.zoom_factor = 1.0
        self.continuous_mode = False

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧缩略图导航
        left_panel = QFrame()
        left_panel.setFixedWidth(180)
        left_panel.setStyleSheet("background-color: #f5f5f5; border-right: 1px solid #ddd;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.addWidget(QLabel("页面导航"))

        self.thumbnail_list = QListWidget()
        self.thumbnail_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.thumbnail_list.setIconSize(QSize(140, 180))
        self.thumbnail_list.setSpacing(8)
        self.thumbnail_list.setMovement(QListWidget.Movement.Static)
        left_layout.addWidget(self.thumbnail_list, 1)

        # 中间区域
        mid_panel = QWidget()
        mid_layout = QVBoxLayout(mid_panel)
        mid_layout.setContentsMargins(0, 0, 0, 0)
        mid_layout.setSpacing(0)

        # 顶部工具栏
        toolbar = QFrame()
        toolbar.setFixedHeight(50)
        toolbar.setStyleSheet("background-color: #f8f8f8; border-bottom: 1px solid #ddd;")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(10, 5, 10, 5)

        self.btn_open = QPushButton("打开PDF")
        self.btn_save = QPushButton("保存PDF")
        self.btn_save_as = QPushButton("另存为")
        self.btn_recognize = QPushButton("识别当前页")
        self.btn_auto_annotate = QPushButton("自动标注")
        self.btn_renumber_all = QPushButton("全页重编号")
        self.btn_clear = QPushButton("清空标注")

        toolbar_layout.addWidget(self.btn_open)
        toolbar_layout.addWidget(self.btn_save)
        toolbar_layout.addWidget(self.btn_save_as)
        toolbar_layout.addSpacing(20)
        toolbar_layout.addWidget(self.btn_recognize)
        toolbar_layout.addWidget(self.btn_auto_annotate)
        toolbar_layout.addWidget(self.btn_renumber_all)
        toolbar_layout.addWidget(self.btn_clear)
        toolbar_layout.addStretch()

        toolbar_layout.addWidget(QLabel("半径:"))
        self.spin_radius = QSpinBox()
        self.spin_radius.setRange(5, 50)
        self.spin_radius.setValue(self.bubble_manager.style.bubble_radius)
        toolbar_layout.addWidget(self.spin_radius)

        toolbar_layout.addWidget(QLabel("字号:"))
        self.spin_font = QSpinBox()
        self.spin_font.setRange(6, 30)
        self.spin_font.setValue(self.bubble_manager.style.font_size)
        toolbar_layout.addWidget(self.spin_font)

        self.btn_border_color = QPushButton("边框色")
        self.btn_fill_color = QPushButton("填充色")
        self.btn_text_color = QPushButton("文字色")
        toolbar_layout.addWidget(self.btn_border_color)
        toolbar_layout.addWidget(self.btn_fill_color)
        toolbar_layout.addWidget(self.btn_text_color)

        mid_layout.addWidget(toolbar)

        # 画布
        self.canvas = PdfCanvas(self)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.canvas)
        mid_layout.addWidget(scroll_area, 1)

        # 右侧面板
        right_panel = QFrame()
        right_panel.setFixedWidth(220)
        right_panel.setStyleSheet("background-color: #f5f5f5; border-left: 1px solid #ddd;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)

        right_layout.addWidget(QLabel("标注列表（双击编辑）"))
        self.bubble_list = QListWidget()
        right_layout.addWidget(self.bubble_list, 1)

        self.lbl_count = QLabel("当前页：0 个标注 | 全文档：0 个标注")
        right_layout.addWidget(self.lbl_count)

        right_layout.addSpacing(10)
        self.btn_continuous = QPushButton("开启连续标注")
        right_layout.addWidget(self.btn_continuous)
        self.btn_export_excel = QPushButton("导出Excel质检报告")
        right_layout.addWidget(self.btn_export_excel)

        main_layout.addWidget(left_panel)
        main_layout.addWidget(mid_panel, 1)
        main_layout.addWidget(right_panel)

    def _connect_signals(self):
        self.btn_open.clicked.connect(self.open_pdf)
        self.btn_save.clicked.connect(self.save_pdf)
        self.btn_save_as.clicked.connect(self.save_pdf_as)

        self.thumbnail_list.currentRowChanged.connect(self.switch_page)

        self.btn_recognize.clicked.connect(self.recognize_current_page)
        self.btn_auto_annotate.clicked.connect(self.auto_bubble_annotate)
        self.btn_renumber_all.clicked.connect(self.renumber_all_bubbles)
        self.btn_clear.clicked.connect(self.clear_current_page_bubbles)

        self.bubble_list.itemDoubleClicked.connect(self.edit_selected_bubble)

        self.btn_continuous.clicked.connect(self.toggle_continuous_mode)
        self.btn_export_excel.clicked.connect(self.export_excel_report)

        self.spin_radius.valueChanged.connect(self.update_bubble_style)
        self.spin_font.valueChanged.connect(self.update_bubble_style)
        self.btn_border_color.clicked.connect(self.choose_border_color)
        self.btn_fill_color.clicked.connect(self.choose_fill_color)
        self.btn_text_color.clicked.connect(self.choose_text_color)

    # ========== 坐标转换核心 ==========
    def get_page_display_rect(self):
        if not self.current_doc or self.current_page < 0 or not self.current_pixmap:
            return QRectF(0, 0, 0, 0)

        page = self.current_doc[self.current_page]
        page_w = page.rect.width * self.zoom_factor
        page_h = page.rect.height * self.zoom_factor

        canvas_w = self.canvas.width()
        canvas_h = self.canvas.height()

        offset_x = (canvas_w - page_w) / 2 if canvas_w > page_w else 0
        offset_y = (canvas_h - page_h) / 2 if canvas_h > page_h else 0

        return QRectF(offset_x, offset_y, page_w, page_h)

    def pdf_to_screen(self, pdf_x, pdf_y, page_rect=None):
        if page_rect is None:
            page_rect = self.get_page_display_rect()

        screen_x = page_rect.x() + pdf_x * self.zoom_factor
        screen_y = page_rect.y() + page_rect.height() - pdf_y * self.zoom_factor
        return screen_x, screen_y

    def screen_to_pdf(self, screen_x, screen_y, page_rect=None):
        if page_rect is None:
            page_rect = self.get_page_display_rect()

        pdf_x = (screen_x - page_rect.x()) / self.zoom_factor
        pdf_y = (page_rect.height() - (screen_y - page_rect.y())) / self.zoom_factor
        return pdf_x, pdf_y

    # ========== PDF文件操作 ==========
    def open_pdf(self):
        file_path, _ = self.pdf_engine.open_file_dialog(self)
        if not file_path:
            return
        try:
            self.current_doc = fitz.open(file_path)
            self.current_page = 0
            self.bubble_manager.clear_all()
            self.continuous_mode = False

            self._load_thumbnails()
            self._render_current_page()
            self._update_bubble_list()
            self._update_bubble_count()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开PDF失败：{str(e)}")

    def _load_thumbnails(self):
        self.thumbnail_list.clear()
        thumbnails = self.pdf_engine.generate_thumbnails(self.current_doc)
        for item in thumbnails:
            list_item = QListWidgetItem()
            list_item.setIcon(QIcon(item["pixmap"]))
            list_item.setText(item["label"])
            list_item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.thumbnail_list.addItem(list_item)
        self.thumbnail_list.setCurrentRow(0)

    def save_pdf(self):
        if not self.current_doc:
            QMessageBox.warning(self, "提示", "请先打开PDF文件")
            return
        try:
            self.pdf_engine.save_bubbles_to_pdf(self.current_doc, self.bubble_manager)
            self.current_doc.saveIncr()
            QMessageBox.information(self, "提示", "保存成功")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败：{str(e)}")

    def save_pdf_as(self):
        if not self.current_doc:
            QMessageBox.warning(self, "提示", "请先打开PDF文件")
            return
        save_path, _ = self.pdf_engine.save_file_dialog(self)
        if not save_path:
            return
        try:
            self.pdf_engine.save_bubbles_to_pdf(self.current_doc, self.bubble_manager)
            self.current_doc.save(save_path)
            QMessageBox.information(self, "提示", "另存为成功")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败：{str(e)}")

    # ========== 页面切换 ==========
    def switch_page(self, page_num):
        if page_num < 0 or page_num >= len(self.current_doc):
            return
        self.current_page = page_num
        self._render_current_page()
        self._update_bubble_list()
        self._update_bubble_count()

    # ========== PDF渲染 ==========
    def _render_current_page(self):
        if not self.current_doc or self.current_page < 0:
            self.current_pixmap = None
            self.canvas.update()
            return

        page = self.current_doc[self.current_page]

        canvas_w = self.canvas.width()
        canvas_h = self.canvas.height()
        if canvas_w <= 0 or canvas_h <= 0:
            self.zoom_factor = 1.0
        else:
            self.zoom_factor = min(
                canvas_w / page.rect.width,
                canvas_h / page.rect.height
            ) * 0.95

        mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
        self.current_pixmap = QPixmap.fromImage(img)
        self.canvas.update()

    # ========== 智能识别 ==========
    def recognize_current_page(self):
        if not self.current_doc or self.current_page < 0:
            QMessageBox.warning(self, "提示", "请先打开PDF文件")
            return

        page = self.current_doc[self.current_page]
        results = self.recognizer.recognize_page(page)
        QMessageBox.information(self, "识别结果", f"当前页识别到 {len(results)} 项可标注内容")

    # ========== 气泡标注 ==========
    def auto_bubble_annotate(self):
        if not self.current_doc or self.current_page < 0:
            QMessageBox.warning(self, "提示", "请先打开PDF文件")
            return

        page = self.current_doc[self.current_page]
        results = self.recognizer.recognize_page(page)
        if not results:
            QMessageBox.information(self, "提示", "未识别到可标注内容")
            return

        start_num = self.bubble_manager.get_max_bubble_number() + 1

        for idx, item in enumerate(results):
            self.bubble_manager.add_bubble(
                page_num=self.current_page,
                pdf_x=item["x"],
                pdf_y=item["y"],
                text=str(start_num + idx)
            )

        self.canvas.update()
        self._update_bubble_list()
        self._update_bubble_count()
        QMessageBox.information(self, "提示", f"已添加 {len(results)} 个标注，序号从 {start_num} 开始")

    def handle_canvas_click(self, x, y):
        if not self.current_doc or self.current_page < 0:
            return

        page_rect = self.get_page_display_rect()
        if not page_rect.contains(x, y):
            return

        pdf_x, pdf_y = self.screen_to_pdf(x, y, page_rect)

        if self.continuous_mode:
            next_num = self.bubble_manager.get_max_bubble_number() + 1
            self.bubble_manager.add_bubble(
                page_num=self.current_page,
                pdf_x=pdf_x,
                pdf_y=pdf_y,
                text=str(next_num)
            )
        else:
            self.bubble_manager.add_bubble(
                page_num=self.current_page,
                pdf_x=pdf_x,
                pdf_y=pdf_y,
                text="1"
            )

        self.canvas.update()
        self._update_bubble_list()
        self._update_bubble_count()

    def edit_selected_bubble(self, item):
        index = self.bubble_list.row(item)
        bubbles = self.bubble_manager.get_page_bubbles(self.current_page)
        if index >= len(bubbles):
            return
        bubble = bubbles[index]

        dialog = BubbleEditDialog(bubble, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_data = dialog.get_result()
            self.bubble_manager.update_bubble(
                self.current_page,
                bubble["id"],
                **new_data
            )
            self.canvas.update()
            self._update_bubble_list()

    def toggle_continuous_mode(self):
        self.continuous_mode = not self.continuous_mode
        if self.continuous_mode:
            self.btn_continuous.setText("关闭连续标注")
            QMessageBox.information(self, "提示", "连续标注已开启，点击画布自动递增序号")
        else:
            self.btn_continuous.setText("开启连续标注")

    def renumber_all_bubbles(self):
        self.bubble_manager.renumber_all_pages()
        self.canvas.update()
        self._update_bubble_list()
        QMessageBox.information(self, "提示", "全文档标注已重新连续编号")

    def clear_current_page_bubbles(self):
        self.bubble_manager.clear_page(self.current_page)
        self.canvas.update()
        self._update_bubble_list()
        self._update_bubble_count()

    def _update_bubble_list(self):
        self.bubble_list.clear()
        bubbles = self.bubble_manager.get_page_bubbles(self.current_page)
        for bubble in bubbles:
            text = f"序号 {bubble['text']}"
            if bubble["dimension"]:
                text += f" | {bubble['dimension']}"
            self.bubble_list.addItem(text)

    def _update_bubble_count(self):
        page_count = len(self.bubble_manager.get_page_bubbles(self.current_page))
        total_count = len(self.bubble_manager.get_all_bubbles())
        self.lbl_count.setText(f"当前页：{page_count} 个标注 | 全文档：{total_count} 个标注")

    # ========== Excel导出 ==========
    def export_excel_report(self):
        if not self.bubble_manager.get_all_bubbles():
            QMessageBox.warning(self, "提示", "暂无标注数据可导出")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, "导出质检报告", "质检标注清单.xlsx", "Excel文件 (*.xlsx)"
        )
        if not save_path:
            return

        try:
            ExcelExporter.export_quality_report(self.bubble_manager, save_path)
            QMessageBox.information(self, "提示", f"导出成功，文件已保存至：\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败：{str(e)}")

    # ========== 样式设置 ==========
    def update_bubble_style(self):
        self.bubble_manager.style.bubble_radius = self.spin_radius.value()
        self.bubble_manager.style.font_size = self.spin_font.value()
        self.canvas.update()

    def choose_border_color(self):
        color = QColorDialog.getColor(QColor(self.bubble_manager.style.border_color), self, "选择边框色")
        if color.isValid():
            self.bubble_manager.style.border_color = color.name()
            self.canvas.update()

    def choose_fill_color(self):
        color = QColorDialog.getColor(QColor(self.bubble_manager.style.fill_color), self, "选择填充色")
        if color.isValid():
            self.bubble_manager.style.fill_color = color.name()
            self.canvas.update()

    def choose_text_color(self):
        color = QColorDialog.getColor(QColor(self.bubble_manager.style.text_color), self, "选择文字色")
        if color.isValid():
            self.bubble_manager.style.text_color = color.name()
            self.canvas.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.current_doc:
            self._render_current_page()