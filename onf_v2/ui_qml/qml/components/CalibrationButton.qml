import QtQuick
import QtQuick.Controls.Basic
import ".."

Button {
    id: control
    property string label: "기준 자세 설정"
    property bool ready: false
    property bool collecting: false
    property real progress: 0
    implicitHeight: 54
    text: label
    scale: down ? 0.985 : 1

    background: Rectangle {
        radius: Theme.radius
        color: control.ready ? Theme.successSoft : control.collecting ? Theme.primarySoft : Theme.warningSoft
        border.color: control.ready ? "#BDECCF" : control.collecting ? "#BFD5FF" : "#FCE2A8"
        Rectangle {
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            height: 4
            width: parent.width * Math.max(0, Math.min(1, control.progress))
            radius: 2
            color: control.ready ? Theme.success : Theme.primary
            Behavior on width { NumberAnimation { duration: 150 } }
        }
    }
    contentItem: Row {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 14
        anchors.rightMargin: 14
        spacing: 9
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: control.ready ? "✓" : control.collecting ? Math.round(control.progress * 100) + "%" : "!"
            color: control.ready ? Theme.success : control.collecting ? Theme.primary : "#B77900"
            font.pixelSize: 13
            font.weight: Font.Bold
            width: 34
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: control.label
            color: Theme.text
            font.pixelSize: 13
            font.weight: Font.DemiBold
        }
        Item { width: 1; height: 1 }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: control.ready ? "완료" : control.collecting ? "설정 중" : "필요"
            color: control.ready ? Theme.success : control.collecting ? Theme.primary : "#B77900"
            font.pixelSize: 11
        }
    }
    Behavior on scale { NumberAnimation { duration: 80 } }
}
