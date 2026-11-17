pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import ".."
import "../components"

Rectangle {
    id: page
    objectName: "studySessionPanel"
    required property var controller
    readonly property var backend: controller.backendObject
    readonly property var measurement: controller.measurementObject
    readonly property var tasks: backend ? backend.todayPlannerTasks : []
    readonly property bool preparation: controller.studyPreparation || (!controller.sessionRunning && !controller.sessionEnded)
    readonly property bool result: controller.sessionEnded && !preparation
    readonly property bool resting: controller.sessionPaused && !preparation
    readonly property bool studying: controller.sessionRunning && !preparation && !resting
    readonly property bool waiting: measurement && measurement.pomodoroPhase === "waiting_next"
    readonly property string status: !measurement ? "측정 미연결" : !measurement.cameraConnected && !controller.sessionPaused ? "카메라 연결 확인" : measurement.statusText
    readonly property bool measurementReady: !!(measurement && measurement.cameraConnected && measurement.screenReady && (!measurement.writingRequired || measurement.writingReady))
    readonly property string readinessText: !measurement ? "측정 미연결" : !measurement.cameraConnected ? "카메라 연결 확인" : !measurement.screenReady ? "화면 자세 설정 필요" : measurement.writingRequired && !measurement.writingReady ? "필기 자세 설정 필요" : "기준 자세 완료"
    readonly property int taskRailWidth: 248
    property string feedbackText: ""
    property bool feedbackIsError: false
    property bool pageReady: false
    color: StudyStyle.background

    function openTools(index) { toolTabs.currentIndex = index; tools.open() }
    function closeTools() { tools.close() }
    function showFeedback(message, isError) {
        feedbackText = message
        feedbackIsError = isError === true
        if (feedbackIsError) feedbackTimer.stop()
        else feedbackTimer.restart()
    }
    function nextTask() {
        var selected = -1
        for (var i = 0; i < tasks.length; i++) if (tasks[i].taskId === controller.currentTaskId) selected = i
        for (var step = 1; step <= tasks.length; step++) {
            var task = tasks[(selected + step) % tasks.length]
            if (task.taskState === 0) { controller.chooseStudyTask(task.taskId, task.title, task.detail); return }
        }
    }
    function cycleTask(taskId, focusIndex) {
        if (backend) backend.cyclePlannerTask(taskId)
        if (focusIndex >= 0) Qt.callLater(function() {
            var row = compactTaskList.itemAtIndex(focusIndex)
            if (row) row.focusStatus()
        })
    }
    function primaryAction() {
        if (preparation) {
            if (!controller.sessionRunning && controller.pomodoroMode && (focusInput.invalid || breakInput.invalid || longInput.invalid || roundsInput.invalid)) {
                var inputs = [focusInput, breakInput, roundsInput, longInput]
                for (var i = 0; i < inputs.length; i++) {
                    if (inputs[i].invalid) {
                        showFeedback(inputs[i].label + " 값을 1~" + inputs[i].maximum + " 범위로 입력하세요.", true)
                        break
                    }
                }
                return
            }
            if (feedbackIsError) feedbackText = ""
            feedbackIsError = false
            controller.startStudySession()
        } else if (result) {
            controller.studyPreparation = true
        } else if (measurement) {
            measurement.toggleBreak()
        } else {
            controller.sessionPaused = !controller.sessionPaused
        }
    }
    onVisibleChanged: if (!visible) tools.close()
    onPreparationChanged: { tools.close(); if (pageReady) enterView.restart() }
    onRestingChanged: { tools.close(); if (pageReady) enterView.restart() }
    onResultChanged: { tools.close(); if (pageReady) enterView.restart() }
    Component.onCompleted: pageReady = true
    Timer { id: feedbackTimer; interval: 1800; onTriggered: page.feedbackText = "" }
    ParallelAnimation {
        id: enterView
        NumberAnimation { target: main; property: "opacity"; from: 0; to: 1; duration: StudyStyle.normal; easing.type: Easing.OutCubic }
        NumberAnimation { target: main; property: "enterOffset"; from: 4; to: 0; duration: StudyStyle.normal; easing.type: Easing.OutCubic }
    }

    Item {
        id: main
        property real enterOffset: 0
        objectName: "studyMainArea"
        x: page.studying ? 32 + (page.width - page.taskRailWidth - 96 - width) / 2 : (parent.width - width) / 2
        y: 24 + enterOffset
        width: Math.min(720, page.width - (page.studying ? page.taskRailWidth + 96 : 64))
        height: page.height - 48

        Item {
            id: preparationView
            objectName: "preparationView"
            anchors.fill: parent
            visible: page.preparation
            StudyText { y: 8; anchors.horizontalCenter: parent.horizontalCenter; text: "학습 준비"; font.pixelSize: 24; font.weight: Font.DemiBold }
            Rectangle {
                id: modeSelector
                objectName: "studyModeSelector"
                y: 64; width: Math.min(480, parent.width - 32); x: (parent.width - width) / 2; height: 48; radius: 8; color: "#EDF1F1"
                Rectangle {
                    objectName: "studyModeIndicator"
                    x: 4 + (page.controller.pomodoroMode ? (modeSelector.width - 4) / 2 : 0)
                    y: 4; width: (modeSelector.width - 12) / 2; height: 40
                    radius: 6; color: "white"; border.color: StudyStyle.line
                    Behavior on x { NumberAnimation { duration: StudyStyle.normal; easing.type: Easing.OutCubic } }
                }
                Row {
                    anchors.fill: parent; anchors.margins: 4; spacing: 4
                    Repeater {
                        model: ["일반 학습", "뽀모도로"]
                        delegate: StudyButton {
                            required property string modelData
                            required property int index
                            objectName: index === 0 ? "chooseGeneral" : "choosePomodoro"
                            width: (modeSelector.width - 12) / 2; height: 40; text: modelData
                            tone: "quiet"
                            enabled: !page.controller.sessionRunning
                            background: Rectangle {
                                radius: 6
                                color: parent.down ? "#DDEAE6" : parent.hovered ? "#0A137B76" : "transparent"
                                border.width: parent.visualFocus ? 2 : 0
                                border.color: StudyStyle.accent
                            }
                            onClicked: page.controller.pomodoroMode = index === 1
                        }
                    }
                }
            }
            Item {
                id: settings
                objectName: "studyPomodoroSettings"
                visible: page.controller.pomodoroMode
                x: (parent.width - width) / 2; y: 140; width: Math.min(560, parent.width - 32); height: 252
                enabled: !page.controller.sessionRunning
                Grid {
                    columns: 2; columnSpacing: 24; rowSpacing: 12
                    StudyNumberInput { id: focusInput; objectName: "focusMinutes"; width: (settings.width - 24) / 2; label: "학습 구간 · 분"; value: page.controller.focusMinutes; onValueEdited: function(value) { page.controller.focusMinutes = value } }
                    StudyNumberInput { id: breakInput; objectName: "breakMinutes"; width: (settings.width - 24) / 2; label: "짧은 휴식 · 분"; value: page.controller.breakMinutes; onValueEdited: function(value) { page.controller.breakMinutes = value } }
                    StudyNumberInput { id: roundsInput; objectName: "rounds"; width: (settings.width - 24) / 2; label: "반복 · 회"; maximum: 12; value: page.controller.targetRounds; onValueEdited: function(value) { page.controller.targetRounds = value } }
                    StudyNumberInput { id: longInput; objectName: "longBreakMinutes"; width: (settings.width - 24) / 2; label: "긴 휴식 · 분"; value: page.controller.longBreakMinutes; onValueEdited: function(value) { page.controller.longBreakMinutes = value } }
                }
                Row {
                    y: 186; spacing: 24
                    StudySwitch { objectName: "autoStartBreakSwitch"; text: "휴식 자동 시작"; checked: page.controller.autoStartBreak; onToggled: page.controller.autoStartBreak = checked }
                    StudySwitch { objectName: "autoStartNextSwitch"; text: "다음 학습 자동 시작"; checked: page.controller.autoStartNext; onToggled: page.controller.autoStartNext = checked }
                }
                StudyText { y: 238; visible: !focusInput.invalid && !breakInput.invalid && !roundsInput.invalid && !longInput.invalid; text: "학습 " + (page.controller.focusMinutes * page.controller.targetRounds) + "분 · 휴식 " + (page.controller.breakMinutes * (page.controller.targetRounds - 1) + page.controller.longBreakMinutes) + "분"; font.pixelSize: 14; color: StudyStyle.muted }
            }
            StudyButton { objectName: "preparationTaskPicker"; y: page.controller.pomodoroMode ? 410 : 214; width: Math.min(400, parent.width); anchors.horizontalCenter: parent.horizontalCenter; tone: "quiet"; symbol: "list-checks"; text: page.controller.currentTaskAvailable ? page.controller.currentTask : "할 일 선택"; onClicked: page.openTools(0) }
            StudyButton { objectName: "calibrationShortcut"; visible: page.feedbackText === ""; anchors.horizontalCenter: parent.horizontalCenter; y: parent.height - 98; height: 36; tone: "quiet"; symbol: page.measurementReady ? "check" : "circle-alert"; text: page.readinessText; onClicked: page.controller.currentTabIndex = 1 }
        }

        Item {
            id: active
            objectName: "activeStudyView"
            property string viewState: page.controller.studyViewState
            anchors.fill: parent
            visible: page.studying
            Item {
                objectName: "studyStatusStrip"
                anchors.horizontalCenter: parent.horizontalCenter; y: 8
                width: statusLabel.implicitWidth + 18; height: 22
                Rectangle { width: 7; height: 7; radius: 3.5; color: page.controller.measurementColor(); anchors.verticalCenter: parent.verticalCenter }
                StudyText { id: statusLabel; objectName: "studyMeasurementStatusLabel"; x: 18; text: page.status; font.pixelSize: 14; font.weight: Font.Medium; color: page.controller.measurementColor() }
            }
            Item {
                y: 62; width: Math.min(460, parent.width - 24); height: 44; x: (parent.width - width) / 2
                StudyButton {
                    objectName: "currentStudyTaskLabel"; x: 0; width: parent.width - 104; tone: "quiet"
                    text: page.controller.currentTaskAvailable ? page.controller.currentTask : page.tasks.length === 0 ? "오늘 계획 없음" : page.controller.currentTask.indexOf("완료") >= 0 ? "모든 목표 완료" : page.controller.currentTask.indexOf("보류") >= 0 ? "보류된 할 일만 남음" : "할 일 선택"
                    contentItem: StudyText { text: parent.text; font.pixelSize: 22; font.weight: Font.Medium; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                    onClicked: page.openTools(0)
                }
                StudyButton { objectName: "completeCurrentTask"; x: parent.width - 96; width: 44; tone: "quiet"; symbol: "check"; hint: "현재 할 일 완료"; enabled: page.controller.currentTaskAvailable; onClicked: page.cycleTask(page.controller.currentTaskId) }
                StudyButton { objectName: "nextStudyTask"; x: parent.width - 48; width: 44; tone: "quiet"; symbol: "chevron-right"; hint: "다음 할 일 선택"; onClicked: page.nextTask() }
            }
            Row {
                visible: page.controller.recommendedTaskId !== -1 && page.controller.recommendedTaskId !== page.controller.currentTaskId
                y: 110; anchors.horizontalCenter: parent.horizontalCenter; spacing: 8
                StudyText { anchors.verticalCenter: parent.verticalCenter; text: "계획 · " + page.controller.recommendedTaskTitle; font.pixelSize: 14; color: StudyStyle.muted; width: Math.min(270, implicitWidth); elide: Text.ElideRight }
                StudyButton { objectName: "selectRecommendedTaskButton"; height: 28; text: "선택"; tone: "quiet"; onClicked: page.controller.chooseStudyTask(page.controller.recommendedTaskId, page.controller.recommendedTaskTitle, page.controller.recommendedTaskSchedule) }
            }
            StudyText { visible: !page.controller.pomodoroMode; y: 170; anchors.horizontalCenter: parent.horizontalCenter; text: "오늘 학습"; color: StudyStyle.muted }
            StudyText { objectName: "todayStudyTimeValue"; visible: !page.controller.pomodoroMode; y: 200; anchors.horizontalCenter: parent.horizontalCenter; text: page.controller.durationText(page.controller.todayStudySeconds, true); font.pixelSize: 80; font.weight: Font.Medium }
            Row {
                visible: !page.controller.pomodoroMode; y: 308; anchors.horizontalCenter: parent.horizontalCenter; spacing: 12
                StudyText { text: "집중"; color: StudyStyle.muted; anchors.verticalCenter: parent.verticalCenter }
                StudyText { objectName: "todayFocusTimeValue"; text: page.controller.durationText(page.controller.todayFocusSeconds, true); font.pixelSize: 24; font.weight: Font.Medium }
            }
            PomodoroRing {
                id: studyRing
                visible: page.controller.pomodoroMode
                x: (parent.width - width) / 2; y: 134; width: 268; height: 268
                progress: page.measurement ? page.measurement.pomodoroProgress : 1 - page.controller.pomodoroSeconds / Math.max(1, page.controller.focusMinutes * 60)
                progressColor: StudyStyle.accent
                timeText: page.controller.durationText(page.controller.pomodoroSeconds, false)
                phaseText: page.waiting ? "다음 학습 대기" : "학습 남음"
                roundText: Math.min(page.controller.completedRounds + 1, page.controller.targetRounds) + " / " + page.controller.targetRounds + "회"
                textColor: StudyStyle.ink; mutedColor: StudyStyle.muted; trackColor: "#E6ECEE"; typeface: StudyStyle.family
                lineWidth: 6; timePixelSize: 64; timeWeight: Font.Medium
                remainingArc: true
            }
            Row {
                objectName: "pomodoroDailyTotals"
                visible: page.controller.pomodoroMode; y: 420; height: 30; anchors.horizontalCenter: parent.horizontalCenter; spacing: 28
                Row { spacing: 8; height: 30; StudyText { text: "오늘 학습"; font.pixelSize: 14; color: StudyStyle.muted; anchors.verticalCenter: parent.verticalCenter } StudyText { text: page.controller.durationText(page.controller.todayStudySeconds, true); font.pixelSize: 20; font.weight: Font.Medium; anchors.verticalCenter: parent.verticalCenter } }
                Row { spacing: 8; height: 30; StudyText { text: "집중"; font.pixelSize: 14; color: StudyStyle.muted; anchors.verticalCenter: parent.verticalCenter } StudyText { text: page.controller.durationText(page.controller.todayFocusSeconds, true); font.pixelSize: 20; font.weight: Font.Medium; anchors.verticalCenter: parent.verticalCenter } }
            }
            Row {
                objectName: "currentSessionTime"
                y: page.controller.pomodoroMode ? 462 : 364
                anchors.horizontalCenter: parent.horizontalCenter; spacing: 8
                StudyText { text: "이번 학습"; font.pixelSize: 14; color: StudyStyle.muted }
                StudyText { objectName: "currentSessionTimeValue"; text: page.controller.durationText(page.controller.elapsedSeconds, true); font.pixelSize: 14; color: StudyStyle.muted }
            }
        }

        Item {
            objectName: "breakView"
            anchors.fill: parent; visible: page.resting
            StudyText { y: 32; anchors.horizontalCenter: parent.horizontalCenter; text: page.waiting ? "다음 단계 대기" : page.measurement ? page.measurement.pomodoroPhase === "paused" && page.controller.pomodoroMode ? "일시정지" : "휴식 중" : "휴식 중"; font.pixelSize: 24; font.weight: Font.DemiBold }
            PomodoroRing {
                objectName: "breakRing"
                timeObjectName: "studyBreakRemainingValue"
                x: (parent.width - width) / 2; y: 120; width: 240; height: 240
                timeText: page.controller.durationText(page.measurement ? page.measurement.breakRemainingSeconds : page.controller.breakMinutes * 60, false)
                phaseText: "휴식 남음"; roundText: ""
                progress: page.measurement && page.controller.pomodoroMode && page.measurement.pomodoroPhase !== "paused" ? page.measurement.pomodoroProgress : 0
                progressColor: "#8E9AA3"; textColor: StudyStyle.ink; mutedColor: StudyStyle.muted; typeface: StudyStyle.family; lineWidth: 6; timePixelSize: 48; timeWeight: Font.Medium
            }
            StudyText { objectName: "studyBreakStatus"; y: 392; anchors.horizontalCenter: parent.horizontalCenter; text: page.waiting ? "다음 단계 대기" : page.controller.pomodoroMode && page.controller.autoStartNext && page.measurement && page.measurement.pomodoroPhase !== "paused" ? "자동 재개 켜짐" : "재개 대기"; color: StudyStyle.muted; font.pixelSize: 14 }
        }

        Item {
            objectName: "resultView"
            anchors.fill: parent; visible: page.result
            StudyText { objectName: "sessionStatusLabel"; text: "학습 종료"; font.pixelSize: 24; font.weight: Font.DemiBold }
            StudyText { y: 110; text: "이번 학습"; font.pixelSize: 14; color: StudyStyle.muted }
            StudyText { objectName: "studyTimeValue"; y: 138; text: page.controller.durationText(page.controller.elapsedSeconds, true); font.pixelSize: 56; font.weight: Font.Medium }
            StudyText { x: parent.width / 2 + 12; y: 110; text: "집중으로 측정"; font.pixelSize: 14; color: StudyStyle.muted }
            StudyText { objectName: "studyFocusTimeValue"; x: parent.width / 2 + 12; y: 146; text: page.controller.durationText(page.measurement ? page.measurement.durations.focus || 0 : 0, true); font.pixelSize: 44; font.weight: Font.Medium }
            Rectangle { y: 242; width: parent.width; height: 1; color: StudyStyle.line }
            StudyText { y: 268; text: "휴식"; font.pixelSize: 14; color: StudyStyle.muted }
            StudyText { y: 296; text: page.controller.durationText(page.measurement ? page.measurement.durations.break || 0 : 0, true); font.pixelSize: 28; font.weight: Font.Medium }
            StudyText { x: parent.width / 2 + 12; y: 268; text: "측정 가능 시간"; font.pixelSize: 14; color: StudyStyle.muted }
            StudyText { x: parent.width / 2 + 12; y: 296; text: page.measurement && page.controller.elapsedSeconds > 0 ? page.measurement.coveragePercent + "%" : "-"; font.pixelSize: 28; font.weight: Font.Medium }
        }

        StudyText { objectName: "studyFeedback"; y: parent.height - 76; width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; text: page.feedbackText; font.pixelSize: 14; color: page.feedbackIsError ? StudyStyle.danger : StudyStyle.accent; visible: page.feedbackText !== "" }
        Row {
            objectName: "studyActions"
            layoutDirection: Qt.RightToLeft
            anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom; spacing: 12
            StudyButton { objectName: "reviewStudyRecord"; visible: page.result; text: "기록 정리"; symbol: "list-checks"; onClicked: { if (page.backend) { page.backend.refreshToday(); page.backend.selectRecordsDate(page.backend.todayStudyDateIso) }; page.controller.currentTabIndex = 3; page.controller.openStudyRecords() } }
            StudyButton { objectName: "studyEndAction"; width: 122; visible: page.controller.sessionRunning && !page.preparation; text: "학습 종료"; symbol: "square"; onClicked: page.controller.endStudySession() }
            StudyButton { objectName: "studyPrimaryAction"; width: page.preparation ? 200 : page.result ? 128 : 160; height: page.preparation ? 48 : 44; tone: page.preparation || page.resting || page.result ? "primary" : "secondary"; text: page.preparation ? page.controller.sessionRunning ? "학습으로 돌아가기" : "학습 시작" : page.result ? "새 학습" : page.measurement ? page.measurement.breakActionText : page.resting ? "학습 재개" : "휴식"; symbol: page.preparation || page.resting || page.result ? "play" : "coffee"; onClicked: page.primaryAction() }
        }
    }

    Item {
        id: compactTasks
        objectName: "compactTasks"
        x: parent.width - width - 32; y: 40; width: page.taskRailWidth
        height: Math.max(100, 40 + Math.min(5, page.tasks.length) * 64 + 48)
        visible: page.studying && !tools.visible
        Rectangle { x: -16; width: 1; height: parent.height; color: StudyStyle.line }
        StudyText { text: "오늘 할 일"; font.pixelSize: 15; font.weight: Font.DemiBold }
        StudyText { anchors.right: parent.right; text: page.tasks.length; font.pixelSize: 14; color: StudyStyle.muted }
        StudyText { y: 46; visible: page.tasks.length === 0; text: "계획 없음"; font.pixelSize: 14; color: StudyStyle.muted }
        ListView {
            id: compactTaskList
            y: 36; width: parent.width; height: Math.min(5, page.tasks.length) * 64
            model: page.tasks; clip: true; interactive: false
            delegate: Item {
                id: compactRow
                required property var modelData
                required property int index
                readonly property bool selected: page.controller.currentTaskId === modelData.taskId
                function focusStatus() { stateToggle.forceActiveFocus(Qt.TabFocusReason) }
                width: ListView.view.width; height: 64
                Rectangle {
                    anchors.fill: parent; anchors.bottomMargin: 4; radius: 6
                    color: compactRow.selected ? StudyStyle.wash : "transparent"
                    Rectangle { width: 2; height: 24; radius: 1; anchors.verticalCenter: parent.verticalCenter; color: StudyStyle.accent; visible: compactRow.selected }
                }
                StudyButton {
                    id: stateToggle
                    objectName: "compactTaskState" + compactRow.index
                    x: 4; y: 10; width: 36; height: 36; tone: "quiet"
                    symbol: compactRow.modelData.taskState === 1 ? "check" : compactRow.modelData.taskState === 2 ? "pause" : "circle"
                    hint: ["완료로 변경", "보류로 변경", "미완료로 변경"][compactRow.modelData.taskState]
                    onClicked: page.cycleTask(compactRow.modelData.taskId, visualFocus ? compactRow.index : -1)
                }
                Button {
                    id: compactTask
                    objectName: "compactTask" + compactRow.index
                    x: 44; width: parent.width - 48; height: 60
                    hoverEnabled: true; enabled: compactRow.modelData.taskState === 0
                    Accessible.name: compactRow.modelData.title
                    ToolTip.visible: (hovered || visualFocus) && compactTitle.truncated; ToolTip.text: compactRow.modelData.title; ToolTip.delay: 500
                    background: Rectangle {
                        radius: 4; color: compactTask.down ? "#DCEBE5" : compactTask.hovered ? "#EFF3F1" : "transparent"
                        border.width: compactTask.visualFocus ? 2 : 0; border.color: StudyStyle.accent
                    }
                    contentItem: Item {
                        StudyText {
                            id: compactTitle
                            y: compactRow.modelData.detail ? 9 : (parent.height - height) / 2
                            width: parent.width; text: compactRow.modelData.title
                            font.pixelSize: 14; font.weight: compactRow.selected ? Font.Medium : Font.Normal
                            font.strikeout: compactRow.modelData.taskState === 1
                            color: compactRow.modelData.taskState === 1 ? StudyStyle.muted : StudyStyle.ink
                            elide: Text.ElideRight
                        }
                        StudyText { y: 32; width: parent.width; visible: compactRow.modelData.detail !== ""; text: compactRow.modelData.detail; font.pixelSize: 13; color: StudyStyle.muted; elide: Text.ElideRight }
                    }
                    onClicked: page.controller.toggleStudyTask(compactRow.modelData.taskId, compactRow.modelData.title, compactRow.modelData.detail)
                }
            }
        }
        StudyButton { objectName: "openAllStudyTasks"; visible: page.tasks.length > 0; anchors.bottom: parent.bottom; height: 36; tone: "quiet"; text: "전체 할 일"; symbol: "chevron-right"; onClicked: page.openTools(0) }
        StudyButton { visible: page.tasks.length === 0; anchors.bottom: parent.bottom; height: 36; tone: "quiet"; text: "계획 추가"; symbol: "plus"; onClicked: page.controller.currentTabIndex = 2 }
    }

    Drawer {
        id: tools
        objectName: "studyTools"
        edge: Qt.RightEdge; modal: false; dim: false
        width: page.controller.width < 1180 ? 300 : 344; y: 64; height: page.controller.height - 144
        padding: 0
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        enter: Transition { NumberAnimation { duration: StudyStyle.normal; easing.type: Easing.OutCubic } }
        exit: Transition { NumberAnimation { duration: StudyStyle.fast; easing.type: Easing.OutCubic } }
        background: Rectangle { color: "white"; Rectangle { width: 1; height: parent.height; color: StudyStyle.line } }
        contentItem: Item {
            StudyText { x: 20; y: 20; text: "학습 도구"; font.pixelSize: 18; font.weight: Font.DemiBold }
            StudyButton { objectName: "closeStudyTools"; x: parent.width - 56; y: 8; width: 40; height: 40; tone: "quiet"; symbol: "x"; hint: "학습 도구 닫기"; onClicked: tools.close() }
            TabBar {
                id: toolTabs
                x: 20; y: 62; width: parent.width - 40; height: 42
                background: Item {}
                Repeater {
                    model: ["할 일", "타임라인", "카메라"]
                    delegate: TabButton {
                        required property string modelData
                        required property int index
                        objectName: ["toolsTasks", "toolsTimeline", "toolsCamera"][index]
                        width: (tools.width - 40) / 3; height: 42; text: modelData
                        contentItem: StudyText { text: parent.text; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.pixelSize: 14; color: parent.checked ? StudyStyle.ink : StudyStyle.muted }
                        background: Rectangle { color: "transparent"; border.width: parent.activeFocus ? 2 : 0; border.color: StudyStyle.accent; Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 2; color: StudyStyle.accent; visible: parent.parent.checked } }
                    }
                }
            }
            Item {
                x: 20; y: 126; width: parent.width - 40; height: parent.height - 142
                Item {
                    anchors.fill: parent; visible: toolTabs.currentIndex === 0
                    ListView {
                        id: fullTasks
                        width: parent.width; height: parent.height - 54; spacing: 8; model: page.tasks; clip: true
                        ScrollIndicator.vertical: ScrollIndicator {}
                        delegate: Rectangle {
                            id: taskRow
                            required property var modelData
                            objectName: "learningTaskRow" + modelData.taskId
                            width: fullTasks.width; height: 80; radius: 6
                            color: page.controller.currentTaskId === modelData.taskId ? StudyStyle.wash : "white"
                            border.color: page.controller.currentTaskId === modelData.taskId ? "#B9DED6" : StudyStyle.line
                            StudyButton { objectName: "learningTaskStateButton" + taskRow.modelData.taskId; x: 8; y: 20; width: 40; tone: "quiet"; symbol: taskRow.modelData.taskState === 1 ? "check" : taskRow.modelData.taskState === 2 ? "pause" : "circle"; hint: ["완료로 변경", "보류로 변경", "미완료로 변경"][taskRow.modelData.taskState]; onClicked: page.cycleTask(taskRow.modelData.taskId) }
                            StudyText { x: 58; y: 16; width: parent.width - 70; text: taskRow.modelData.title; font.pixelSize: 16; font.weight: page.controller.currentTaskId === taskRow.modelData.taskId ? Font.Medium : Font.Normal; color: taskRow.modelData.taskState === 1 ? StudyStyle.muted : StudyStyle.ink; font.strikeout: taskRow.modelData.taskState === 1; elide: Text.ElideRight }
                            StudyText { x: 58; y: 45; width: parent.width - 70; text: (taskRow.modelData.taskState === 2 ? "보류 · " : "") + taskRow.modelData.detail; font.pixelSize: 14; color: StudyStyle.muted; elide: Text.ElideRight }
                            MouseArea { objectName: "learningTaskSelect" + taskRow.modelData.taskId; x: 54; width: parent.width - 54; height: parent.height; cursorShape: Qt.PointingHandCursor; onClicked: if (taskRow.modelData.taskState === 0) page.controller.toggleStudyTask(taskRow.modelData.taskId, taskRow.modelData.title, taskRow.modelData.detail) }
                        }
                    }
                    StudyButton { objectName: "editTodayPlanButton"; anchors.bottom: parent.bottom; width: parent.width; text: "오늘 계획 편집"; symbol: "calendar"; onClicked: { tools.close(); if (page.backend) page.backend.selectPlannerDate(Qt.formatDate(page.controller.currentDateTime, "yyyy-MM-dd")); page.controller.currentTabIndex = 2 } }
                }
                StudyTimeline {
                    visible: toolTabs.currentIndex === 1; anchors.fill: parent
                    currentHour: page.controller.currentDateTime.getHours(); currentMinute: page.controller.currentDateTime.getMinutes()
                    hourlyData: page.backend && tools.visible && toolTabs.currentIndex === 1 ? page.backend.learningHourlyData(page.measurement ? page.measurement.liveSessionData : {}) : []
                    plannerTasks: page.tasks
                }
                Item {
                    objectName: "cameraPanel"
                    anchors.fill: parent; visible: toolTabs.currentIndex === 2
                    Rectangle {
                        objectName: "studyCameraPreview"
                        width: parent.width; height: width * 9 / 16; radius: 8; clip: true
                        color: page.controller.cameraVisible ? "#0D1726" : "#EFF2F3"
                        Image { anchors.fill: parent; visible: page.controller.cameraVisible && page.measurement && page.measurement.cameraConnected; source: tools.visible && toolTabs.currentIndex === 2 && visible && page.measurement ? page.measurement.frameSource : ""; fillMode: Image.PreserveAspectFit; cache: false }
                        StudyText { anchors.centerIn: parent; width: parent.width - 24; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; visible: !(page.controller.cameraVisible && page.measurement && page.measurement.cameraConnected); text: !page.controller.cameraVisible ? "화면 숨김" : page.measurement ? page.measurement.cameraMessage : "측정 미연결"; color: StudyStyle.muted; font.pixelSize: 14 }
                        StudyButton { objectName: "studyCameraToggle"; anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 8; width: 40; height: 40; tone: "secondary"; symbol: page.controller.cameraVisible ? "eye-off" : "camera"; hint: page.controller.cameraVisible ? "카메라 화면 숨기기" : "카메라 화면 표시"; onClicked: { page.controller.cameraVisible = !page.controller.cameraVisible; if (page.backend) page.backend.saveSettings({camera_preview_hidden: !page.controller.cameraVisible}) } }
                    }
                    StudyText { y: parent.width * 9 / 16 + 24; width: parent.width; text: page.status; font.pixelSize: 14; color: page.controller.measurementColor(); wrapMode: Text.WordWrap }
                    StudyText { y: parent.width * 9 / 16 + 62; width: parent.width; text: page.measurement ? page.measurement.statusDetail : ""; font.pixelSize: 14; color: StudyStyle.muted; wrapMode: Text.WordWrap }
                    StudyButton { anchors.bottom: parent.bottom; width: parent.width; text: "측정 설정"; symbol: "settings-2"; onClicked: { tools.close(); page.controller.currentTabIndex = 1 } }
                }
            }
        }
    }
}
