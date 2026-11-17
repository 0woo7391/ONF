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
    hoverEnabled: true
    scale: down ? 0.96 : 1.0

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
            font.family: StudyStyle.family
            font.weight: Font.DemiBold
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    background: Rectangle {
        radius: Theme.radius
        color: control.backgroundColor()
        border.width: control.visualFocus ? 2 : control.tone === "neutral" ? 1 : 0
        border.color: control.visualFocus ? StudyStyle.accent : Theme.border
        Behavior on color { ColorAnimation { duration: Theme.fast } }
    }

    Behavior on scale { NumberAnimation { duration: StudyStyle.fast; easing.type: Easing.OutCubic } }

    function foregroundColor() {
        if (!enabled && !busy) return StudyStyle.disabled
        if (tone === "primary") return "#FFFFFF"
        if (tone === "danger") return Theme.danger
        return Theme.text
    }

    function backgroundColor() {
        if (!enabled) return "#F1F3F5"
        if (tone === "primary") return hovered ? "#106F6A" : Theme.primary
        if (tone === "danger") return hovered ? "#FFE4E7" : Theme.dangerSoft
        return hovered ? "#F2F5F8" : Theme.surface
    }
}
