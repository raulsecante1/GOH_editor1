import sys
import os
import back_end
import shutil
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QScrollArea, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox, 
    QFileDialog, QSplitter, QTabWidget
)
from PySide6.QtGui import QPixmap, QMouseEvent, QCursor
from PySide6.QtCore import Qt, QPoint

#base_img_dir = "./portrait_squad"

STAGE = ["stage_1", "stage_2", "stage_3", "stage_4", "stage_5", "stage_specials"]
STAGE_NAMES = {
    "stage_1": "阶段一",
    "stage_2": "阶段二",
    "stage_3": "阶段三",
    "stage_4": "阶段四",
    "stage_5": "阶段五",
    "stage_specials": "特殊阶段"
}

class DraggableLabel(QLabel):
    def __init__(self, unit_data, pixmap, source_area, controller, parent=None):
        super().__init__(parent)
        self.unit_data = unit_data  # [unit_id, stage, ...rest]
        self.setPixmap(pixmap)
        self.setScaledContents(True)
        self.setFixedSize(pixmap.size())
        self.controller = controller
        self.source_area = source_area
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
        self.controller.on_label_released(self, event.globalPosition().toPoint())

        # Reorder top list if dragged in top
        if self.source_area == "top":
            self.controller.top_labels.sort(
                key=lambda lbl: lbl.pos().x()
            )



class UnitEditor(QWidget):
    def __init__(self, player_units):
        super().__init__()
        self.setWindowTitle("战役库编辑器")

        self.player_units_data = player_units
        self.top_labels = []
        self.stage_labels = {stage: [] for stage in STAGE}

        self.pre = ""
        self.nxt = ""
        self.sav_path = ""
        self.scn_path = ""
        self.status_path = ""

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # --- Top Panel (Player Owned Units - Reorderable) ---
        self.top_area = self.create_scroll_area(horizontal=True)
        self.top_layout = self.top_area.widget().layout()
        for unit in self.player_units_data:
            label = DraggableLabel(unit['full'], unit['pixmap'], "top", self, self.top_area.widget())
            self.top_layout.addWidget(label)
            self.top_labels.append(label)

        splitter.addWidget(self.top_area)

        # --- Bottom Panel (Tabs for stages) ---
        self.tabs = QTabWidget()
        self.stage_layouts = {}
        for stage in STAGE:
            scroll = self.create_scroll_area(horizontal=True)
            self.stage_layouts[stage] = scroll.widget().layout()
            self.tabs.addTab(scroll, STAGE_NAMES.get(stage, stage))

        splitter.addWidget(self.tabs)

        # Save button
        save_btn = QPushButton("保存顺序")
        save_btn.clicked.connect(self.save_all)

        main_layout.addWidget(splitter)
        main_layout.addWidget(save_btn)

        self.populate_stages()

    def create_scroll_area(self, horizontal=True):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QHBoxLayout() if horizontal else QVBoxLayout()
        container.setLayout(layout)
        scroll.setWidget(container)
        return scroll

    def populate_stages(self):
        for label in self.top_labels:
            stage = label.unit_data[1]
            if stage in self.stage_layouts:
                clone = DraggableLabel(label.unit_data, label.pixmap(), stage, self, self.stage_layouts[stage].parent())
                self.stage_layouts[stage].addWidget(clone)
                self.stage_labels[stage].append(clone)

    def on_label_released(self, label, global_pos):
        local_pos = self.mapFromGlobal(global_pos)

        # --- Top Panel Drop ---
        if self.top_area.geometry().contains(local_pos):
            if label.source_area != "top":
                # Moving from stage to top: remove from old stage
                stage = label.source_area
                if label in self.stage_labels[stage]:
                    self.stage_labels[stage].remove(label)
                label.setParent(self.top_area.widget())
                label.source_area = "top"

                # Avoid duplication
                if all(l.unit_data[0] != label.unit_data[0] for l in self.top_labels):
                    self.top_labels.append(label)

            # Sort and realign top labels
            self.top_labels.sort(key=lambda lbl: lbl.pos().x())
            self.realign_layout(self.top_layout, self.top_labels)
            return

        # --- Bottom Panel Drop (into stage tabs) ---
        for stage in STAGE:
            tab_index = STAGE.index(stage)
            stage_widget = self.tabs.widget(tab_index)
            stage_pos = stage_widget.mapFromGlobal(global_pos)

            if stage_widget.rect().contains(stage_pos):
                if label.source_area == "top":
                    # Dragging from top to stage
                    new_data = label.unit_data.copy()
                    new_data[1] = stage
                    new_label = DraggableLabel(new_data, label.pixmap(), stage, self, self.stage_layouts[stage].parent())
                    self.stage_layouts[stage].addWidget(new_label)
                    self.stage_labels[stage].append(new_label)

                    # Update internal data
                    for unit in self.player_units_data:
                        if unit['id'] == new_data[0]:
                            unit['full'][1] = stage
                            break
                    self.realign_layout(self.top_layout, self.top_labels)

                elif label.source_area in STAGE:
                    if label.source_area != stage:
                        # Move between stages
                        self.stage_labels[label.source_area].remove(label)
                        label.setParent(None)
                        label.unit_data[1] = stage
                        new_label = DraggableLabel(label.unit_data, label.pixmap(), stage, self, self.stage_layouts[stage].parent())
                        self.stage_layouts[stage].addWidget(new_label)
                        self.stage_labels[stage].append(new_label)

                else:
                    # Dropped into same stage — realign to avoid overlap
                    self.realign_layout(self.stage_layouts[stage], self.stage_labels[stage])
                return

        # If not dropped anywhere useful, just realign top
        self.realign_layout(self.top_layout, self.top_labels)


    def realign_layout(self, layout, labels):
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)
        for lbl in labels:
            layout.addWidget(lbl)

    def save_all(self):
        try:
            # Top panel order
            full_order = [lbl.unit_data for lbl in self.top_labels]
            back_end.modify_campaign_scn(self.scn_path, full_order, self.pre, self.nxt)
            back_end.save_changes(self.sav_path, self.scn_path, self.status_path)
            QMessageBox.information(self, "保存", "顺序已保存并写入 .sav 文件")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败:\n{e}")

def resource_path(relative_path):
    #Get absolute path to resource, used for PyInstaller
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)


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
    base_img_dir = resource_path("portrait_squad")
    for ext in extensions:
        path = os.path.join(base_img_dir, f"{unit_id}{ext}")
        if os.path.exists(path):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                return pixmap

    #fallback pixmap if image not found or failed to load
    print(f"[DEBUG] no image found or failed to load: {unit_id}")
    fallback = QPixmap(*fallback_size)
    fallback.fill(Qt.GlobalColor.darkGray)
    return fallback


def main():
    app = QApplication(sys.argv)

    sav_path, _ = QFileDialog.getOpenFileName(
        None,
        "选择战役存档文件",
        ".",
        "Save Files (*.sav)"
    )

    if not sav_path:
        print("cancelled, and exited")
        return


    #save_path = back_end.get_path(save_name)

    ext_dir = back_end.unzip_sav(sav_path)
    scn_path = os.path.join(ext_dir, "campaign.scn")
    lines, pre, nxt = back_end.read_armory(scn_path)
    #save_changes(save_path)

    units = [{'id': line[0], 'stage': line[1], 'pixmap': load_pic(line[0]), 'full': line} for line in lines]

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
