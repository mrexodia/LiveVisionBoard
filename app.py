import sys
import os

from PySide6.QtCore import (
    QMimeDatabase,
    QObject,
    QUrl,
    Qt,
    QSize,
    QPoint,
    QRectF,
    QSettings,
    QTimer,
    QThread,
)
from PySide6.QtGui import (
    QDragEnterEvent,
    QDropEvent,
    QGuiApplication,
    QImageReader,
    QPixmap,
    QPainter,
    QResizeEvent,
    QDesktopServices,
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
    QLabel,
    QPushButton,
    QListWidgetItem,
    QFileDialog,
    QMessageBox,
    QSizePolicy,
    QGraphicsBlurEffect,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QDoubleSpinBox,
)
from PySide6.QtMultimedia import (
    QMediaPlayer,
    QAudioOutput,
    QAudioDevice,
)


def generate_video(images: list[str], duration: float, music: str, output: str):
    print(f"generate_video({repr(images)}, {repr(duration)}, {repr(music)}, {repr(output)})")
    import time
    time.sleep(5)
    return "Not implemented!"


class GenerateVideoThread(QThread):
    def __init__(self, parent: QObject = None) -> None:
        super().__init__(parent)
        self.images: list[str] = []
        self.duration = 0.0
        self.music = ""
        self.output = ""
        self.error: str = None

    def run(self):
        self.error = generate_video(self.images, self.duration, self.music, self.output)


class AspectRatioWidget(QWidget):
    def __init__(self, widget: QWidget, parent: QWidget = None):
        super().__init__(parent)
        self.aspect_ratio = widget.size().width() / widget.size().height()
        # add spacer, then widget, then spacer
        layout = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addItem(QSpacerItem(0, 0))
        layout.addWidget(widget)
        layout.addItem(QSpacerItem(0, 0))
        self.setLayout(layout)

    def resizeEvent(self, event: QResizeEvent):
        w = event.size().width()
        h = event.size().height()

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


