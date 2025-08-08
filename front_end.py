import sys
import os
import back_end
import shutil
import json
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QScrollArea, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox, 
    QFileDialog, QSplitter, QTabWidget, QComboBox
)
from PySide6.QtGui import QPixmap, QMouseEvent, QCursor
from PySide6.QtCore import Qt, QPoint

#base_img_dir = "./portrait_squad"

STAGE = ["stage_1", "stage_2", "stage_3", "stage_4", "stage_5", "stage_specials"]

class DraggableLabel(QWidget):
    def __init__(self, unit_data, pixmap, source_area, controller, parent=None):
        super().__init__(parent)
        self.unit_data = unit_data  # e.g. [unit_id, stage, ...]
        self.controller = controller
        self.source_area = source_area
        self._pixmap = pixmap

        # Setup fixed size to fit image + name label (adjust height as needed)
        self.setFixedSize(pixmap.width(), pixmap.height() + 20)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Image label
        self.image_label = QLabel()
        self.image_label.setPixmap(pixmap)
        self.image_label.setScaledContents(True)
        self.image_label.setFixedSize(pixmap.size())

        # Name label under the image
        self.name_label = QLabel()
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setFixedHeight(20)
        self.update_name()  # set initial squad name

        layout.addWidget(self.image_label)
        layout.addWidget(self.name_label)

        self.drag_start_pos = None

    def update_name(self):
        unit_id = self.unit_data[0]
        squad = self.controller.squads_data.get(unit_id)
        if squad:
            lang = self.controller.current_language
            if lang == "zh":
                name = squad.get("name_cn", unit_id)
            elif lang == "en":
                name = squad.get("name_en", unit_id)
            elif lang == "es":
                name = squad.get("name_es", unit_id)
            else:
                name = unit_id
        else:
            name = unit_id
        self.name_label.setText(name)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.position()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            new_pos = self.mapToParent(event.position().toPoint() - self.drag_start_pos.toPoint())
            self.move(new_pos)
            self.raise_()
            self.setCursor(QCursor(Qt.ClosedHandCursor))
            self.grabMouse()

    def mouseReleaseEvent(self, event):
        self.setCursor(QCursor(Qt.ArrowCursor))
        self.releaseMouse()
        self.controller.on_label_released(self, event.globalPosition().toPoint())

    def pixmap(self):
        return self._pixmap



