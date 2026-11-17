pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "."
import "components"
import "pages"

ApplicationWindow {
    id: window
    objectName: "learningWindow"
    width: 1280
    height: 720
    minimumWidth: 1024
    minimumHeight: 680
    visible: true
    title: "집중 학습"
    color: Theme.background
    font.family: StudyStyle.family

    property bool pomodoroMode: true
    property bool sessionRunning: false
    property bool sessionPaused: false
    property bool sessionEnded: false
    property bool studyPreparation: false
    readonly property string studyViewState: sessionRunning ? (sessionPaused ? "break" : "study") : sessionEnded ? "result" : "ready"
    property bool cameraVisible: true
    property int elapsedSeconds: 0
    property int todayStudySeconds: backendObject ? backendObject.todayStudySeconds + (measurementObject && measurementObject.sessionRunning ? measurementObject.todayStudySeconds : 0) : 0
    readonly property int todayFocusSeconds: (backendObject ? backendObject.todayFocusSeconds : 0) + (measurementObject && measurementObject.sessionRunning ? measurementObject.todayFocusSeconds : 0)
    property int pomodoroSeconds: focusMinutes * 60
    property int focusMinutes: 25
    property int breakMinutes: 5
    property int targetRounds: 4
    property int longBreakMinutes: 15
    property bool autoStartBreak: true
    property bool autoStartNext: false
    property int completedRounds: 0
    property string currentTask: "선택된 할 일이 없습니다"
    property string currentTaskSchedule: "오늘 계획에서 선택하세요"
    property int currentTaskId: -1
    property bool currentTaskAvailable: false
    property bool currentTaskAutoSelected: false
    property int recommendedTaskId: -1
    property string recommendedTaskTitle: ""
    property string recommendedTaskSchedule: ""
    property int lastTaskCheckMinute: -1
    property date currentDateTime: new Date()
    property int currentTabIndex: 0
    property var backendObject: null
    property var measurementObject: null

    function measurementColor() {
        if (!measurementObject) return Theme.muted
        if (!measurementObject.cameraConnected && !sessionPaused) return Theme.warning
        switch (measurementObject.effectiveState) {
        case "focus": return Theme.success
        case "non_focus": return Theme.danger
        case "unscored":
        case "absent_pending": return Theme.warning
        default: return Theme.muted
        }
    }

    function twoDigits(value) {
        return value < 10 ? "0" + value : value
    }

    function durationText(seconds, includeHours) {
        var safe = Math.max(0, seconds)
        var hours = Math.floor(safe / 3600)
        var minutes = Math.floor((safe % 3600) / 60)
        var secs = safe % 60
        if (includeHours || hours > 0)
            return twoDigits(hours) + ":" + twoDigits(minutes) + ":" + twoDigits(secs)
        return twoDigits(minutes) + ":" + twoDigits(secs)
    }

    function startStudySession() {
        if (sessionRunning) { if (currentTabIndex === 0) studyPreparation = false; return }
        if (measurementObject) {
            var selectedTaskId = currentTaskAvailable ? currentTaskId : -1
            var selectedTaskTitle = currentTaskAvailable ? currentTask : ""
            if (backendObject) {
                backendObject.saveSettings({
                    session_mode: pomodoroMode ? "pomodoro" : "free",
                    pomodoro_focus_minutes: focusMinutes,
                    pomodoro_short_break_minutes: breakMinutes,
                    pomodoro_cycles: targetRounds,
                    pomodoro_long_break_minutes: longBreakMinutes,
                    pomodoro_auto_start_break: autoStartBreak,
                    pomodoro_auto_start_next: autoStartNext
                })
                measurementObject.reloadSettings()
            }
            if (!measurementObject.startSession(pomodoroMode ? "pomodoro" : "free", selectedTaskId, selectedTaskTitle, "")) {
                currentTabIndex = 1
                return
            }
        }
        elapsedSeconds = 0
        pomodoroSeconds = focusMinutes * 60
        completedRounds = 0
        sessionRunning = true
        sessionPaused = false
        sessionEnded = false
        studyPreparation = false
        currentTabIndex = 0
    }

    function endStudySession() {
        if (measurementObject && measurementObject.sessionRunning)
            measurementObject.endSession()
        sessionRunning = false
        sessionPaused = false
        sessionEnded = true
        studyPreparation = false
    }

    function applyBackendSettings() {
        if (!backendObject) return
        var stored = backendObject.settings
        cameraVisible = !stored.camera_preview_hidden
        if (sessionRunning) return
        focusMinutes = stored.pomodoro_focus_minutes || 25
        breakMinutes = stored.pomodoro_short_break_minutes || 5
        targetRounds = stored.pomodoro_cycles || 4
        longBreakMinutes = stored.pomodoro_long_break_minutes || 15
        autoStartBreak = stored.pomodoro_auto_start_break
        autoStartNext = stored.pomodoro_auto_start_next
        pomodoroSeconds = focusMinutes * 60
        pomodoroMode = stored.session_mode === "pomodoro"
    }

    function parseClock(value) {
        if (!value || value.indexOf(":") < 0) return -1
        var parts = value.split(":")
        var hour = Number(parts[0])
        var minute = Number(parts[1])
        if (isNaN(hour) || isNaN(minute)) return -1
        return hour * 60 + minute
    }

    function refreshScheduledTask() {
        var nowMinute = currentDateTime.getHours() * 60 + currentDateTime.getMinutes()
        var source = backendObject ? backendObject.todayPlannerTasks : todayTasks
        var bestTask = null
        var bestStart = -1
        var sourceCount = backendObject ? source.length : source.count
        var incompleteCount = 0
        var deferredCount = 0
        var currentTaskStillAvailable = false
        for (var i = 0; i < sourceCount; i++) {
            var task = backendObject ? source[i] : source.get(i)
            if (task.taskState === 2) {
                deferredCount += 1
                continue
            }
            if (task.done || task.taskState === 1) continue
            incompleteCount += 1
            if (currentTaskAvailable && task.taskId === currentTaskId)
                currentTaskStillAvailable = true
            var start = parseClock(task.start)
            if (start < 0) continue
            var end = parseClock(task.end)
            if (end < 0) {
                var duration = Number(String(task.duration || "").replace(/[^0-9]/g, ""))
                end = start + (isNaN(duration) || duration <= 0 ? 60 : duration)
            }
            var active = end >= start ? nowMinute >= start && nowMinute < end : nowMinute >= start || nowMinute < end
            if (active && start >= bestStart) {
                bestStart = start
                bestTask = task
            }
        }
        recommendedTaskId = bestTask ? bestTask.taskId : -1
        recommendedTaskTitle = bestTask ? bestTask.title : ""
        recommendedTaskSchedule = bestTask ? bestTask.detail : ""
        if (!currentTaskStillAvailable && measurementObject && measurementObject.sessionRunning && measurementObject.selectedTaskId > 0)
            measurementObject.selectTask(-1, "")
        if (currentTaskStillAvailable) {
            for (var selectedIndex = 0; selectedIndex < sourceCount; selectedIndex++) {
                var selected = backendObject ? source[selectedIndex] : source.get(selectedIndex)
                if (selected.taskId === currentTaskId) {
                    currentTask = selected.title
                    currentTaskSchedule = selected.detail
                    break
                }
            }
            currentTaskAvailable = true
            currentTaskAutoSelected = false
        } else if (sourceCount > 0 && incompleteCount === 0) {
            currentTask = deferredCount > 0 ? "보류된 할 일만 남았습니다" : "모든 목표를 완료했습니다!"
            currentTaskSchedule = "-"
            currentTaskId = -1
            currentTaskAvailable = false
            currentTaskAutoSelected = false
        } else {
            currentTask = sourceCount > 0 ? "선택된 할 일이 없습니다" : "오늘 계획이 없습니다"
            currentTaskSchedule = sourceCount > 0 ? "오늘 계획에서 선택하세요" : "플래너에서 계획을 추가하세요"
            currentTaskId = -1
            currentTaskAvailable = false
            currentTaskAutoSelected = false
        }
    }

    function chooseStudyTask(taskId, title, detail) {
        if (measurementObject && measurementObject.sessionRunning && !measurementObject.selectTask(taskId, title))
            return
        currentTask = title
        currentTaskSchedule = detail
        currentTaskId = taskId
        currentTaskAvailable = true
        currentTaskAutoSelected = false
        feedback.showMessage("지금 할 일을 변경했습니다.")
    }

    function openStudyRecords() { recordsPage.openStudyRecords() }

    function toggleStudyTask(taskId, title, detail) {
        if (currentTaskAvailable && currentTaskId === taskId) {
            if (measurementObject && measurementObject.sessionRunning && !measurementObject.selectTask(-1, "")) return
            currentTaskAvailable = false
            currentTaskId = -1
            refreshScheduledTask()
            feedback.showMessage("할 일 선택을 해제했습니다.")
        } else {
            chooseStudyTask(taskId, title, detail)
        }
    }

    Connections {
        target: window.backendObject
        enabled: window.backendObject !== null
        ignoreUnknownSignals: true
        function onDataChanged() { window.refreshScheduledTask() }
        function onSettingsChanged() { window.applyBackendSettings() }
    }

    Connections {
        target: window.measurementObject
        enabled: window.measurementObject !== null
        ignoreUnknownSignals: true
        function onStateChanged() {
            var justStarted = !window.sessionRunning && window.measurementObject.sessionRunning
            var justEnded = window.sessionRunning && !window.measurementObject.sessionRunning
            window.sessionRunning = window.measurementObject.sessionRunning
            window.sessionPaused = window.measurementObject.sessionPaused
            window.sessionEnded = window.measurementObject.appState === "result"
            if (justStarted) {
                window.studyPreparation = false
                window.currentTabIndex = 0
                window.pomodoroMode = window.measurementObject.sessionMode === "pomodoro"
            }
            if (window.measurementObject.calibrationTarget !== "screen"
                && window.measurementObject.calibrationTarget !== "validation"
                && !(window.measurementObject.calibrationTarget === "" && window.measurementObject.screenCalibrationFailed)
                && screenCalibrationWindow.visible) {
                screenCalibrationWindow.finishAndClose()
            }
            if (window.sessionRunning || window.measurementObject.appState === "result")
                window.elapsedSeconds = window.measurementObject.elapsedSeconds
            if (window.measurementObject.pomodoroPhase !== "idle") {
                window.pomodoroSeconds = window.measurementObject.pomodoroRemainingSeconds
                window.completedRounds = window.measurementObject.pomodoroCompletedRounds
            }
            if (justEnded) {
                window.studyPreparation = false
                window.applyBackendSettings()
            }
        }
        function onFeedback(message) { feedback.showMessage(message) }
        function onScreenCalibrationRequested() { screenCalibrationWindow.openOn(window.screen) }
        function onRecordsChanged() { if (window.backendObject) window.backendObject.refresh() }
    }

    Timer {
        objectName: "wallClockTimer"
        interval: 1000
        repeat: true
        running: true
        onTriggered: {
            window.currentDateTime = new Date()
            if (window.backendObject)
                window.backendObject.refreshToday()
            var minute = window.currentDateTime.getMinutes()
            if (minute !== window.lastTaskCheckMinute) {
                window.lastTaskCheckMinute = minute
                window.refreshScheduledTask()
            }
            if (!window.measurementObject && window.sessionRunning && !window.sessionPaused) {
                window.elapsedSeconds += 1
                if (!window.backendObject)
                    window.todayStudySeconds += 1
                if (window.pomodoroMode && !window.measurementObject && window.pomodoroSeconds > 0)
                    window.pomodoroSeconds -= 1
            }
        }
    }

    ListModel {
        id: todayTasks
        ListElement { taskId: -1; taskState: 0; title: "영어 독해 지문 2개"; start: "09:00"; end: "09:40"; duration: "40분"; detail: "09:00 - 09:40"; done: false; pinned: false }
        ListElement { taskId: -2; taskState: 1; title: "수학 오답노트 정리"; start: "11:00"; end: "12:00"; duration: "60분"; detail: "11:00 - 12:00"; done: true; pinned: false }
        ListElement { taskId: -3; taskState: 2; title: "한국사 4강 복습"; start: "14:20"; end: "15:00"; duration: "40분"; detail: "14:20 - 15:00"; done: false; pinned: false }
        ListElement { taskId: -4; taskState: 0; title: "과학 개념 문제 20개"; start: "20:00"; end: "21:00"; duration: "60분"; detail: "20:00 - 21:00"; done: false; pinned: false }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            id: navigationHeader
            objectName: "navigationHeader"
            Layout.fillWidth: true
            Layout.preferredHeight: 64
            color: "white"
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: StudyStyle.line }
            Row {
                id: navigation
                x: 24; height: parent.height; spacing: 8
                Repeater {
                    model: ["학습", "측정", "플래너", "기록", "설정"]
                    delegate: StudyButton {
                        id: navButton
                        required property int index
                        required property string modelData
                        objectName: "navigationButton" + index
                        height: 64; implicitWidth: 64; text: modelData; tone: "quiet"
                        onClicked: window.currentTabIndex = index
                        contentItem: StudyText {
                            text: navButton.text
                            font.pixelSize: 15
                            font.weight: window.currentTabIndex === navButton.index ? Font.DemiBold : Font.Normal
                            color: window.currentTabIndex === navButton.index ? StudyStyle.accent : StudyStyle.muted
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }
            }
            Rectangle {
                objectName: "navigationIndicator"
                x: navigation.x + window.currentTabIndex * 72 + 8
                y: parent.height - height
                width: 48; height: 2; color: StudyStyle.accent
                Behavior on x { NumberAnimation { duration: StudyStyle.normal; easing.type: Easing.OutCubic } }
            }
            Row {
                anchors.right: parent.right; anchors.rightMargin: 24
                anchors.verticalCenter: parent.verticalCenter; spacing: 12
                StudyButton {
                    objectName: "returnPreparation"
                    visible: window.currentTabIndex === 0 && window.sessionRunning && !window.studyPreparation
                    width: window.width >= 1180 ? 112 : 40
                    tone: "quiet"; text: window.width >= 1180 ? "학습 준비" : ""; symbol: "chevron-left"; hint: "학습 준비"
                    onClicked: window.studyPreparation = true
                }
                StudyButton {
                    objectName: "openStudyTools"
                    visible: window.currentTabIndex === 0
                    width: window.width >= 1180 ? 112 : 40
                    tone: "quiet"; text: window.width >= 1180 ? "학습 도구" : ""; symbol: "list-checks"; hint: "학습 도구"
                    onClicked: learningPage.openTools(0)
                }
                StudyButton {
                    objectName: "primaryDdayButton"
                    visible: window.backendObject && window.backendObject.hasPrimaryDday
                    width: 174; height: 44; tone: "quiet"
                    text: window.backendObject ? window.backendObject.primaryDdayLabel + " " + window.backendObject.primaryDdayTitle : ""
                    hint: "대표 D-day 일정 보기"
                    contentItem: StudyText { text: parent.text; width: 174; elide: Text.ElideRight; font.pixelSize: 17; font.weight: Font.Medium; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    onClicked: {
                        window.currentTabIndex = 2
                        plannerPage.openCalendarForDate(window.backendObject.primaryDdayDate)
                    }
                }
                Item {
                    width: 172; height: 44
                    StudyText { anchors.right: parent.right; text: Qt.formatTime(window.currentDateTime, "HH:mm"); font.pixelSize: 24; font.weight: Font.Medium }
                    StudyText { anchors.right: parent.right; y: 29; text: Qt.formatDate(window.currentDateTime, "yyyy. MM. dd.") + " " + ["일요일", "월요일", "화요일", "수요일", "목요일", "금요일", "토요일"][window.currentDateTime.getDay()]; font.pixelSize: 14; color: StudyStyle.muted }
                }
            }
        }

        LearningPage {
            id: learningPage
            objectName: "learningPage"
            controller: window
            visible: window.currentTabIndex === 0
            Layout.fillWidth: true
            Layout.fillHeight: true
        }

        MeasurementPage {
            visible: window.currentTabIndex === 1
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 18
            measurementObject: window.measurementObject
            cameraVisible: window.cameraVisible
            onCameraVisibleChanged: window.cameraVisible = cameraVisible
            onFeedbackRequested: function(message) { feedback.showMessage(message) }
        }

        PlannerPage {
            id: plannerPage
            visible: window.currentTabIndex === 2
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 18
            backendObject: window.backendObject
            onFeedbackRequested: function(message) { feedback.showMessage(message) }
        }

        RecordsPage {
            id: recordsPage
            visible: window.currentTabIndex === 3
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 18
            backendObject: window.backendObject
            onFeedbackRequested: function(message) { feedback.showMessage(message) }
        }

        SettingsPage {
            visible: window.currentTabIndex === 4
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 18
            backendObject: window.backendObject
            measurementObject: window.measurementObject
            onFeedbackRequested: function(message) { feedback.showMessage(message) }
        }
    }

    Rectangle {
        id: feedback
        objectName: "appFeedbackOverlay"
        visible: window.currentTabIndex !== 0
        anchors.horizontalCenter: parent.horizontalCenter
        y: parent.height - height - 22
        width: Math.min(parent.width - 40, messageText.implicitWidth + 36)
        height: 44
        radius: Theme.radius
        color: Theme.text
        opacity: 0
        scale: 0.96
        z: 100
        Text { id: messageText; anchors.centerIn: parent; color: "white"; font.pixelSize: 13; font.weight: Font.DemiBold }
        Behavior on opacity { NumberAnimation { duration: Theme.normal } }
        Behavior on scale { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }
        Timer { id: feedbackTimer; interval: 1700; onTriggered: { feedback.opacity = 0; feedback.scale = 0.96 } }
        function showMessage(message) {
            learningPage.showFeedback(message)
            messageText.text = message
            opacity = 1
            scale = 1
            feedbackTimer.restart()
        }
    }

    ScreenCalibrationWindow {
        id: screenCalibrationWindow
        measurementObject: window.measurementObject
    }

    onBackendObjectChanged: {
        applyBackendSettings()
        refreshScheduledTask()
    }
}