class DoubleSpinBox(QDoubleSpinBox):
    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

    def textFromValue(self, val: float) -> str:
        return f"{{:.{self.decimals()}f}}".format(val)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle(QApplication.applicationName())
        self.resize(1200, 520)
        self.move(QGuiApplication.primaryScreen().geometry().center() - self.frameGeometry().center())
        self.setAcceptDrops(True)

        self.mimedb = QMimeDatabase()
        self.settings = QSettings()
        self._music_dir = self.settings.value("music_dir", "")
        self._image_dir = self.settings.value("image_dir", "")
        self.is_previewing = False
        self.preview_selection = -1
        self.timer_preview = QTimer(self)
        self.timer_preview.timeout.connect(self.onTimeout)
        self.timer_resize = QTimer(self)
        self.timer_resize.setSingleShot(True)
        self.timer_resize.timeout.connect(self.onListSelection)
        self.music_file = ""
        self.image_cache: dict[str, QPixmap] = {}
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(QAudioOutput(QAudioDevice(), self))
        self.player.audioOutput()  # NOTE: without this audio doesn't play
        self.thread_generate = GenerateVideoThread(self)
        self.thread_generate.finished.connect(self.onFinished)

        self.list_images = QListWidget()
        self.list_images.setDragEnabled(True)
        self.list_images.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.list_images.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list_images.setIconSize(QSize(120, 68))
        self.list_images.itemSelectionChanged.connect(self.onListSelection)

        self.label_image = QLabel()
        self.label_image.resize(1920, 1080)
        self.label_image.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.label_image.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.button_clear = QPushButton(self.tr("Clear"))
        self.button_clear.clicked.connect(self.onImageClear)
        self.button_clear.setToolTip(self.tr("Remove all images"))

        layout_list_bottom = QHBoxLayout()
        layout_list_bottom.setSpacing(4)
        layout_list_bottom.setContentsMargins(0, 0, 0, 0)
        layout_list_bottom.addStretch()
        layout_list_bottom.addWidget(self.button_clear)

        layout_list_label = QVBoxLayout()
        layout_list_label.setSpacing(4)
        layout_list_label.setContentsMargins(0, 0, 0, 0)
        layout_list_label.addWidget(QLabel(self.tr("Images:")))
        layout_list_label.addWidget(self.list_images)
        layout_list_label.addLayout(layout_list_bottom)

        self.button_add = QPushButton("+")
        self.button_add.clicked.connect(self.onImageAdd)
        self.button_add.setToolTip(self.tr("Add new image after selection"))
        self.button_remove = QPushButton("-")
        self.button_remove.clicked.connect(self.onImageRemove)
        self.button_remove.setToolTip(self.tr("Remove selected image"))
        self.button_up = QPushButton("↑")
        self.button_up.setToolTip(self.tr("Move selected image up"))
        self.button_up.clicked.connect(self.onImageUp)
        self.button_down = QPushButton("↓")
        self.button_down.setToolTip(self.tr("Move selected image down"))
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

        self.label_time = QLabel(self.tr("Duration:"))
        self.spin_duration = DoubleSpinBox()
        self.spin_duration.setToolTip(self.tr("Seconds per slide"))
        self.spin_duration.setRange(0.1, 60.0)
        self.spin_duration.setSingleStep(0.1)
        self.spin_duration.setValue(1.0)
        self.spin_duration.setSuffix("s")
        self.spin_duration.setDecimals(1)
        self.button_music = QPushButton(self.tr("Music"))
        self.button_music.setToolTip(self.tr("Select background music file"))
        self.button_music.clicked.connect(self.onMusic)
        self.label_music = QLabel("")
        self.button_music_remove = QPushButton("✖")
        self.button_music_remove.setToolTip(self.tr("Remove selected music"))
        self.button_music_remove.clicked.connect(self.onMusicRemove)
        self.button_preview = QPushButton()
        self.button_preview.clicked.connect(self.onPreview)
        self.button_generate = QPushButton(self.tr("Save Video"))
        self.button_generate.clicked.connect(self.onGenerate)

        layout_preview_buttons = QHBoxLayout()
        layout_preview_buttons.setSpacing(4)
        layout_preview_buttons.setContentsMargins(0, 0, 0, 0)
        layout_preview_buttons.addWidget(self.label_time)
        layout_preview_buttons.addWidget(self.spin_duration)
        layout_preview_buttons.addWidget(self.button_music)
        layout_preview_buttons.addWidget(self.label_music)
        layout_preview_buttons.addWidget(self.button_music_remove)
        layout_preview_buttons.addStretch(0)
        layout_preview_buttons.addWidget(self.button_preview)
        layout_preview_buttons.addWidget(self.button_generate)

        layout_preview = QVBoxLayout()
        layout_preview.setSpacing(3)
        layout_preview.setContentsMargins(0, 0, 0, 0)
        layout_preview.addWidget(AspectRatioWidget(self.label_image))
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

        self.update_buttons()

    @property
    def music_dir(self):
        return self._music_dir

    @music_dir.setter
    def music_dir(self, value):
        self._music_dir = value
        self.settings.setValue("music_dir", value)
        self.settings.sync()
        if not self.image_dir:
            self.image_dir = value

    @property
    def image_dir(self):
        return self._image_dir

    @image_dir.setter
    def image_dir(self, value):
        self._image_dir = value
        self.settings.setValue("image_dir", value)
        self.settings.sync()
        if not self.music_dir:
            self.music_dir = value

    def update_buttons(self):
        editing = not self.is_previewing
        count = self.list_images.count()
        row = self.list_images.currentRow()
        self.list_images.setEnabled(editing)
        self.button_clear.setEnabled(editing and count > 0)
        self.button_generate.setEnabled(editing and count > 0)
        self.button_preview.setEnabled(count > 0)
        preview_text = self.tr("Stop") if self.is_previewing else self.tr("Preview")
        self.button_preview.setText(preview_text)
        self.button_add.setEnabled(editing)
        self.button_remove.setEnabled(editing and row != -1)
        self.button_up.setEnabled(editing and row > 0)
        self.button_down.setEnabled(editing and row + 1 < count)
        self.spin_duration.setEnabled(editing)
        self.button_music.setEnabled(editing)
        self.button_music_remove.setVisible(len(self.music_file) > 0)
        self.button_music_remove.setEnabled(editing)

    def read_image_cache(self, path: str):
        if path in self.image_cache:
            return self.image_cache[path]
        reader = QImageReader(path)
        if not reader.canRead():
            raise Exception(reader.errorString())
        pixmap = QPixmap.fromImageReader(reader)
        self.image_cache[path] = pixmap
        # Evict images from the cache
        if len(self.image_cache) > 20:
            first_key = None
            for key in self.image_cache:
                first_key = key
                break
            del self.image_cache[first_key]
        return pixmap

    def read_image(self, path: str, size: QSize):
        pixmap = self.read_image_cache(path)

        # Blur the stretched for the background
        blurred = pixmap.scaled(size)
        blurred = self.blur_image(blurred, 50)
        blurred = self.blur_image(blurred, 20)

        # Resize the main image
        if pixmap.height() > size.height():
            pixmap = pixmap.scaledToHeight(size.height(), Qt.TransformationMode.SmoothTransformation)
        if pixmap.width() > size.width():
            pixmap = pixmap.scaledToWidth(size.width(), Qt.TransformationMode.SmoothTransformation)

        # Draw the final result
        result = QPixmap(size)
        result.fill(Qt.GlobalColor.transparent)
        with QPainter(result) as painter:
            painter.drawPixmap(QPoint(0, 0), blurred)
            midx = (size.width() / 2) - (pixmap.width() / 2)
            midy = (size.height() / 2) - (pixmap.height() / 2)
            painter.drawPixmap(QPoint(midx, midy), pixmap)
        return result

    def add_image(self, path: str):
        try:
            icon_size = self.list_images.iconSize()
            icon = self.read_image(path, icon_size)
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setText(os.path.basename(path))
            item.setIcon(icon)
            row = self.list_images.currentRow() + 1
            self.list_images.insertItem(row, item)
            self.list_images.setCurrentRow(row)
        except Exception as x:
            QMessageBox.critical(
                self,
                self.tr("Error"),
                self.tr("{0}\n\n{1}").format(
                    str(x),
                    path,
                ),
            )

    def add_images(self, paths: list[str]):
        self.list_images.setUpdatesEnabled(False)
        for path in paths:
            self.add_image(path)
        self.list_images.setUpdatesEnabled(True)
        self.onListSelection()

    def blur_image(self, pixmap: QPixmap, radius: float):
        scene = QGraphicsScene()
        item = QGraphicsPixmapItem()
        item.setPixmap(pixmap)
        blur = QGraphicsBlurEffect(scene)
        blur.setBlurRadius(radius)
        blur.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
        item.setGraphicsEffect(blur)
        scene.addItem(item)
        blurred = QPixmap(pixmap.size())
        blurred.fill(Qt.GlobalColor.transparent)
        with QPainter(blurred) as painter:
            scene.render(painter, QRectF(), QRectF(0, 0, pixmap.width(), pixmap.height()))
        return blurred

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

    def dropEvent(self, event: QDropEvent) -> None:
        accepted_urls = self.get_accepted_urls(event.mimeData().urls())
        self.add_images([url.path() for url in accepted_urls])

    def resizeEvent(self, event: QResizeEvent) -> None:
        # Resize the image with a debounce
        self.label_image.setPixmap(QPixmap())
        self.timer_resize.start(250)

    def onListSelection(self):
        if not self.list_images.updatesEnabled():
            return

        row = self.list_images.currentRow()
        if row == -1:
            self.label_image.setPixmap(QPixmap())
        else:
            item = self.list_images.item(row)
            path: str = item.data(Qt.ItemDataRole.UserRole)
            try:
                preview = self.read_image(path, self.label_image.size())
                self.label_image.setPixmap(preview)
            except Exception as x:
                QMessageBox.critical(
                    self,
                    self.tr("Error"),
                    self.tr("{0}\n\n{1}").format(
                        str(x),
                        path
                    )
                )
        self.update_buttons()

    def onImageClear(self):
        if self.list_images.count() > 0 and QMessageBox.question(
            self,
            self.tr("Confirm"),
            self.tr("Are you sure you want to remove all images?"),
            QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes:
            self.list_images.clear()
            self.onListSelection()
            self.update_buttons()

    def onImageAdd(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            self.tr("Open Image"),
            self.image_dir,
            self.tr("Image files (*.jpg *.jpeg *.png)")
        )
        if len(paths) > 0:
            self.image_dir = os.path.dirname(paths[0])
        self.add_images(paths)

    def onImageRemove(self):
        row_num = self.list_images.currentRow()
        if row_num >= 0:
            item = self.list_images.takeItem(row_num)
            del item
        self.update_buttons()

    def onImageUp(self):
        row_num = self.list_images.currentRow()
        if row_num > 0:
            row = self.list_images.itemWidget(self.list_images.currentItem())
            itemN = self.list_images.currentItem().clone()

            self.list_images.insertItem(row_num - 1, itemN)
            self.list_images.setItemWidget(itemN, row)

            self.list_images.takeItem(row_num + 1)
            self.list_images.setCurrentRow(row_num - 1)
        self.update_buttons()

    def onImageDown(self):
        row_num = self.list_images.currentRow()
        if row_num >= 0 and row_num +1 < self.list_images.count():
            row = self.list_images.itemWidget(self.list_images.currentItem())
            itemN = self.list_images.currentItem().clone()

            self.list_images.insertItem(row_num + 2, itemN)
            self.list_images.setItemWidget(itemN, row)

            self.list_images.takeItem(row_num)
            self.list_images.setCurrentRow(row_num+1)
        self.update_buttons()

    def onMusic(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select music"),
            self.music_dir,
            self.tr("Music files (*.mp3 *.wav *.m4a *.wma *.aac)")
        )
        if not path:
            return

        self.music_file = path
        self.music_dir = os.path.dirname(path)
        self.label_music.setText(os.path.basename(path))
        self.update_buttons()

    def onMusicRemove(self):
        self.music_file = ""
        self.label_music.setText("")
        self.update_buttons()

    def onPreview(self):
        self.is_previewing = not self.is_previewing
        if self.is_previewing:
            if self.music_file:
                self.player.setSource(QUrl.fromLocalFile(self.music_file))
                self.player.play()
            self.preview_selection = self.list_images.currentRow()
            self.list_images.setCurrentRow(0)
            self.timer_preview.start(int(self.spin_duration.value() * 1000) + 50)
        else:
            self.player.stop()
            self.timer_preview.stop()
            self.list_images.setCurrentRow(self.preview_selection)
            self.list_images.setFocus()
        self.update_buttons()

    def onTimeout(self):
        row = self.list_images.currentRow() + 1
        if row  == self.list_images.count():
            self.player.stop()
            self.timer_preview.stop()
            self.is_previewing = False
            self.update_buttons()
            self.list_images.setCurrentRow(self.preview_selection)
            self.list_images.setFocus()
        else:
            self.list_images.setCurrentRow(row)

    def onGenerate(self):
        output, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save video (MP4)"),
            self.image_dir,
            self.tr("Video file (*.mp4)")
        )
        if not output:
            return

        self.setWindowTitle(self.tr("{} (saving video)").format(QApplication.applicationName()))
        self.setEnabled(False)

        images = [self.list_images.item(row).data(Qt.ItemDataRole.UserRole) for row in range(self.list_images.count())]
        self.thread_generate.images = images
        self.thread_generate.duration = self.spin_duration.value()
        self.thread_generate.music = self.music_file
        self.thread_generate.output = output
        self.thread_generate.start()

    def onFinished(self):
        self.setEnabled(True)
        self.setWindowTitle(QApplication.applicationName())

        error = self.thread_generate.error
        if error is None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.thread_generate.output))
        else:
            QMessageBox.critical(
                self,
                self.tr("Error"),
                self.tr("Video creation failed:\n\n{}").format(error)
            )


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName("Ogilvie")
    app.setOrganizationDomain("ogilvie.pl")
    app.setApplicationName("MusicSlides")
    main = MainWindow()
    main.show()
    main.raise_()
    app.exec()


if __name__ == "__main__":
    main()