class UnitEditor(QWidget):
    def __init__(self, player_units):
        super().__init__()

        # Load localization file
        with open(resource_path("localization.json"), "r", encoding="utf-8") as f:
            self.translations = json.load(f)

        with open(resource_path("squads.json"), "r", encoding="utf-8") as f:
            self.squads_data = json.load(f)

        self.current_language = "zh"  # default language Chinese

        self.setWindowTitle(self.tr("window_title"))

        self.player_units_data = player_units
        self.top_labels = []
        self.stage_labels = {stage: [] for stage in STAGE}

        self.pre = ""
        self.nxt = ""
        self.sav_path = ""
        self.scn_path = ""
        self.status_path = ""

        self.init_ui()

    def tr(self, key, **kwargs):
        text = self.translations.get(key, {}).get(self.current_language, key)
        if kwargs:
            return text.format(**kwargs)
        return text

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # Language selector at the top-left
        top_bar = QHBoxLayout()
        from PySide6.QtWidgets import QComboBox, QLabel
        self.lang_label = QLabel(self.tr("label_language"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["中文", "English", "Español"])
        self.lang_combo.setCurrentIndex(["zh", "en", "es"].index(self.current_language))
        self.lang_combo.currentIndexChanged.connect(self.change_language)
        
        top_bar.addWidget(self.lang_label)
        top_bar.addWidget(self.lang_combo)
        top_bar.addStretch(1)
        main_layout.addLayout(top_bar)

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
            self.tabs.addTab(scroll, self.tr(f"tab_{stage}"))

        splitter.addWidget(self.tabs)

        # Save button
        self.save_btn = QPushButton(self.tr("btn_save_order"))
        self.save_btn.clicked.connect(self.save_all)

        btn_layout = QHBoxLayout()
        self.export_btn = QPushButton(self.tr("btn_export_layout"))
        self.export_btn.clicked.connect(self.export_layout)
        self.import_btn = QPushButton("导入布局")
        self.import_btn.clicked.connect(self.import_layout)

        btn_layout.addWidget(self.import_btn)
        btn_layout.addWidget(self.export_btn)
        
        main_layout.addLayout(btn_layout)
        main_layout.addWidget(splitter)
        main_layout.addWidget(self.save_btn)

        self.populate_stages()

    def change_language(self, index):
        lang_codes = ["zh", "en", "es"]
        self.current_language = lang_codes[index]

        # Update window title
        self.setWindowTitle(self.tr("window_title"))

        # Update all UI texts
        self.save_btn.setText(self.tr("btn_save_order"))
        self.export_btn.setText(self.tr("btn_export_layout"))
        self.import_btn.setText(self.tr("btn_import_layout"))

        self.tabs.setTabText(0, self.tr("tab_stage_1"))
        self.tabs.setTabText(1, self.tr("tab_stage_2"))
        self.tabs.setTabText(2, self.tr("tab_stage_3"))
        self.tabs.setTabText(3, self.tr("tab_stage_4"))
        self.tabs.setTabText(4, self.tr("tab_stage_5"))
        self.tabs.setTabText(5, self.tr("tab_stage_specials"))

        # Update language label
        self.lang_label.setText(self.tr("label_language"))

        for label in self.top_labels:
            label.update_name()

        for stage in STAGE:
            for label in self.stage_labels[stage]:
                label.update_name()

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

    def export_layout(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("btn_export_layout"),
            ".",
            "Scenario Files (*.scn)"
        )
        if not path:
            return

        try:
            shutil.copyfile(self.scn_path, path)
            QMessageBox.information(self, self.tr("btn_export_layout"), self.tr("msg_export_success", path=path))
        except Exception as e:
            QMessageBox.critical(self, self.tr("btn_export_layout"), f"{self.tr('msg_export_error')}\n{e}")


    def import_layout(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("btn_import_layout"),
            ".",
            "Scenario Files (*.scn)"
        )
        if not path:
            return

        try:
            # re-read everything
            lines, pre, nxt = back_end.read_armory(path)

            # update data
            self.player_units_data.clear()
            self.top_labels.clear()
            for stage in STAGE:
                self.stage_labels[stage].clear()
                self.clear_layout(self.stage_layouts[stage])

            self.clear_layout(self.top_layout)

            for line in lines:
                unit = {'id': line[0], 'stage': line[1], 'pixmap': load_pic(line[0]), 'full': line}
                self.player_units_data.append(unit)

                label = DraggableLabel(unit['full'], unit['pixmap'], "top", self, self.top_area.widget())
                self.top_layout.addWidget(label)
                self.top_labels.append(label)

            self.pre = pre
            self.nxt = nxt
            #self.scn_path = path  # optional: use this as new base for saving
            self.populate_stages()

            QMessageBox.information(self, self.tr("btn_import_layout"), self.tr("msg_import_success", path=path))
        except Exception as e:
            QMessageBox.critical(self, self.tr("btn_import_layout"), f"{self.tr('msg_import_error')}\n{e}")


    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()



    def save_all(self):
        try:
            # Top panel order
            save_order = []
            for label in self.top_labels:
                unit_data = label.unit_data.copy()
                found_in_stage = False
                for stage, labels in self.stage_labels.items():
                    if any(l.unit_data[0] == unit_data[0] for l in labels):
                        unit_data[1] = stage
                        found_in_stage = True
                        break
                if not found_in_stage:
                    unit_data[1] = ""
                save_order.append(unit_data)
          
            back_end.modify_campaign_scn(self.scn_path, save_order, self.pre, self.nxt)
            back_end.save_changes(self.sav_path, self.scn_path, self.status_path)
            QMessageBox.information(self, self.tr("window_title"), self.tr("msg_save_success"))
        except Exception as e:
            QMessageBox.critical(self, self.tr("window_title"), f"{self.tr('msg_save_error')}\n{e}")

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
