import QtQuick
import QtQuick.Controls.Basic
import ".."

Button {
    id: control
    property string symbol: ""
    property string tone: "secondary"
    property string hint: ""
    implicitHeight: 44
    implicitWidth: text ? Math.max(88, caption.implicitWidth + (symbol ? 62 : 32)) : 40
    hoverEnabled: true
    Accessible.name: text || hint
    ToolTip.visible: (hovered || visualFocus) && hint !== ""
    ToolTip.text: hint
    ToolTip.delay: 500
    background: Rectangle {
        radius: 8
        color: !control.enabled ? (control.tone === "quiet" ? "transparent" : "#EEF0F2")
            : control.tone === "primary" ? (control.down ? "#0D625F" : control.hovered ? "#106F6A" : StudyStyle.accent)
            : control.down ? "#E7ECEF" : control.hovered ? "#F0F3F4" : control.tone === "quiet" ? "transparent" : "white"
        border.width: control.visualFocus ? 2 : control.tone === "secondary" ? 1 : 0
        border.color: control.visualFocus ? StudyStyle.accent : StudyStyle.line
        scale: control.down ? 0.96 : 1
        Behavior on scale { NumberAnimation { duration: StudyStyle.motionEnabled ? (control.down ? 70 : 110) : 0; easing.type: Easing.OutCubic } }
    }
    contentItem: Item {
        implicitWidth: contents.implicitWidth
        implicitHeight: 24
        Row {
            id: contents
            anchors.centerIn: parent
            spacing: 8
            StudyIcon { visible: control.symbol !== ""; width: visible ? 18 : 0; height: 18; name: control.symbol; tint: caption.color; anchors.verticalCenter: parent.verticalCenter }
            StudyText { id: caption; text: control.text; font.weight: Font.Medium; color: !control.enabled ? StudyStyle.disabled : control.tone === "primary" ? "white" : control.tone === "danger" ? StudyStyle.danger : StudyStyle.ink; anchors.verticalCenter: parent.verticalCenter }
        }
    }
}
