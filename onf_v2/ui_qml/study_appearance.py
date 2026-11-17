from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtSvg import QSvgRenderer


class StudyIconProvider(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.Image)

    def requestImage(self, identifier, size, requested_size):
        name, color = identifier.split("/", 1)
        path = Path(__file__).with_name("qml") / "assets" / "icons" / f"{name}.svg"
        renderer = QSvgRenderer(str(path))
        image = QImage(40, 40, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        renderer.render(painter)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(image.rect(), QColor("#" + color))
        painter.end()
        size.setWidth(40)
        size.setHeight(40)
        return image
