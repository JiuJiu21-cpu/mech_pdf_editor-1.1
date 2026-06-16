import fitz
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtGui import QPixmap, QImage


class PdfEngine:
    def __init__(self):
        self.current_file = None

    def open_file_dialog(self, parent):
        file_path, _ = QFileDialog.getOpenFileName(
            parent, "打开PDF文件", "", "PDF文件 (*.pdf)"
        )
        self.current_file = file_path
        return file_path, _

    def save_file_dialog(self, parent):
        file_path, _ = QFileDialog.getSaveFileName(
            parent, "另存为PDF", "未命名.pdf", "PDF文件 (*.pdf)"
        )
        return file_path, _

    def generate_thumbnails(self, doc, width=150):
        thumbnails = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            zoom = width / page.rect.width
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)

            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(img)

            thumbnails.append({
                "page_num": page_num,
                "pixmap": pixmap,
                "label": f"第 {page_num + 1} 页"
            })
        return thumbnails

    def save_bubbles_to_pdf(self, doc, bubble_manager):
        style = bubble_manager.style
        radius = style.bubble_radius
        font_size = style.font_size

        for page_num, bubbles in bubble_manager.bubbles.items():
            page = doc[page_num]
            for bubble in bubbles:
                x, y = bubble["pdf_x"], bubble["pdf_y"]
                page.draw_circle(
                    fitz.Point(x, y),
                    radius,
                    color=self._hex_to_rgb(style.border_color),
                    width=1
                )
                text = bubble["text"]
                text_width = len(text) * font_size * 0.4
                page.insert_text(
                    fitz.Point(x - text_width / 2, y + font_size / 3),
                    text,
                    fontsize=font_size,
                    color=self._hex_to_rgb(style.text_color)
                )
        return doc

    @staticmethod
    def _hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 1)/255 for i in (0, 2, 4))