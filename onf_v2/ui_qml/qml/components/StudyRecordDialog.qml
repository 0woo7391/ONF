pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import ".."

Popup {
    id: root
    objectName: "studyRecordDialog"
    property var backendObject: null
    property int recordId: -1
    property int taskId: -1
    property int sessionId: -1
    property string errorText: ""
    property bool saving: false
    signal feedbackRequested(string message)
    parent: Overlay.overlay
    width: Math.min(700, parent ? parent.width - 32 : 700)
    height: Math.min(620, parent ? parent.height - 32 : 620)
    anchors.centerIn: parent
    modal: true
    focus: true
    padding: 18
    background: Rectangle { radius: Theme.radius; color: Theme.surface; border.color: Theme.border }

    function newRecord() {
        recordId = -1; taskId = -1; sessionId = -1
        recordKind.currentIndex = 0
        recordTitle.clear(); recordHours.value = 0; recordMinutes.value = 0
        errorText = ""; saving = false
    }

    function editRecord(row) {
        recordId = row.id; taskId = row.task_id || -1; sessionId = row.session_id || -1
        recordKind.currentIndex = row.source === "allocated" ? 1 : 0
        recordTitle.text = row.title
        recordHours.value = row.hours; recordMinutes.value = row.minutes
        errorText = ""
    }

    function remainingText() {
        if (!backendObject || sessionId < 0) return "측정 기록을 선택하세요"
        var sessions = backendObject.recordSessions
        for (var i = 0; i < sessions.length; i++) {
            if (sessions[i].id === sessionId) {
                var available = sessions[i].remaining
                var entries = backendObject.studyRecords
                for (var j = 0; j < entries.length; j++) {
                    if (entries[j].id === recordId && entries[j].session_id === sessionId)
                        available += entries[j].study_seconds
                }
                return "연결 가능 " + Math.floor(available / 60) + "분 " + Math.floor(available % 60) + "초"
            }
        }
        return "해당 날짜에 측정 기록이 없습니다"
    }

    function saveRecord() {
        if (!visible || saving || !backendObject) return
        var hours = Number(recordHours.contentItem.text)
        var minutes = Number(recordMinutes.contentItem.text)
        if (!Number.isInteger(hours) || !Number.isInteger(minutes) || hours < 0 || hours > 24 || minutes < 0 || minutes > 59) {
            errorText = "시간과 분을 확인하세요."
            return
        }
        if (recordKind.currentIndex === 1 && (sessionId < 0 || sessionChoice.currentIndex < 0)) {
            errorText = "연결할 측정 기록을 선택하세요."
            return
        }
        saving = true
        var result = backendObject.saveStudyRecord(recordId, recordKind.currentIndex === 1 ? sessionId : -1, taskId, recordTitle.text, hours, minutes)
        if (!result.ok) { errorText = result.message; saving = false; return }
        root.feedbackRequested("공부 기록을 저장했습니다.")
        close()
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10
        RowLayout {
            Layout.fillWidth: true
            Text { text: "공부 기록"; color: Theme.text; font.pixelSize: 19; font.weight: Font.Bold }
            Item { Layout.fillWidth: true }
            ActionButton {
                objectName: "recordDateButton"
                text: root.backendObject ? root.backendObject.dayLabel : "날짜 선택"
                enabled: root.recordId < 0 || recordKind.currentIndex === 0
                onClicked: datePicker.openForDate(root.backendObject.recordsDateIso)
            }
            ActionButton { text: "×"; onClicked: root.close(); ToolTip.visible: hovered; ToolTip.text: "닫기" }
        }
        RowLayout {
            Layout.fillWidth: true
            ComboBox {
                id: recordKind
                objectName: "recordKindChoice"
                Layout.preferredWidth: 180
                model: ["별도 공부 기록", "측정 시간에 연결"]
                enabled: root.recordId < 0
                palette.text: Theme.text
                onActivated: { root.errorText = ""; root.sessionId = -1 }
            }
            ComboBox {
                id: sessionChoice
                objectName: "recordSessionChoice"
                visible: recordKind.currentIndex === 1
                Layout.fillWidth: true
                model: root.backendObject ? root.backendObject.recordSessions : []
                textRole: "label"
                valueRole: "id"
                currentIndex: indexOfValue(root.sessionId)
                palette.text: Theme.text
                onActivated: root.sessionId = currentValue
            }
            Text { visible: recordKind.currentIndex === 0; text: "집중 정보 미측정"; color: Theme.muted; font.pixelSize: 11 }
        }
        ComboBox {
            id: taskChoice
            objectName: "recordTaskChoice"
            Layout.fillWidth: true
            model: [{taskId: -1, title: "계획에 연결하지 않음"}].concat(root.backendObject ? root.backendObject.recordTasks : [])
            textRole: "title"
            valueRole: "taskId"
            currentIndex: indexOfValue(root.taskId)
            palette.text: Theme.text
            onActivated: {
                root.taskId = currentValue
                if (currentValue > 0) recordTitle.text = currentText
            }
        }
        TextField {
            id: recordTitle
            objectName: "recordTitleInput"
            Layout.fillWidth: true
            implicitHeight: 40
            placeholderText: "공부한 내용"
            color: Theme.text
            placeholderTextColor: Theme.muted
            selectByMouse: true
            background: Rectangle { radius: Theme.radiusSmall; color: Theme.surface; border.color: recordTitle.activeFocus ? Theme.primary : Theme.border }
            onAccepted: root.saveRecord()
        }
        RowLayout {
            Layout.fillWidth: true
            Text { text: "실제 공부시간"; color: Theme.text; font.pixelSize: 12 }
            SpinBox { id: recordHours; objectName: "recordHours"; from: 0; to: 24; editable: true; palette.text: Theme.text; Layout.preferredWidth: 130 }
            Text { text: "시간"; color: Theme.muted; font.pixelSize: 12 }
            SpinBox { id: recordMinutes; objectName: "recordMinutes"; from: 0; to: 59; editable: true; palette.text: Theme.text; Layout.preferredWidth: 130 }
            Text { text: "분"; color: Theme.muted; font.pixelSize: 12 }
            Item { Layout.fillWidth: true }
            Text { visible: recordKind.currentIndex === 1; text: root.remainingText(); color: Theme.muted; font.pixelSize: 10 }
        }
        Text { visible: root.errorText !== ""; Layout.fillWidth: true; text: root.errorText; color: Theme.danger; font.pixelSize: 12; wrapMode: Text.Wrap }
        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.border }
        RowLayout {
            Layout.fillWidth: true
            Text { text: "이 날짜의 공부 기록"; color: Theme.text; font.pixelSize: 13; font.weight: Font.DemiBold }
            Item { Layout.fillWidth: true }
            ActionButton { objectName: "newStudyRecordButton"; text: "+ 새 기록"; implicitHeight: 32; onClicked: root.newRecord() }
        }
        ListView {
            id: recordList
            objectName: "studyRecordList"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 6
            model: root.backendObject ? root.backendObject.studyRecords : []
            ScrollBar.vertical: ScrollBar {}
            delegate: RowLayout {
                required property var modelData
                width: recordList.width
                height: 54
                spacing: 12
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3
                    Text { Layout.fillWidth: true; text: modelData.title; color: Theme.text; font.pixelSize: 13; font.weight: Font.DemiBold; elide: Text.ElideRight }
                    Text { text: modelData.sourceLabel + " · " + modelData.duration + " · 집중 " + modelData.focusLabel; color: Theme.muted; font.pixelSize: 10 }
                }
                ActionButton { objectName: "editStudyRecord" + modelData.id; visible: modelData.source !== "tracked"; text: "수정"; implicitHeight: 32; onClicked: root.editRecord(modelData) }
            }
            Text { anchors.centerIn: parent; visible: recordList.count === 0; text: "아직 공부 기록이 없습니다"; color: Theme.muted; font.pixelSize: 12 }
        }
        RowLayout {
            Layout.fillWidth: true
            ActionButton { objectName: "deleteStudyRecordButton"; visible: root.recordId > 0; text: "삭제"; tone: "danger"; onClicked: deleteConfirmation.open() }
            Item { Layout.fillWidth: true }
            ActionButton { text: "취소"; onClicked: root.close() }
            ActionButton { objectName: "saveStudyRecordButton"; text: "저장"; tone: "primary"; busy: root.saving; onClicked: root.saveRecord() }
        }
    }

    PlannerCalendarPopup {
        id: datePicker
        objectName: "studyRecordDatePicker"
        parent: Overlay.overlay
        dateSelectionOnly: true
        onDateSelected: function(value) { root.backendObject.selectRecordsDate(value); root.taskId = -1; root.sessionId = -1 }
    }
    Dialog {
        id: deleteConfirmation
        objectName: "deleteStudyRecordConfirmation"
        parent: Overlay.overlay
        implicitWidth: 360
        width: Math.min(implicitWidth, parent ? parent.width - 32 : implicitWidth)
        anchors.centerIn: parent
        modal: true
        title: "공부 기록 삭제"
        standardButtons: Dialog.NoButton
        contentItem: Text { text: "이 공부 기록을 삭제할까요?"; color: Theme.text; padding: 16 }
        footer: RowLayout {
            Item { Layout.fillWidth: true }
            ActionButton { text: "취소"; onClicked: deleteConfirmation.close() }
            ActionButton {
                objectName: "confirmDeleteStudyRecordButton"
                text: "삭제"; tone: "danger"
                onClicked: {
                    var result = root.backendObject.deleteStudyRecord(root.recordId)
                    deleteConfirmation.close()
                    if (!result.ok) { root.errorText = result.message; return }
                    root.newRecord(); root.feedbackRequested("공부 기록을 삭제했습니다.")
                }
            }
        }
    }
    onClosed: saving = false
}
