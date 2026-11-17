import QtQuick
import QtQuick.Controls.Basic
import ".."

FocusScope {
    id: root

    property string text: ""
    property bool calculated: false
    property bool invalid: false
    property bool dirty: false
    property bool syncing: false
    property var previousTabItem: null
    property var nextTabItem: null
    signal valueCommitted(bool userEdited)
    signal invalidCommitted()
    signal accepted()

    implicitWidth: 82
    implicitHeight: 40

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusSmall
        color: root.calculated ? "#F3F5F7" : Theme.surface
        border.color: root.invalid ? Theme.danger : root.activeFocus ? Theme.primary : Theme.border
    }

    Row {
        anchors.centerIn: parent
        spacing: 4

        TextInput {
            id: hourInput
            objectName: root.objectName + "Hour"
            width: 22
            color: root.invalid ? Theme.danger : root.calculated ? Theme.muted : Theme.text
            font.pixelSize: 12
            font.italic: root.calculated
            horizontalAlignment: Text.AlignHCenter
            selectByMouse: true
            maximumLength: 2
            validator: RegularExpressionValidator { regularExpression: /^[0-9]{0,2}$/ }
            KeyNavigation.tab: minuteInput
            Keys.onBacktabPressed: function(event) {
                if (root.commit())
                    root.focusPrevious()
                event.accepted = true
            }
            Keys.onReturnPressed: function(event) {
                if (root.commit()) root.accepted()
                event.accepted = true
            }
            Keys.onEnterPressed: function(event) {
                if (root.commit()) root.accepted()
                event.accepted = true
            }
            onTextEdited: root.userEdited()
            onEditingFinished: Qt.callLater(root.commitIfOutside)
        }

        Text {
            text: ":"
            color: root.calculated ? Theme.muted : Theme.text
            font.pixelSize: 12
            font.weight: Font.DemiBold
        }

        TextInput {
            id: minuteInput
            objectName: root.objectName + "Minute"
            width: 22
            color: root.invalid ? Theme.danger : root.calculated ? Theme.muted : Theme.text
            font.pixelSize: 12
            font.italic: root.calculated
            horizontalAlignment: Text.AlignHCenter
            selectByMouse: true
            maximumLength: 2
            validator: RegularExpressionValidator { regularExpression: /^[0-9]{0,2}$/ }
            KeyNavigation.backtab: hourInput
            Keys.onTabPressed: function(event) {
                if (root.commit())
                    root.focusNext()
                event.accepted = true
            }
            Keys.onReturnPressed: function(event) {
                if (root.commit()) root.accepted()
                event.accepted = true
            }
            Keys.onEnterPressed: function(event) {
                if (root.commit()) root.accepted()
                event.accepted = true
            }
            onTextEdited: root.userEdited()
            onEditingFinished: Qt.callLater(root.commitIfOutside)
        }
    }

    function userEdited() {
        if (syncing)
            return
        dirty = true
        calculated = false
        invalid = false
        text = currentText()
    }

    function focusHour() {
        hourInput.forceActiveFocus(Qt.TabFocusReason)
        hourInput.selectAll()
    }

    function focusMinute() {
        minuteInput.forceActiveFocus(Qt.TabFocusReason)
        minuteInput.selectAll()
    }

    function focusFirst() {
        focusHour()
    }

    function focusLast() {
        focusMinute()
    }

    function focusTarget(item, last) {
        if (!item)
            return
        if (last && typeof item.focusLast === "function")
            item.focusLast()
        else if (!last && typeof item.focusFirst === "function")
            item.focusFirst()
        else
            item.forceActiveFocus(Qt.TabFocusReason)
    }

    function focusPrevious() {
        focusTarget(previousTabItem, true)
    }

    function focusNext() {
        focusTarget(nextTabItem, false)
    }

    function currentText() {
        if (hourInput.text === "" && minuteInput.text === "")
            return ""
        return hourInput.text + ":" + minuteInput.text
    }

    function commitIfOutside() {
        if (!hourInput.activeFocus && !minuteInput.activeFocus)
            commit()
    }

    function commit() {
        var wasEdited = dirty
        if (!normalize()) {
            dirty = true
            invalidCommitted()
            return false
        }
        dirty = false
        valueCommitted(wasEdited)
        return true
    }

    function normalize() {
        if (hourInput.text === "" && minuteInput.text === "") {
            invalid = false
            text = ""
            return true
        }
        if (hourInput.text === "") {
            invalid = true
            return false
        }
        var hour = Number(hourInput.text)
        var minute = minuteInput.text === "" ? 0 : Number(minuteInput.text)
        invalid = isNaN(hour) || isNaN(minute) || hour < 0 || hour > 23 || minute < 0 || minute > 59
        if (invalid)
            return false
        setMinutes(hour * 60 + minute)
        return true
    }

    function minutes() {
        if (!normalize())
            return -1
        if (text === "")
            return -1
        return Number(hourInput.text) * 60 + Number(minuteInput.text)
    }

    function setMinutes(value) {
        var normalized = (value + 24 * 60) % (24 * 60)
        var hour = Math.floor(normalized / 60)
        var minute = normalized % 60
        syncing = true
        hourInput.text = (hour < 10 ? "0" : "") + hour
        minuteInput.text = (minute < 10 ? "0" : "") + minute
        text = hourInput.text + ":" + minuteInput.text
        syncing = false
        invalid = false
    }

    function syncFromText(value) {
        if (syncing || dirty)
            return
        syncing = true
        var clean = value.trim()
        if (clean === "") {
            hourInput.text = ""
            minuteInput.text = ""
        } else {
            var parts = clean.split(":")
            hourInput.text = parts.length > 0 ? parts[0] : ""
            minuteInput.text = parts.length > 1 ? parts[1] : ""
        }
        syncing = false
    }

    onTextChanged: syncFromText(text)
    Component.onCompleted: syncFromText(text)
}
