import QtQuick
import QtQuick.Controls.Basic
import ".."

Item {
    id: control
    property string label: ""
    property int value: 25
    property int maximum: 120
    readonly property bool invalid: field.text === "" || Number(field.text) < 1 || Number(field.text) > maximum
    signal valueEdited(int value)
    implicitHeight: 80
    function commit() { if (!invalid) valueEdited(Number(field.text)) }
    StudyText { text: control.label; color: StudyStyle.muted; font.pixelSize: 14 }
    Rectangle { y: 28; width: parent.width; height: 48; radius: 6; color: StudyStyle.field; border.width: field.activeFocus ? 2 : 1; border.color: control.invalid ? StudyStyle.danger : field.activeFocus ? StudyStyle.accent : StudyStyle.line }
    StudyButton { x: 4; y: 30; width: 40; tone: "quiet"; symbol: "minus"; hint: control.label + " 줄이기"; onClicked: { field.text = String(Math.max(1, control.value - 1)); control.commit() } }
    TextField {
        id: field
        objectName: control.objectName + "Field"
        x: 46; y: 28; width: parent.width - 92; height: 48
        text: String(control.value)
        color: StudyStyle.ink
        font.family: StudyStyle.family
        font.pixelSize: 20
        font.weight: Font.Medium
        horizontalAlignment: Text.AlignHCenter
        selectByMouse: true
        validator: IntValidator { bottom: 1; top: control.maximum }
        background: Item {}
        onTextEdited: control.commit()
        onEditingFinished: control.commit()
        Accessible.name: control.label
    }
    StudyButton { x: parent.width - 44; y: 30; width: 40; tone: "quiet"; symbol: "plus"; hint: control.label + " 늘리기"; onClicked: { field.text = String(Math.min(control.maximum, control.value + 1)); control.commit() } }
}
