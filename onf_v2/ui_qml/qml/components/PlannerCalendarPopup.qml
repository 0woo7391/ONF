import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import ".."

Popup {
    id: root
    objectName: "plannerCalendarPopup"

    property var backendObject: null
    property date displayMonth: new Date()
    property string selectedDate: ""
    property int pendingEventId: -1
    property bool dateSelectionOnly: false
    signal dateSelected(string value)
    signal feedbackRequested(string message)

    width: Math.min(dateSelectionOnly ? 520 : 760, parent ? parent.width - 48 : 760)
    height: Math.min(dateSelectionOnly ? 440 : 600, parent ? parent.height - 48 : 600)
    anchors.centerIn: parent
    modal: true
    focus: true
    padding: 0
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    background: Rectangle {
        radius: Theme.radius
        color: Theme.surface
        border.color: Theme.border
    }

    function twoDigits(value) {
        return value < 10 ? "0" + value : "" + value
    }

    function isoDate(value) {
        return value.getFullYear() + "-" + twoDigits(value.getMonth() + 1) + "-" + twoDigits(value.getDate())
    }

    function dateFromIso(value) {
        var parts = value.split("-")
        return new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]))
    }

    function openForDate(value) {
        var selected = value ? dateFromIso(value) : new Date()
        selectedDate = isoDate(selected)
        displayMonth = new Date(selected.getFullYear(), selected.getMonth(), 1)
        open()
    }

    function firstWeekday() {
        return new Date(displayMonth.getFullYear(), displayMonth.getMonth(), 1).getDay()
    }

    function daysInMonth() {
        return new Date(displayMonth.getFullYear(), displayMonth.getMonth() + 1, 0).getDate()
    }

    function dateForCell(index) {
        var day = index - firstWeekday() + 1
        if (day < 1 || day > daysInMonth())
            return ""
        return displayMonth.getFullYear() + "-" + twoDigits(displayMonth.getMonth() + 1) + "-" + twoDigits(day)
    }

    function eventCount(value) {
        if (!backendObject || !value)
            return 0
        var count = 0
        for (var index = 0; index < backendObject.calendarEvents.length; index++) {
            if (backendObject.calendarEvents[index].date === value)
                count++
        }
        return count
    }

    function selectedEvents() {
        var result = []
        if (!backendObject)
            return result
        for (var index = 0; index < backendObject.calendarEvents.length; index++) {
            var event = backendObject.calendarEvents[index]
            if (event.date === selectedDate)
                result.push(event)
        }
        return result
    }

    function shiftMonth(direction) {
        displayMonth = new Date(displayMonth.getFullYear(), displayMonth.getMonth() + direction, 1)
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 14

        RowLayout {
            Layout.fillWidth: true
            Text { text: root.dateSelectionOnly ? "날짜 선택" : "학습 캘린더"; color: Theme.text; font.pixelSize: 20; font.weight: Font.Bold }
            Item { Layout.fillWidth: true }
            ActionButton { text: "‹"; onClicked: root.shiftMonth(-1) }
            Text {
                Layout.preferredWidth: 140
                text: root.displayMonth.getFullYear() + "년 " + (root.displayMonth.getMonth() + 1) + "월"
                color: Theme.text
                font.pixelSize: 14
                font.weight: Font.DemiBold
                horizontalAlignment: Text.AlignHCenter
            }
            ActionButton { text: "›"; onClicked: root.shiftMonth(1) }
            ActionButton { text: "×"; onClicked: root.close() }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 16

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: Theme.radius
                color: Theme.surfaceSoft
                border.color: Theme.border

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 6

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 7
                        columnSpacing: 4
                        Repeater {
                            model: ["일", "월", "화", "수", "목", "금", "토"]
                            delegate: Text {
                                required property string modelData
                                Layout.fillWidth: true
                                text: modelData
                                color: modelData === "일" ? Theme.danger : modelData === "토" ? Theme.primary : Theme.muted
                                font.pixelSize: 10
                                font.weight: Font.DemiBold
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        columns: 7
                        rowSpacing: 4
                        columnSpacing: 4

                        Repeater {
                            model: 42
                            delegate: Button {
                                id: dayButton
                                required property int index
                                property string cellDate: root.dateForCell(index)
                                property int dayNumber: cellDate === "" ? 0 : Number(cellDate.slice(-2))
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                enabled: cellDate !== ""
                                text: dayNumber > 0 ? dayNumber : ""
                                onClicked: {
                                    root.selectedDate = cellDate
                                    if (root.dateSelectionOnly) {
                                        root.dateSelected(cellDate)
                                        root.close()
                                    }
                                }
                                background: Rectangle {
                                    radius: Theme.radiusSmall
                                    color: dayButton.cellDate === root.selectedDate ? Theme.primarySoft : dayButton.hovered ? "#F0F4F8" : Theme.surface
                                    border.color: dayButton.cellDate === root.selectedDate ? Theme.primary : Theme.border
                                    Rectangle {
                                        visible: root.eventCount(dayButton.cellDate) > 0
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        anchors.bottom: parent.bottom
                                        anchors.bottomMargin: 5
                                        width: 5
                                        height: 5
                                        radius: 3
                                        color: Theme.success
                                    }
                                }
                                contentItem: Text {
                                    text: dayButton.text
                                    color: dayButton.index % 7 === 0 ? Theme.danger : dayButton.index % 7 === 6 ? Theme.primary : Theme.text
                                    font.pixelSize: 11
                                    font.weight: dayButton.cellDate === root.selectedDate ? Font.Bold : Font.Medium
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                visible: !root.dateSelectionOnly
                Layout.preferredWidth: 270
                Layout.fillHeight: true
                radius: Theme.radius
                color: Theme.surface
                border.color: Theme.border

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10

                    Text {
                        text: root.selectedDate === "" ? "날짜를 선택하세요" : root.selectedDate.replace(/-/g, ".")
                        color: Theme.text
                        font.pixelSize: 15
                        font.weight: Font.Bold
                    }

                    TextField {
                        id: eventTitle
                        Layout.fillWidth: true
                        implicitHeight: 40
                        placeholderText: "시험, 과제, 목표 추가"
                        color: Theme.text
                        placeholderTextColor: Theme.muted
                        background: Rectangle { radius: Theme.radiusSmall; color: Theme.surface; border.color: eventTitle.activeFocus ? Theme.primary : Theme.border }
                        onAccepted: addEventButton.clicked()
                    }

                    ActionButton {
                        id: addEventButton
                        Layout.fillWidth: true
                        text: "이 날짜에 추가"
                        tone: "primary"
                        enabled: root.selectedDate !== "" && eventTitle.text.trim() !== ""
                        onClicked: {
                            if (!root.backendObject)
                                return
                            var eventId = root.backendObject.addCalendarEvent(eventTitle.text, root.selectedDate)
                            if (eventId <= 0) {
                                root.feedbackRequested("일정을 추가하지 못했습니다.")
                                return
                            }
                            eventTitle.clear()
                            root.pendingEventId = eventId
                        }
                    }

                    Text { text: "다가오는 일정"; color: Theme.muted; font.pixelSize: 11; font.weight: Font.DemiBold }

                    ListView {
                        id: eventList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 6
                        clip: true
                        model: root.backendObject ? root.backendObject.calendarEvents : []
                        delegate: Rectangle {
                            id: eventRow
                            required property var modelData
                            width: eventList.width
                            height: 62
                            radius: Theme.radiusSmall
                            color: eventRow.modelData.isPrimary ? Theme.primarySoft : Theme.surfaceSoft
                            border.color: eventRow.modelData.isPrimary ? "#BFD5FF" : Theme.border
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 9
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    Text { text: eventRow.modelData.title; color: Theme.text; font.pixelSize: 12; font.weight: Font.DemiBold; elide: Text.ElideRight; Layout.fillWidth: true }
                                    Text { text: eventRow.modelData.dateLabel + " · " + eventRow.modelData.remainingLabel; color: Theme.muted; font.pixelSize: 9; elide: Text.ElideRight; Layout.fillWidth: true }
                                }
                                Button {
                                    text: eventRow.modelData.isPrimary ? "★" : "☆"
                                    ToolTip.visible: hovered
                                    ToolTip.text: eventRow.modelData.isPrimary ? "대표 D-day 해제" : "대표 D-day로 설정"
                                    onClicked: root.backendObject.setPrimaryCalendarEvent(eventRow.modelData.isPrimary ? -1 : eventRow.modelData.eventId)
                                    background: Rectangle { color: "transparent" }
                                    contentItem: Text { text: parent.text; color: Theme.primary; font.pixelSize: 16; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                }
                                Button {
                                    text: "×"
                                    ToolTip.visible: hovered
                                    ToolTip.text: "일정 삭제"
                                    onClicked: root.backendObject.deleteCalendarEvent(eventRow.modelData.eventId)
                                    background: Rectangle { color: "transparent" }
                                    contentItem: Text { text: parent.text; color: Theme.danger; font.pixelSize: 16; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Rectangle {
        visible: root.pendingEventId > 0
        anchors.fill: parent
        z: 20
        radius: Theme.radius
        color: "#CCFFFFFF"

        Rectangle {
            anchors.centerIn: parent
            width: 340
            height: 170
            radius: Theme.radius
            color: Theme.surface
            border.color: Theme.border

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 12
                Text { text: "대표 D-day로 설정할까요?"; color: Theme.text; font.pixelSize: 17; font.weight: Font.Bold }
                Text { text: "대표로 설정하면 플래너 상단에 표시됩니다."; color: Theme.muted; font.pixelSize: 11 }
                Item { Layout.fillHeight: true }
                RowLayout {
                    Layout.fillWidth: true
                    ActionButton {
                        Layout.fillWidth: true
                        text: "아니요"
                        onClicked: { root.pendingEventId = -1; root.feedbackRequested("캘린더에 일정을 추가했습니다.") }
                    }
                    ActionButton {
                        Layout.fillWidth: true
                        text: "대표로 설정"
                        tone: "primary"
                        onClicked: {
                            root.backendObject.setPrimaryCalendarEvent(root.pendingEventId)
                            root.pendingEventId = -1
                            root.feedbackRequested("대표 D-day를 설정했습니다.")
                        }
                    }
                }
            }
        }
    }
}
