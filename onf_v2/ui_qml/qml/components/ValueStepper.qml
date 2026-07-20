import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import ".."

Rectangle {
    id: root
    property int value: 25
    property int minimumValue: 1
    property int maximumValue: 120
    property string suffix: "분"

    implicitWidth: 98
    implicitHeight: 36
    radius: Theme.radius
    color: Theme.surfaceSoft
    border.color: Theme.border

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Button {
            id: decreaseButton
            Layout.preferredWidth: 30
            Layout.fillHeight: true
            text: "−"
            enabled: root.value > root.minimumValue
            onClicked: root.value = Math.max(root.minimumValue, root.value - 1)
            background: Rectangle { radius: Theme.radius; color: decreaseButton.down ? "#DCE7F8" : decreaseButton.hovered ? Theme.primarySoft : "transparent" }
            contentItem: Text { text: decreaseButton.text; color: decreaseButton.enabled ? Theme.text : "#B8C0CB"; font.pixelSize: 17; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
        }

        Text {
            Layout.fillWidth: true
            text: root.value + root.suffix
            color: Theme.text
            font.pixelSize: 12
            font.weight: Font.DemiBold
            horizontalAlignment: Text.AlignHCenter
        }

        Button {
            id: increaseButton
            Layout.preferredWidth: 30
            Layout.fillHeight: true
            text: "+"
            enabled: root.value < root.maximumValue
            onClicked: root.value = Math.min(root.maximumValue, root.value + 1)
            background: Rectangle { radius: Theme.radius; color: increaseButton.down ? "#DCE7F8" : increaseButton.hovered ? Theme.primarySoft : "transparent" }
            contentItem: Text { text: increaseButton.text; color: increaseButton.enabled ? Theme.text : "#B8C0CB"; font.pixelSize: 17; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
        }
    }
}
