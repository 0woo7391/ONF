pragma ComponentBehavior: Bound
import QtQuick
import ".."

Item {
    id: root
    property var values: [82, 88, 91, 76, 68, 72, 85, 93, 90, 0, -1, 64, 78, 88, 94, 86, 73, 81]
    property int activeCount: values.length

    function rateColor(value) {
        if (value < 0) return "#CBD2DA"
        if (value === 0) return "#E5E8EB"
        if (value < 50) return Qt.tint(Theme.danger, Qt.rgba(1, 0.72, 0.30, value / 50))
        return Qt.tint(Theme.warning, Qt.rgba(0, 0.72, 0.29, (value - 50) / 50))
    }

    Row {
        anchors.fill: parent
        spacing: 5
        Repeater {
            model: root.values
            delegate: Item {
                id: barSlot
                required property var modelData
                width: Math.max(4, (root.width - (root.values.length - 1) * 5) / root.values.length)
                height: root.height
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: barSlot.modelData < 0 ? 4 : Math.max(5, parent.height * barSlot.modelData / 100)
                    radius: Math.min(3, width / 2)
                    color: root.rateColor(barSlot.modelData)
                    Behavior on height {
                        NumberAnimation { duration: 240; easing.type: Easing.OutCubic }
                    }
                    Behavior on color { ColorAnimation { duration: 180 } }
                }
            }
        }
    }
}
