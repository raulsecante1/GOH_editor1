import sys
import os
import back_end
import shutil
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QScrollArea, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox, 
    QFileDialog
)
from PySide6.QtGui import QPixmap, QMouseEvent, QCursor
from PySide6.QtCore import Qt, QPoint

#base_img_dir = "./portrait_squad"

class DraggableLabel(QLabel):
    def __init__(self, unit_data, pixmap, controller, parent=None):
        super().__init__(parent)
        self.unit_data = unit_data
        self.setPixmap(pixmap)
        self.controller = controller
        self.setScaledContents(True)
        self.setFixedSize(pixmap.size())
        self.drag_start_pos = None

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.position()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton:
            new_pos = self.mapToParent(event.position().toPoint() - self.drag_start_pos.toPoint())
            self.move(new_pos)
            self.raise_()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            self.grabMouse()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.releaseMouse()
        self.controller.on_label_released(self)


class UnitEditor(QWidget):
    def __init__(self, units):
        super().__init__()
        self.setWindowTitle("战役库编辑器")
        self.units = units
        self.labels = []
        self.pre = ""
        self.nxt = ""
        self.sav_path = ""
        self.scn_path = ""
        self.status_path = ""

        main_layout = QVBoxLayout(self)

        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        container = QWidget()
        self.unit_layout = QHBoxLayout(container)
        self.unit_layout.setSpacing(10)
        scroll_area.setWidget(container)

        # Load all unit labels into scroll area
        for unit in self.units:
            label = DraggableLabel(unit['full'], unit['pixmap'], self, container)
            self.unit_layout.addWidget(label)
            self.labels.append(label)

        # Add Save button
        save_btn = QPushButton("保存顺序")
        save_btn.clicked.connect(self.save_order)

        main_layout.addWidget(scroll_area)
        main_layout.addWidget(save_btn)

    def on_label_released(self, label):
        # Sort based on X position (horizontal layout)
        self.labels.sort(key=lambda l: l.x())
        for i, lbl in enumerate(self.labels):
            lbl.move(i * (lbl.width() + 10), 0)

    def save_order(self):
        full_order = [lbl.unit_data for lbl in self.labels]

        try:
            back_end.modify_campaign_scn(self.scn_path, full_order, self.pre, self.nxt)
            back_end.save_changes(self.sav_path, self.scn_path, self.status_path)
            QMessageBox.information(self, "保存", "顺序已保存并写入 .sav 文件")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败:\n{e}")



def load_pic(unit_id, fallback_size=(100, 100)):
    '''
    Used to load the portraits, since there are of png and tga
    If no image found, returns a gray QPixmap as fallback.

    Args:
        unit_id (str): portrait´s name
    Returns:
        path (QPixmap): the QPixmap of the image
    '''
    extensions = [".png", ".tga"]
    base_dir = resource_path("portrait_squad")
    for ext in extensions:
        path = os.path.join(base_dir, f"{unit_id}{ext}")
        if os.path.exists(path):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                return pixmap

    #fallback pixmap if image not found or failed to load
    print(f"[DEBUG] no image found or failed to load: {unit_id}")
    fallback = QPixmap(*fallback_size)
    fallback.fill(Qt.GlobalColor.darkGray)
    return fallback

def resource_path(relative_path):
    #Get absolute path to resource, used for PyInstaller
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)

def main():
    app = QApplication(sys.argv)

    sav_path, _ = QFileDialog.getOpenFileName(
        None,
        "选择战役存档文件",
        ".",
        "Save Files (*.sav)"
    )

    if not sav_path:
        print("用户取消选择存档，程序退出")
        return


    #save_path = back_end.get_path(save_name)

    ext_dir = back_end.unzip_sav(sav_path)
    scn_path = os.path.join(ext_dir, "campaign.scn")
    lines, pre, nxt = back_end.read_armory(scn_path)
    #save_changes(save_path)

    units = [{'id': line[0], 'stages': line[1], 'pixmap': load_pic(line[0]), 'full': line} for line in lines]

    editor = UnitEditor(units)
    editor.pre = pre
    editor.nxt = nxt
    editor.sav_path = sav_path
    editor.scn_path = scn_path
    editor.status_path = os.path.join(ext_dir, "status")
    editor.resize(800, 250)
    editor.show()

    #delete the unnecessary archive
    def cleanup():
        try:
            shutil.rmtree(ext_dir)
            print(f"Deleted extracted folder: {ext_dir}")
        except Exception as e:
            print(f"Failed to delete folder {ext_dir}: {e}")

    app.aboutToQuit.connect(cleanup)

    sys.exit(app.exec())
    

if __name__ == "__main__":
    main()
