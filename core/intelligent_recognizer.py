import re
import fitz
import io
from PIL import Image


class IntelligentRecognizer:
    def __init__(self):
        self.patterns = [
            r"[ΦØφ]\s*\d+\.?\d*\s*[±+-]\s*\d+\.?\d*",
            r"\d+\.?\d*\s*[±+-]\s*\d+\.?\d*",
            r"\b\d{1,4}\.?\d*\b"
        ]
        self._ocr_engine = None

    def _get_ocr_engine(self):
        if self._ocr_engine is None:
            from paddleocr import PaddleOCR
            self._ocr_engine = PaddleOCR(
                use_angle_cls=False,
                lang="en",
                show_log=False
            )
        return self._ocr_engine

    def recognize_page(self, page: fitz.Page):
        results = self._recognize_native_text(page)
        if results:
            return results
        return self._recognize_by_ocr(page)

    def _recognize_native_text(self, page: fitz.Page):
        text_dict = page.get_text("dict")
        results = []

        for block in text_dict["blocks"]:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if not text or len(text) > 30:
                        continue

                    for pattern in self.patterns:
                        matches = re.findall(pattern, text)
                        for match in matches:
                            bbox = span["bbox"]
                            results.append({
                                "text": match.strip(),
                                "x": (bbox[0] + bbox[2]) / 2,
                                "y": (bbox[1] + bbox[3]) / 2,
                                "source": "native"
                            })

        return self._deduplicate(results)

    def _recognize_by_ocr(self, page: fitz.Page):
        try:
            ocr = self._get_ocr_engine()
        except Exception as e:
            print(f"OCR引擎加载失败：{e}")
            return []

        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_bytes = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_bytes))

        result = ocr.ocr(img, cls=False)
        if not result or not result[0]:
            return []

        results = []
        for line in result[0]:
            bbox_points = line[0]
            text = line[1][0]
            confidence = line[1][1]

            if confidence < 0.6:
                continue

            for pattern in self.patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    x_center = (bbox_points[0][0] + bbox_points[2][0]) / 2 / 2
                    y_center = (bbox_points[0][1] + bbox_points[2][1]) / 2 / 2

                    results.append({
                        "text": match.strip(),
                        "x": x_center,
                        "y": page.rect.height - y_center,
                        "source": "ocr"
                    })

        return self._deduplicate(results)

    @staticmethod
    def _deduplicate(results):
        unique = []
        seen = set()
        for item in results:
            key = (round(item["x"], 0), round(item["y"], 0))
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique

    def recognize_all_pages(self, doc: fitz.Document):
        all_results = {}
        for page_num in range(len(doc)):
            page = doc[page_num]
            all_results[page_num] = self.recognize_page(page)
        return all_results