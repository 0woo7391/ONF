import QtQuick
import ".."

Image {
    property string name: ""
    property color tint: StudyStyle.ink
    width: 20
    height: 20
    sourceSize: Qt.size(40, 40)
    source: name ? "image://study-icons/" + name + "/" + tint.toString().replace("#", "") : ""
}
