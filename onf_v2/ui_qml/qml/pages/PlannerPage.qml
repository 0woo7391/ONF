pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Window
import ".."
import "../components"

Item {
    id: root
    objectName: "plannerPage"
    property var backendObject: null
    property var pendingPlanEdits: []
    signal feedbackRequested(string message)

    function openCalendarForDate(value) {
        plannerCalendar.openForDate(value)
    }

    function findInput(name, item) {
        if (item.objectName === name) return item
        for (var i = 0; i < item.children.length; i++) {
            var found = findInput(name, item.children[i])
            if (found) return found
        }
        return null
    }

    function savePlanEdit(taskId, title, start, end, duration, changedField, derivedField) {
        // Let Tab finish moving before a model refresh replaces the row delegate.
        pendingPlanEdits.push(function() {
            if (!root.backendObject) return
            var focused = root.Window.window.activeFocusItem
            var name = focused ? focused.objectName : ""
            var selectionStart = focused ? focused.selectionStart : undefined
            var selectionEnd = focused ? focused.selectionEnd : undefined
            var cursorPosition = focused ? focused.cursorPosition : undefined
            if (!root.backendObject.updatePlannerTask(taskId, title, start, end, duration, changedField, derivedField)) {
                root.feedbackRequested("할 일과 시간 입력을 확인하세요.")
                return
            }
            if (name.indexOf("plannerRow") !== 0) return
            Qt.callLater(function() {
                if (!root.visible) return
                var input = root.findInput(name, root)
                if (!input || input.activeFocus) return
                input.forceActiveFocus(Qt.OtherFocusReason)
                if (cursorPosition !== undefined) input.cursorPosition = cursorPosition
                if (selectionStart !== undefined && selectionEnd > selectionStart)
                    input.select(selectionStart, selectionEnd)
            })
        })
        Qt.callLater(root.flushPlanEdits)
    }

    function flushPlanEdits() {
        var edits = pendingPlanEdits
        pendingPlanEdits = []
        for (var i = 0; i < edits.length; i++) edits[i]()
    }

    Connections {
        target: Qt.application
        function onAboutToQuit() { root.flushPlanEdits() }
    }

    function durationMinutes(value) {
        var digits = value.replace(/[^0-9]/g, "")
        return digits === "" ? -1 : Number(digits)
    }

    function durationText(minutes) {
        return minutes > 0 ? minutes + "분" : ""
    }

    function updateExplicitOrder(order, key, hasValue) {
        var updated = order.slice()
        var previous = updated.indexOf(key)
        if (previous >= 0)
            updated.splice(previous, 1)
        if (hasValue)
            updated.push(key)
        return updated
    }

    function generatedTarget(order) {
        if (order.length < 2)
            return ""
        var sources = order.slice(-2)
        var keys = ["start", "end", "duration"]
        for (var index = 0; index < keys.length; index++) {
            if (sources.indexOf(keys[index]) < 0)
                return keys[index]
        }
        return ""
    }

    function calculatedValue(target, fields) {
        var start = fields.start.minutes()
        var end = fields.end.minutes()
        var duration = durationMinutes(fields.duration.text)
        if (target === "end" && start >= 0 && duration > 0)
            return {"minutes": start + duration, "text": ""}
        if (target === "start" && end >= 0 && duration > 0)
            return {"minutes": end - duration, "text": ""}
        if (target === "duration" && start >= 0 && end >= 0) {
            var difference = (end - start + 24 * 60) % (24 * 60)
            return {"minutes": -1, "text": durationText(difference === 0 ? 24 * 60 : difference)}
        }
        return null
    }

    function setCalculatedField(target, value, fields) {
        if (target === "duration") {
            fields.duration.text = value.text
            fields.duration.calculated = true
        } else {
            fields[target].setMinutes(value.minutes)
            fields[target].calculated = true
        }
    }

    ListModel {
        id: planModel
        ListElement { taskId: -1; taskState: 0; title: "영어 독해 지문 2개"; start: "09:00"; end: "09:40"; duration: "40분"; pinned: false; generatedField: "end"; actualStudy: "0분"; actualFocus: "0분" }
        ListElement { taskId: -2; taskState: 1; title: "수학 오답노트 정리"; start: "11:00"; end: "12:00"; duration: "60분"; pinned: false; generatedField: "end"; actualStudy: "0분"; actualFocus: "0분" }
        ListElement { taskId: -3; taskState: 2; title: "한국사 4강 복습"; start: "14:20"; end: "15:00"; duration: "40분"; pinned: false; generatedField: "end"; actualStudy: "0분"; actualFocus: "0분" }
        ListElement { taskId: -4; taskState: 0; title: "과학 개념 문제 20개"; start: "20:00"; end: "21:00"; duration: "60분"; pinned: false; generatedField: "end"; actualStudy: "0분"; actualFocus: "0분" }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            Text { text: "오늘의 학습 계획"; color: Theme.text; font.pixelSize: 20; font.weight: Font.Bold }
            Rectangle {
                visible: root.backendObject && root.backendObject.plannerUsesSampleData
                Layout.preferredWidth: 62
                Layout.preferredHeight: 24
                radius: Theme.radiusSmall
                color: Theme.primarySoft
                Text { anchors.centerIn: parent; text: "예시 데이터"; color: Theme.primary; font.pixelSize: 9; font.weight: Font.DemiBold }
            }
            Item { Layout.fillWidth: true }
            ActionButton { text: "‹"; onClicked: { if (root.backendObject) root.backendObject.shiftPlannerDate(-1); root.feedbackRequested("이전 날짜") } }
            Button {
                id: plannerDateButton
                Layout.preferredWidth: 190
                Layout.preferredHeight: 42
                text: root.backendObject ? root.backendObject.plannerDayLabel : "2026년 7월 20일"
                ToolTip.visible: hovered
                ToolTip.text: "캘린더 열기"
                onClicked: plannerCalendar.openForDate(root.backendObject ? root.backendObject.plannerDateIso : "2026-07-20")
                background: Rectangle { radius: Theme.radius; color: plannerDateButton.hovered ? Theme.primarySoft : Theme.surface; border.color: plannerDateButton.hovered ? "#BFD5FF" : Theme.border }
                contentItem: Text { text: plannerDateButton.text; color: Theme.text; font.pixelSize: 13; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            }
            ActionButton { text: "›"; onClicked: { if (root.backendObject) root.backendObject.shiftPlannerDate(1); root.feedbackRequested("다음 날짜") } }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumWidth: 560
                radius: Theme.radius
                color: Theme.surface
                border.color: Theme.border

                ColumnLayout {
                    id: plannerColumn
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 9
                    property var quickExplicitOrder: []
                    property string quickGeneratedKey: ""
                    property string quickDerivedField: ""

                    function quickFields() {
                        return {"start": startInput, "end": endInput, "duration": durationInput}
                    }

                    function confirmQuickCalculation() {
                        if (quickGeneratedKey === "")
                            return
                        quickFields()[quickGeneratedKey].calculated = false
                        quickGeneratedKey = ""
                    }

                    function addQuickTask() {
                        if (!startInput.normalize()) {
                            startInput.invalidCommitted()
                            startInput.focusFirst()
                            return
                        }
                        if (!endInput.normalize()) {
                            endInput.invalidCommitted()
                            endInput.focusFirst()
                            return
                        }
                        var derivedField = quickDerivedField || quickGeneratedKey
                        confirmQuickCalculation()
                        if (taskInput.text.trim() === "") {
                            root.feedbackRequested("할 일을 입력하세요.")
                            return
                        }
                        if (root.backendObject) {
                            if (!root.backendObject.addPlannerTask(taskInput.text, startInput.text, endInput.text, durationInput.text, derivedField)) {
                                root.feedbackRequested("계획을 추가하지 못했습니다.")
                                return
                            }
                        } else {
                            planModel.append({taskId: -(planModel.count + 10), taskState: 0, title: taskInput.text, start: startInput.text, end: endInput.text, duration: durationInput.text, pinned: false, generatedField: derivedField, actualStudy: "0분", actualFocus: "0분"})
                        }
                        taskInput.clear(); startInput.text = ""; endInput.text = ""; durationInput.clear()
                        quickExplicitOrder = []
                        quickDerivedField = ""
                        root.feedbackRequested("계획을 추가했습니다.")
                        taskInput.forceActiveFocus(Qt.TabFocusReason)
                    }

                    function quickScheduleEdited(key, userEdited) {
                        var fields = quickFields()
                        if (quickGeneratedKey !== "") {
                            fields[quickGeneratedKey].calculated = false
                            quickGeneratedKey = ""
                            if (!userEdited)
                                return
                        }
                        if (userEdited) {
                            quickDerivedField = ""
                            var valid = key === "duration" ? root.durationMinutes(fields.duration.text) > 0 : fields[key].minutes() >= 0
                            quickExplicitOrder = root.updateExplicitOrder(quickExplicitOrder, key, valid)
                        }
                        var target = root.generatedTarget(quickExplicitOrder)
                        if (target === "")
                            return
                        var value = root.calculatedValue(target, fields)
                        if (value !== null) {
                            root.setCalculatedField(target, value, fields)
                            quickGeneratedKey = target
                            quickDerivedField = target
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 7
                        TextField {
                            id: taskInput
                            objectName: "plannerTaskInput"
                            Layout.fillWidth: true
                            implicitHeight: 40
                            placeholderText: "오늘 할 공부를 입력하세요"
                            color: Theme.text
                            placeholderTextColor: Theme.muted
                            selectionColor: Theme.primary
                            selectedTextColor: "#FFFFFF"
                            background: Rectangle {
                                radius: Theme.radiusSmall
                                color: Theme.surface
                                border.color: taskInput.activeFocus ? Theme.primary : Theme.border
                            }
                            onAccepted: plannerColumn.addQuickTask()
                            Keys.onTabPressed: function(event) {
                                startInput.focusFirst()
                                event.accepted = true
                            }
                        }
                        ClockEntry {
                            id: startInput
                            objectName: "plannerStartInput"
                            previousTabItem: taskInput
                            nextTabItem: endInput
                            Layout.preferredWidth: 82
                            onValueCommitted: plannerColumn.quickScheduleEdited("start", userEdited)
                            onAccepted: plannerColumn.addQuickTask()
                            onInvalidCommitted: root.feedbackRequested("시간은 00:00부터 23:59 사이로 입력하세요.")
                        }
                        ClockEntry {
                            id: endInput
                            objectName: "plannerEndInput"
                            previousTabItem: startInput
                            nextTabItem: durationInput
                            Layout.preferredWidth: 82
                            onValueCommitted: plannerColumn.quickScheduleEdited("end", userEdited)
                            onAccepted: plannerColumn.addQuickTask()
                            onInvalidCommitted: root.feedbackRequested("시간은 00:00부터 23:59 사이로 입력하세요.")
                        }
                        TextField {
                            id: durationInput
                            objectName: "plannerDurationInput"
                            Layout.preferredWidth: 72
                            implicitHeight: 40
                            property bool calculated: false
                            property bool dirty: false
                            placeholderText: "_분"
                            color: calculated ? Theme.muted : Theme.text
                            placeholderTextColor: Theme.muted
                            selectionColor: Theme.primary
                            selectedTextColor: "#FFFFFF"
                            font.italic: calculated
                            horizontalAlignment: Text.AlignHCenter
                            background: Rectangle { radius: Theme.radiusSmall; color: durationInput.calculated ? "#F3F5F7" : Theme.surface; border.color: durationInput.activeFocus ? Theme.primary : Theme.border }
                            onTextEdited: {
                                dirty = true
                                calculated = false
                            }
                            onEditingFinished: {
                                var wasEdited = dirty
                                var minutes = root.durationMinutes(text)
                                if (minutes > 0)
                                    text = root.durationText(minutes)
                                dirty = false
                                plannerColumn.quickScheduleEdited("duration", wasEdited)
                            }
                            onAccepted: plannerColumn.addQuickTask()
                            Keys.onBacktabPressed: function(event) {
                                endInput.focusLast()
                                event.accepted = true
                            }
                            Keys.onTabPressed: function(event) {
                                addButton.forceActiveFocus(Qt.TabFocusReason)
                                event.accepted = true
                            }
                        }
                        ActionButton {
                            id: addButton
                            objectName: "plannerAddButton"
                            text: "+"
                            tone: "primary"
                            KeyNavigation.backtab: durationInput
                            KeyNavigation.tab: taskInput
                            onClicked: {
                                plannerColumn.addQuickTask()
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text { Layout.preferredWidth: 34; text: "상태"; color: Theme.muted; font.pixelSize: 10 }
                        Text { Layout.fillWidth: true; text: "할 일"; color: Theme.muted; font.pixelSize: 10 }
                        Text { Layout.preferredWidth: 82; text: "시작"; color: Theme.muted; font.pixelSize: 10 }
                        Text { Layout.preferredWidth: 82; text: "종료"; color: Theme.muted; font.pixelSize: 10 }
                        Text { Layout.preferredWidth: 72; text: "예상"; color: Theme.muted; font.pixelSize: 10 }
                        Item { Layout.preferredWidth: 30 }
                        Item { Layout.preferredWidth: 34 }
                    }

                    ListView {
                        id: planList
                        objectName: "plannerPlanList"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 6
                        clip: true
                        model: root.backendObject ? root.backendObject.plannerTasks : planModel
                        delegate: Rectangle {
                            id: planRow
                            required property int index
                            required property int taskId
                            required property int taskState
                            required property string title
                            required property string start
                            required property string end
                            required property string duration
                            required property string generatedField
                            required property bool pinned
                            required property string actualStudy
                            required property string actualFocus
                            property var explicitOrder: {
                                if (generatedField === "end") return ["start", "duration"]
                                if (generatedField === "start") return ["end", "duration"]
                                if (generatedField === "duration") return ["start", "end"]
                                if (start !== "" && duration !== "") return ["start", "duration"]
                                if (start !== "" && end !== "") return ["start", "end"]
                                if (end !== "" && duration !== "") return ["end", "duration"]
                                if (start !== "") return ["start"]
                                if (end !== "") return ["end"]
                                if (duration !== "") return ["duration"]
                                return []
                            }
                            property string generatedKey: ""
                            property string derivedField: generatedField
                            width: planList.width
                            height: 56
                            radius: Theme.radius
                            color: planRow.taskState === 1 ? Theme.successSoft : planRow.taskState === 2 ? Theme.warningSoft : Theme.surfaceSoft
                            border.color: Theme.border

                            function commit(changedField) {
                                if (root.backendObject) {
                                    root.savePlanEdit(planRow.taskId, titleEdit.text, startEdit.text, endEdit.text, durationEdit.text, changedField || "", derivedField)
                                } else {
                                    planModel.setProperty(planRow.index, "title", titleEdit.text)
                                    planModel.setProperty(planRow.index, "start", startEdit.text)
                                    planModel.setProperty(planRow.index, "end", endEdit.text)
                                    planModel.setProperty(planRow.index, "duration", durationEdit.text)
                                }
                            }

                            function scheduleFields() {
                                return {"start": startEdit, "end": endEdit, "duration": durationEdit}
                            }

                            function preferredOrder(key, fields) {
                                var startValid = fields.start.minutes() >= 0
                                var endValid = fields.end.minutes() >= 0
                                var durationValid = root.durationMinutes(fields.duration.text) > 0
                                if (key === "start") {
                                    if (durationValid) return ["duration", "start"]
                                    if (endValid) return ["end", "start"]
                                } else if (key === "end") {
                                    if (startValid) return ["start", "end"]
                                    if (durationValid) return ["duration", "end"]
                                } else if (key === "duration") {
                                    if (startValid) return ["start", "duration"]
                                    if (endValid) return ["end", "duration"]
                                }
                                return root.updateExplicitOrder(explicitOrder, key, true)
                            }

                            function scheduleEdited(key, userEdited) {
                                var fields = scheduleFields()
                                if (generatedKey !== "") {
                                    fields[generatedKey].calculated = false
                                    generatedKey = ""
                                    if (!userEdited) {
                                        commit()
                                        return
                                    }
                                }
                                if (userEdited) {
                                    derivedField = ""
                                    var valid = key === "duration" ? root.durationMinutes(fields.duration.text) > 0 : fields[key].minutes() >= 0
                                    explicitOrder = valid ? preferredOrder(key, fields) : root.updateExplicitOrder(explicitOrder, key, false)
                                }
                                var target = root.generatedTarget(explicitOrder)
                                if (target !== "") {
                                    var value = root.calculatedValue(target, fields)
                                    if (value !== null) {
                                        root.setCalculatedField(target, value, fields)
                                        generatedKey = target
                                        derivedField = target
                                        commit(key)
                                        return
                                    }
                                }
                                commit(userEdited ? key : "")
                            }

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 7
                                anchors.rightMargin: 7
                                spacing: 7

                                Button {
                                    id: stateButton
                                    Layout.preferredWidth: 30
                                    Layout.preferredHeight: 30
                                    text: planRow.taskState === 1 ? "✓" : planRow.taskState === 2 ? "Ⅱ" : "○"
                                    ToolTip.visible: hovered
                                    ToolTip.text: planRow.taskState === 0 ? "완료로 변경" : planRow.taskState === 1 ? "보류로 변경" : "공란으로 변경"
                                    onClicked: {
                                        if (root.backendObject)
                                            root.backendObject.cyclePlannerTask(planRow.taskId)
                                        else
                                            planModel.setProperty(planRow.index, "taskState", (planRow.taskState + 1) % 3)
                                    }
                                    background: Rectangle { radius: 6; color: planRow.taskState === 1 ? Theme.success : planRow.taskState === 2 ? Theme.warning : Theme.surface; border.color: planRow.taskState === 0 ? "#B8C0CB" : "transparent" }
                                    contentItem: Text { text: stateButton.text; color: planRow.taskState === 0 ? Theme.muted : "white"; font.pixelSize: 13; font.weight: Font.Bold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    spacing: 0

                                    TextField {
                                        id: titleEdit
                                        objectName: "plannerRowTitle" + planRow.taskId
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        text: planRow.title
                                        color: planRow.taskState === 1 ? "#356148" : planRow.taskState === 2 ? "#7A4A00" : Theme.text
                                        placeholderTextColor: Theme.muted
                                        selectionColor: Theme.primary
                                        selectedTextColor: "#FFFFFF"
                                        font.pixelSize: 12
                                        font.weight: Font.DemiBold
                                        selectByMouse: true
                                        background: Item {}
                                        onEditingFinished: planRow.commit("")
                                        Keys.onTabPressed: function(event) {
                                            startEdit.focusFirst()
                                            event.accepted = true
                                        }
                                        Keys.onBacktabPressed: function(event) {
                                            stateButton.forceActiveFocus(Qt.BacktabFocusReason)
                                            event.accepted = true
                                        }
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 14
                                        text: "실제 " + planRow.actualStudy + " · 집중 " + planRow.actualFocus
                                        color: Theme.muted
                                        font.pixelSize: 9
                                        elide: Text.ElideRight
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }
                                ClockEntry {
                                    id: startEdit
                                    objectName: "plannerRowStart" + planRow.taskId
                                    Layout.preferredWidth: 82
                                    text: planRow.start
                                    previousTabItem: titleEdit
                                    nextTabItem: endEdit
                                    onValueCommitted: planRow.scheduleEdited("start", userEdited)
                                    onInvalidCommitted: root.feedbackRequested("시간은 00:00부터 23:59 사이로 입력하세요.")
                                }
                                ClockEntry {
                                    id: endEdit
                                    objectName: "plannerRowEnd" + planRow.taskId
                                    Layout.preferredWidth: 82
                                    text: planRow.end
                                    previousTabItem: startEdit
                                    nextTabItem: durationEdit
                                    onValueCommitted: planRow.scheduleEdited("end", userEdited)
                                    onInvalidCommitted: root.feedbackRequested("시간은 00:00부터 23:59 사이로 입력하세요.")
                                }
                                TextField {
                                    id: durationEdit
                                    objectName: "plannerRowDuration" + planRow.taskId
                                    Layout.preferredWidth: 72
                                    text: planRow.duration
                                    property bool calculated: false
                                    property bool dirty: false
                                    placeholderText: "--분"
                                    color: calculated ? Theme.muted : Theme.text
                                    placeholderTextColor: Theme.muted
                                    selectionColor: Theme.primary
                                    selectedTextColor: "#FFFFFF"
                                    font.italic: calculated
                                    horizontalAlignment: Text.AlignHCenter
                                    background: Item {}
                                    onTextEdited: {
                                        dirty = true
                                        calculated = false
                                    }
                                    onEditingFinished: {
                                        var wasEdited = dirty
                                        var minutes = root.durationMinutes(text)
                                        if (minutes > 0)
                                            text = root.durationText(minutes)
                                        dirty = false
                                        planRow.scheduleEdited("duration", wasEdited)
                                    }
                                    Keys.onBacktabPressed: function(event) {
                                        endEdit.focusLast()
                                        event.accepted = true
                                    }
                                    Keys.onTabPressed: function(event) {
                                        pinButton.forceActiveFocus(Qt.TabFocusReason)
                                        event.accepted = true
                                    }
                                }
                                Button {
                                    id: pinButton
                                    Layout.preferredWidth: 30
                                    Layout.preferredHeight: 30
                                    text: "📌"
                                    KeyNavigation.backtab: durationEdit
                                    KeyNavigation.tab: deleteButton
                                    ToolTip.visible: hovered
                                    ToolTip.text: planRow.pinned ? "매일 반복 해제" : "매일 반복으로 고정"
                                    onClicked: {
                                        var wasPinned = planRow.pinned
                                        if (root.backendObject)
                                            root.backendObject.togglePlannerTaskFixed(planRow.taskId)
                                        else
                                            planModel.setProperty(planRow.index, "pinned", !planRow.pinned)
                                        root.feedbackRequested(wasPinned ? "고정 스케줄을 해제했습니다." : "매일 반복 스케줄로 고정했습니다.")
                                    }
                                    background: Rectangle {
                                        radius: 6
                                        color: planRow.pinned ? Theme.primarySoft : pinButton.hovered ? Theme.surface : "transparent"
                                        border.color: planRow.pinned ? "#BFD5FF" : "transparent"
                                    }
                                    contentItem: Text {
                                        text: pinButton.text
                                        color: planRow.pinned ? Theme.primary : Theme.muted
                                        font.pixelSize: 15
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }
                                Button {
                                    id: deleteButton
                                    Layout.preferredWidth: 30
                                    Layout.preferredHeight: 30
                                    text: "×"
                                    KeyNavigation.backtab: pinButton
                                    onClicked: {
                                        if (root.backendObject)
                                            root.backendObject.deletePlannerTask(planRow.taskId)
                                        else
                                            planModel.remove(planRow.index)
                                        root.feedbackRequested("계획을 삭제했습니다.")
                                    }
                                    background: Rectangle { radius: 6; color: deleteButton.hovered ? Theme.dangerSoft : "transparent" }
                                    contentItem: Text { text: deleteButton.text; color: Theme.danger; font.pixelSize: 18; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "○ 공란"; color: Theme.muted; font.pixelSize: 10 }
                        Text { text: "✓ 완료"; color: Theme.success; font.pixelSize: 10 }
                        Text { text: "Ⅱ 보류"; color: Theme.warning; font.pixelSize: 10 }
                        Item { Layout.fillWidth: true }
                        Text { text: "시간은 선택 입력"; color: Theme.muted; font.pixelSize: 10 }
                    }
                }
            }

            Rectangle {
                Layout.preferredWidth: Math.max(350, root.width * 0.34)
                Layout.fillHeight: true
                radius: Theme.radius
                color: Theme.surface
                border.color: Theme.border

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "실제 학습 타임라인"; color: Theme.text; font.pixelSize: 15; font.weight: Font.Bold }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: "순공 " + (root.backendObject ? root.backendObject.plannerDailySummary.focus : "1시간 22분")
                            color: Theme.success
                            font.pixelSize: 11
                            font.weight: Font.DemiBold
                        }
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: Theme.radius
                        color: Theme.surfaceSoft
                        DailyPlannerTimeline {
                            anchors.fill: parent
                            anchors.margins: 12
                            plannerTasks: root.backendObject ? root.backendObject.plannerTasks : []
                            hourlyData: root.backendObject ? root.backendObject.plannerHourlyData : []
                            studyDayStartHour: root.backendObject ? Number(root.backendObject.settings.study_day_start_hour || 0) : 0
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Rectangle { Layout.preferredWidth: 24; Layout.preferredHeight: 8; radius: 2; color: Theme.success }
                        Text { text: "실제 집중도"; color: Theme.muted; font.pixelSize: 9 }
                        Item { Layout.fillWidth: true }
                        Text { text: "점선 계획 · 실선 완료"; color: Theme.muted; font.pixelSize: 9 }
                    }
                }
            }
        }
    }

    PlannerCalendarPopup {
        id: plannerCalendar
        parent: root
        backendObject: root.backendObject
        onFeedbackRequested: function(message) { root.feedbackRequested(message) }
    }
}
