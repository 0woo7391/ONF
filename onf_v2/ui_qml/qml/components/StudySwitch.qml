import QtQuick
import QtQuick.Controls.Basic
import ".."

Switch {
    id: toggle
    implicitHeight: 36
    implicitWidth: caption.implicitWidth + 46
    indicator: Rectangle {
        x: toggle.width - 36; y: (toggle.height - height) / 2
        width: 34; height: 20; radius: 10
        color: toggle.checked ? StudyStyle.accent : "#C8D0D6"
        opacity: toggle.enabled ? 1 : 0.5
        Rectangle {
            x: toggle.checked ? 16 : 2; y: 2
            width: 16; height: 16; radius: 8; color: "white"
            Behavior on x { NumberAnimation { duration: StudyStyle.fast; easing.type: Easing.OutCubic } }
        }
    }
    contentItem: StudyText { id: caption; text: toggle.text; font.pixelSize: 14; rightPadding: 46; verticalAlignment: Text.AlignVCenter; color: toggle.enabled ? StudyStyle.ink : StudyStyle.muted }
    background: Rectangle { color: "transparent"; radius: 6; border.width: toggle.visualFocus ? 2 : 0; border.color: StudyStyle.accent }
}
