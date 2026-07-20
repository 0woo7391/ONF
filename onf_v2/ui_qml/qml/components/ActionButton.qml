import QtQuick
import QtQuick.Controls.Basic
import ".."

Button {
    id: control
    property string tone: "neutral"
    property bool busy: false
    property bool completed: false

    implicitHeight: 42
    leftPadding: 16
    rightPadding: 16
    enabled: !busy
    scale: down ? 0.98 : 1.0

    contentItem: Row {
        spacing: 8
        anchors.centerIn: parent
        BusyIndicator {
            width: 17
            height: 17
            running: control.busy
            visible: control.busy
            palette.dark: control.foregroundColor()
        }
        Text {
            text: control.completed ? "✓  " + control.text : control.text
            color: control.foregroundColor()
            font.pixelSize: 14
            font.weight: Font.DemiBold
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    background: Rectangle {
        radius: Theme.radius
        color: control.backgroundColor()
        border.width: control.tone === "neutral" ? 1 : 0
        border.color: Theme.border
        Behavior on color { ColorAnimation { duration: Theme.fast } }
    }

    Behavior on scale { NumberAnimation { duration: 80; easing.type: Easing.OutCubic } }

    function foregroundColor() {
        if (!enabled) return "#AAB2BD"
        if (tone === "primary") return "#FFFFFF"
        if (tone === "danger") return Theme.danger
        return Theme.text
    }

    function backgroundColor() {
        if (!enabled) return "#F1F3F5"
        if (tone === "primary") return hovered ? "#1D4ED8" : Theme.primary
        if (tone === "danger") return hovered ? "#FFE4E7" : Theme.dangerSoft
        return hovered ? "#F2F5F8" : Theme.surface
    }
}
