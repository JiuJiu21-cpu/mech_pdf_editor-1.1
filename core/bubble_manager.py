class BubbleStyle:
    def __init__(self):
        self.bubble_radius = 12
        self.font_size = 10
        self.border_color = "#000000"
        self.fill_color = "#ffffff"
        self.text_color = "#000000"


class BubbleManager:
    def __init__(self):
        # 按页码存储气泡：key=页码(int)，value=气泡列表
        self.bubbles = {}
        self.style = BubbleStyle()

    def add_bubble(self, page_num, pdf_x, pdf_y, text, dimension="", tolerance="", remark=""):
        """添加单个气泡，支持扩展字段"""
        if page_num not in self.bubbles:
            self.bubbles[page_num] = []
        
        bubble = {
            "id": len(self.get_all_bubbles()) + 1,
            "page_num": page_num,
            "pdf_x": pdf_x,
            "pdf_y": pdf_y,
            "text": text,
            "dimension": dimension,
            "tolerance": tolerance,
            "remark": remark
        }
        self.bubbles[page_num].append(bubble)
        return bubble

    def get_page_bubbles(self, page_num):
        """获取指定页的所有气泡"""
        return self.bubbles.get(page_num, [])

    def get_all_bubbles(self):
        """获取全文档所有气泡"""
        all_bubbles = []
        for page_list in self.bubbles.values():
            all_bubbles.extend(page_list)
        return all_bubbles

    def get_max_bubble_number(self):
        """获取当前全文档最大的气泡序号，用于跨页延续"""
        all_bubbles = self.get_all_bubbles()
        if not all_bubbles:
            return 0
        try:
            return max(int(b["text"]) for b in all_bubbles if b["text"].isdigit())
        except:
            return 0

    def renumber_page(self, page_num, start_num=1):
        """单页重新编号：从上到下、从左到右排序"""
        if page_num not in self.bubbles:
            return
        # PDF坐标Y轴向上，所以reverse=True实现从上到下排序
        bubbles = sorted(
            self.bubbles[page_num],
            key=lambda b: (b["pdf_y"], b["pdf_x"]),
            reverse=True
        )
        for idx, bubble in enumerate(bubbles):
            bubble["text"] = str(start_num + idx)

    def renumber_all_pages(self):
        """全文档跨页连续重新编号"""
        current_num = 1
        # 按页码从小到大依次编号
        for page_num in sorted(self.bubbles.keys()):
            self.renumber_page(page_num, start_num=current_num)
            current_num += len(self.bubbles[page_num])

    def update_bubble(self, page_num, bubble_id, **kwargs):
        """更新气泡的尺寸、公差等信息"""
        if page_num not in self.bubbles:
            return
        for bubble in self.bubbles[page_num]:
            if bubble["id"] == bubble_id:
                bubble.update(kwargs)
                break

    def clear_page(self, page_num):
        """清空指定页的标注"""
        if page_num in self.bubbles:
            del self.bubbles[page_num]

    def clear_all(self):
        """清空所有标注"""
        self.bubbles.clear()