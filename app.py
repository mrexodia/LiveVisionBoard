import sys
import os

from PySide6.QtCore import (
    QMimeDatabase,
    QUrl,
    Qt,
    QSize,
)
from PySide6.QtGui import (
    QDragEnterEvent,
    QDropEvent,
    QGuiApplication,
)
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QBoxLayout,
    QVBoxLayout,
    QHBoxLayout,
    QSpacerItem,
    QWidget,
    QListWidget,
    QGraphicsView,
    QLabel,
    QPushButton,
    QListWidgetItem,
)


class AspectRatioWidget(QWidget):
    def __init__(self, widget, parent=None):
        super().__init__(parent)
        self.aspect_ratio = widget.size().width() / widget.size().height()
        #  add spacer, then widget, then spacer
        layout = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addItem(QSpacerItem(0, 0))
        layout.addWidget(widget)
        layout.addItem(QSpacerItem(0, 0))
        self.setLayout(layout)

    def resizeEvent(self, e):
        w = e.size().width()
        h = e.size().height()

        if w / h > self.aspect_ratio:  # too wide
            self.layout().setDirection(QBoxLayout.Direction.LeftToRight)
            widget_stretch = h * self.aspect_ratio
            outer_stretch = (w - widget_stretch) / 2 + 0.5
        else:  # too tall
            self.layout().setDirection(QBoxLayout.Direction.TopToBottom)
            widget_stretch = w / self.aspect_ratio
            outer_stretch = (h - widget_stretch) / 2 + 0.5

        self.layout().setStretch(0, outer_stretch)
        self.layout().setStretch(1, widget_stretch)
        self.layout().setStretch(2, outer_stretch)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("MusicSlides")
        self.resize(1200, 520)
        self.move(QGuiApplication.primaryScreen().geometry().center() - self.frameGeometry().center())
        self.setAcceptDrops(True)

        self.mimedb = QMimeDatabase()

        self.list_images = QListWidget()
        self.list_images.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.list_images.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list_images.itemSelectionChanged.connect(self.onListSelection)

        self.preview = QGraphicsView()
        self.preview.resize(1920, 1080)

        layout_list_label = QVBoxLayout()
        layout_list_label.setSpacing(4)
        layout_list_label.setContentsMargins(0, 0, 0, 0)
        layout_list_label.addWidget(QLabel("Images:"))
        layout_list_label.addWidget(self.list_images)

        self.button_add = QPushButton("+")
        self.button_add.clicked.connect(self.onImageAdd)
        self.button_add.setToolTip("Add new image")
        self.button_remove = QPushButton("-")
        self.button_remove.clicked.connect(self.onImageRemove)
        self.button_remove.setToolTip("Remove selected image")
        self.button_up = QPushButton("↑")
        self.button_up.setToolTip("Move selected image up")
        self.button_up.clicked.connect(self.onImageUp)
        self.button_down = QPushButton("↓")
        self.button_down.setToolTip("Move selected image down")
        self.button_down.clicked.connect(self.onImageDown)

        layout_list_buttons = QVBoxLayout()
        layout_list_buttons.setSpacing(4)
        layout_list_buttons.setContentsMargins(0, 0, 0, 0)
        layout_list_buttons.addStretch()
        layout_list_buttons.addWidget(self.button_add)
        layout_list_buttons.addWidget(self.button_remove)
        layout_list_buttons.addSpacing(10)
        layout_list_buttons.addWidget(self.button_up)
        layout_list_buttons.addWidget(self.button_down)
        layout_list_buttons.addStretch()

        layout_list = QHBoxLayout()
        layout_list.setContentsMargins(0, 0, 0, 0)
        layout_list.addLayout(layout_list_label)
        layout_list.addLayout(layout_list_buttons)

        self.button_generate = QPushButton("Generate")
        self.button_generate.clicked.connect(self.onGenerate)

        layout_preview_buttons = QHBoxLayout()
        layout_preview_buttons.setSpacing(4)
        layout_preview_buttons.setContentsMargins(0, 0, 0, 0)
        layout_preview_buttons.addStretch(0)
        layout_preview_buttons.addWidget(self.button_generate)
        layout_preview_buttons.addStretch(0)

        layout_preview = QVBoxLayout()
        layout_preview.setSpacing(3)
        layout_preview.setContentsMargins(0, 0, 0, 0)
        layout_preview.addWidget(AspectRatioWidget(self.preview))
        layout_preview.addLayout(layout_preview_buttons)

        layout_main = QHBoxLayout()
        layout_main.setContentsMargins(7, 7, 7, 7)
        layout_main.setSpacing(3)
        layout_main.addLayout(layout_list)
        layout_main.addLayout(layout_preview)
        layout_main.setStretch(0, 30)
        layout_main.setStretch(1, 70)

        central = QWidget()
        central.setLayout(layout_main)
        self.setCentralWidget(central)

        self.counter = 0

    def get_accepted_urls(self, urls: list[QUrl]):
        result: list[QUrl] = []
        for url in urls:
            if self.mimedb.mimeTypeForUrl(url).name().startswith("image/"):
                result.append(url)
        return result

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        accepted_urls = self.get_accepted_urls(event.mimeData().urls())
        if len(accepted_urls) > 0:
            event.accept()
        else:
            event.ignore()

    def add_image(self, path: str):
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, path)
        item.setText(os.path.basename(path))
        index = self.list_images.count()
        self.list_images.addItem(item)
        return index

    def dropEvent(self, event: QDropEvent) -> None:
        accepted_urls = self.get_accepted_urls(event.mimeData().urls())
        last_index = None
        for url in accepted_urls:
            last_index = self.add_image(url.path())
        if last_index is not None:
            self.list_images.setCurrentRow(last_index)

    def onListSelection(self):
        row = self.list_images.currentRow()
        print(f"selected row: {row}")
        if row == -1:
            print("  <no selection>")
        else:
            item = self.list_images.item(row)
            path: str = item.data(Qt.ItemDataRole.UserRole)
            print(f"  path: {path}")

    def onImageAdd(self):
        self.counter += 1
        self.list_images.addItem(f"slide{self.counter:03}.jpg")

    def onImageRemove(self):
        row_num = self.list_images.currentRow()
        if row_num >= 0:
            item = self.list_images.takeItem(row_num)
            del item

    def onImageUp(self):
        row_num = self.list_images.currentRow()
        if row_num > 0:
            row = self.list_images.itemWidget(self.list_images.currentItem())
            itemN = self.list_images.currentItem().clone()

            self.list_images.insertItem(row_num - 1, itemN)
            self.list_images.setItemWidget(itemN, row)

            self.list_images.takeItem(row_num + 1)
            self.list_images.setCurrentRow(row_num - 1)

    def onImageDown(self):
        row_num = self.list_images.currentRow()
        if row_num >= 0 and row_num +1 < self.list_images.count():
            row = self.list_images.itemWidget(self.list_images.currentItem())
            itemN = self.list_images.currentItem().clone()

            self.list_images.insertItem(row_num + 2, itemN)
            self.list_images.setItemWidget(itemN, row)

            self.list_images.takeItem(row_num)
            self.list_images.setCurrentRow(row_num+1)

    def onGenerate(self):
        pass


def main():
    app = QApplication(sys.argv)
    main = MainWindow()
    main.show()
    main.raise_()
    app.exec()


if __name__ == "__main__":
    main()