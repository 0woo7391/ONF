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

    property bool pomodoroMode: true
    property bool sessionRunning: false
    property bool sessionPaused: false
    property bool cameraVisible: true
    property int elapsedSeconds: 0
    property int todayStudySeconds: 0
    property int pomodoroSeconds: focusMinutes * 60
    property int focusMinutes: 25
    property int breakMinutes: 5
    property int targetRounds: 4
    property int completedRounds: 0
    property string currentTask: "영어 독해 지문 2개"
    property string currentTaskSchedule: "시간 미지정"
    property bool currentTaskAutoSelected: false
    property int lastTaskCheckMinute: -1
    property date currentDateTime: new Date()
    property int currentTabIndex: 0
    property var backendObject: null

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
        elapsedSeconds = 0
        pomodoroSeconds = focusMinutes * 60
        completedRounds = 0
        sessionRunning = true
        sessionPaused = false
    }

    function endStudySession() {
        sessionRunning = false
        sessionPaused = false
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
        var wasAutoSelected = currentTaskAutoSelected
        var nowMinute = currentDateTime.getHours() * 60 + currentDateTime.getMinutes()
        var source = backendObject ? backendObject.plannerTasks : todayTasks
        var bestTask = null
        var bestStart = -1
        var sourceCount = backendObject ? source.length : source.count
        for (var i = 0; i < sourceCount; i++) {
            var task = backendObject ? source[i] : source.get(i)
            if (task.done || task.taskState === 1) continue
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
        if (bestTask) {
            currentTask = bestTask.title
            currentTaskSchedule = bestTask.detail || (bestTask.start + " - " + bestTask.end)
            currentTaskAutoSelected = true
        } else {
            currentTaskAutoSelected = false
            if (wasAutoSelected) {
                currentTask = "선택된 할 일이 없습니다"
                currentTaskSchedule = "오늘 계획에서 선택하세요"
            }
        }
    }

    Connections {
        target: window.backendObject
        enabled: window.backendObject !== null
        ignoreUnknownSignals: true
        function onDataChanged() { window.refreshScheduledTask() }
    }

    Timer {
        interval: 1000
        repeat: true
        running: true
        onTriggered: {
            window.currentDateTime = new Date()
            var minute = window.currentDateTime.getMinutes()
            if (minute !== window.lastTaskCheckMinute) {
                window.lastTaskCheckMinute = minute
                window.refreshScheduledTask()
            }
            if (window.sessionRunning && !window.sessionPaused) {
                window.elapsedSeconds += 1
                window.todayStudySeconds += 1
                if (window.pomodoroMode && window.pomodoroSeconds > 0)
                    window.pomodoroSeconds -= 1
            }
        }
    }

    ListModel {
        id: todayTasks
        ListElement { taskId: -1; taskState: 0; title: "영어 독해 지문 2개"; start: "09:00"; end: "09:45"; duration: "45분"; detail: "09:00 - 09:45"; done: false }
        ListElement { taskId: -2; taskState: 0; title: "수학 오답노트 정리"; start: ""; end: ""; duration: ""; detail: "시간 미지정"; done: false }
        ListElement { taskId: -3; taskState: 1; title: "한국사 4강 복습"; start: ""; end: ""; duration: "30분"; detail: "예상 30분"; done: true }
        ListElement { taskId: -4; taskState: 0; title: "과학 개념 문제 20개"; start: "20:00"; end: "21:00"; duration: "60분"; detail: "20:00 - 21:00"; done: false }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 62
            radius: Theme.radius
            color: Theme.surface
            border.color: Theme.border

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 16
                spacing: 5

                Repeater {
                    model: ["학습", "플래너", "기록", "설정"]
                    delegate: Button {
                        id: navButton
                        required property int index
                        required property string modelData
                        text: modelData
                        implicitWidth: 76
                        implicitHeight: 40
                        flat: true
                        onClicked: window.currentTabIndex = navButton.index
                        contentItem: Text {
                            text: navButton.text
                            color: window.currentTabIndex === navButton.index ? Theme.primary : Theme.muted
                            font.pixelSize: 14
                            font.weight: window.currentTabIndex === navButton.index ? Font.DemiBold : Font.Medium
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        background: Rectangle {
                            radius: Theme.radius
                            color: window.currentTabIndex === navButton.index ? Theme.primarySoft : navButton.hovered ? "#F2F5F8" : "transparent"
                            Behavior on color { ColorAnimation { duration: Theme.fast } }
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                Column {
                    spacing: 1
                    Text {
                        anchors.right: parent.right
                        text: Qt.formatTime(window.currentDateTime, "AP h:mm")
                        color: Theme.text
                        font.pixelSize: 20
                        font.weight: Font.DemiBold
                    }
                    Text {
                        anchors.right: parent.right
                        text: Qt.formatDate(window.currentDateTime, "yyyy년 M월 d일 dddd")
                        color: Theme.muted
                        font.pixelSize: 11
                    }
                }
            }
        }

        RowLayout {
            visible: window.currentTabIndex === 0
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            Rectangle {
                Layout.preferredWidth: Math.max(230, window.width * 0.225)
                Layout.fillHeight: true
                radius: Theme.radius
                color: Theme.surface
                border.color: Theme.border

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "오늘 할 일"; color: Theme.text; font.pixelSize: 17; font.weight: Font.Bold }
                        Item { Layout.fillWidth: true }
                        Rectangle {
                            Layout.preferredWidth: taskCount.implicitWidth + 16
                            Layout.preferredHeight: 28
                            radius: 14
                            color: Theme.primarySoft
                            Text { id: taskCount; anchors.centerIn: parent; text: (window.backendObject ? window.backendObject.plannerTasks.length : 3) + "개 계획"; color: Theme.primary; font.pixelSize: 11; font.weight: Font.DemiBold }
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        text: "선택한 항목이 지금 할 일로 표시됩니다."
                        color: Theme.muted
                        font.pixelSize: 10
                    }

                    ListView {
                        id: taskList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 7
                        clip: true
                        model: window.backendObject ? window.backendObject.plannerTasks : todayTasks
                        delegate: Rectangle {
                            id: taskDelegate
                            required property string title
                            required property string detail
                            required property bool done
                            required property int index
                            required property int taskId
                            width: taskList.width
                            height: 68
                            radius: Theme.radius
                            color: window.currentTask === title ? Theme.primarySoft : taskMouse.containsMouse ? Theme.surfaceSoft : Theme.surface
                            border.color: window.currentTask === title ? "#BFD5FF" : Theme.border
                            border.width: 1

                            RowLayout {
                                z: 1
                                anchors.fill: parent
                                anchors.leftMargin: 11
                                anchors.rightMargin: 10
                                spacing: 9

                                Button {
                                    id: doneButton
                                    Layout.preferredWidth: 28
                                    Layout.preferredHeight: 28
                                    text: taskDelegate.done ? "✓" : ""
                                    onClicked: {
                                        if (window.backendObject)
                                            window.backendObject.cyclePlannerTask(taskDelegate.taskId)
                                        else
                                            todayTasks.setProperty(taskDelegate.index, "done", !taskDelegate.done)
                                    }
                                    background: Rectangle {
                                        radius: 6
                                        color: taskDelegate.done ? Theme.success : Theme.surface
                                        border.color: taskDelegate.done ? Theme.success : "#B8C0CB"
                                    }
                                    contentItem: Text { text: doneButton.text; color: "white"; font.pixelSize: 15; font.weight: Font.Bold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 3
                                    Text {
                                        Layout.fillWidth: true
                                        text: taskDelegate.title
                                        color: taskDelegate.done ? "#98A1AD" : Theme.text
                                        font.pixelSize: 13
                                        font.weight: Font.DemiBold
                                        elide: Text.ElideRight
                                        font.strikeout: taskDelegate.done
                                    }
                                    Text { text: taskDelegate.detail; color: Theme.muted; font.pixelSize: 11 }
                                }
                            }

                            MouseArea {
                                id: taskMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: {
                                    if (!taskDelegate.done) {
                                        window.currentTask = taskDelegate.title
                                        window.currentTaskSchedule = taskDelegate.detail
                                        window.currentTaskAutoSelected = false
                                        feedback.showMessage("지금 할 일을 변경했습니다.")
                                    }
                                }
                            }
                        }
                    }

                    ActionButton {
                        Layout.fillWidth: true
                        text: "오늘 계획 편집"
                        onClicked: feedback.showMessage("플래너로 이동합니다.")
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumWidth: 390
                radius: Theme.radius
                color: Theme.surface
                border.color: Theme.border

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 22
                    spacing: 12

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 78
                        radius: Theme.radius
                        color: Theme.primarySoft
                        border.color: "#BFD5FF"
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            anchors.rightMargin: 14
                            spacing: 11
                            Rectangle { Layout.preferredWidth: 5; Layout.fillHeight: true; Layout.topMargin: 13; Layout.bottomMargin: 13; radius: 3; color: Theme.primary }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 3
                                Row {
                                    spacing: 7
                                    Text { text: "지금 할 일"; color: Theme.primary; font.pixelSize: 11; font.weight: Font.Bold }
                                    Text { text: window.currentTaskAutoSelected ? "현재 시각에 맞춰 자동 선택" : "직접 선택"; color: Theme.muted; font.pixelSize: 9 }
                                }
                                Text { Layout.fillWidth: true; text: window.currentTask; color: Theme.text; font.pixelSize: 24; font.weight: Font.Bold; elide: Text.ElideRight }
                            }
                            Text { text: window.currentTaskSchedule; color: Theme.primary; font.pixelSize: 11; font.weight: Font.DemiBold }
                        }
                    }

                    Row {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: 4
                        Repeater {
                            model: ["자유 학습", "뽀모도로"]
                            delegate: Button {
                                id: modeButton
                                required property string modelData
                                width: 112
                                height: 38
                                text: modelData
                                enabled: !window.sessionRunning
                                onClicked: {
                                    window.pomodoroMode = modelData === "뽀모도로"
                                    window.pomodoroSeconds = window.focusMinutes * 60
                                }
                                contentItem: Text {
                                    text: modeButton.text
                                    color: (window.pomodoroMode === (modeButton.text === "뽀모도로")) ? Theme.primary : Theme.muted
                                    font.pixelSize: 13
                                    font.weight: Font.DemiBold
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                                background: Rectangle {
                                    radius: Theme.radius
                                    color: (window.pomodoroMode === (modeButton.text === "뽀모도로")) ? Theme.primarySoft : Theme.surfaceSoft
                                    border.color: (window.pomodoroMode === (modeButton.text === "뽀모도로")) ? "#BFD5FF" : Theme.border
                                }
                            }
                        }
                    }

                    RowLayout {
                        visible: window.pomodoroMode && !window.sessionRunning
                        Layout.alignment: Qt.AlignHCenter
                        spacing: 10
                        Repeater {
                            model: [
                                {label: "집중", suffix: "분", value: window.focusMinutes},
                                {label: "휴식", suffix: "분", value: window.breakMinutes},
                                {label: "반복", suffix: "회", value: window.targetRounds}
                            ]
                            delegate: Column {
                                id: pomodoroSetting
                                required property var modelData
                                spacing: 3
                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: pomodoroSetting.modelData.label; color: Theme.muted; font.pixelSize: 11 }
                                ValueStepper {
                                    width: 98
                                    minimumValue: pomodoroSetting.modelData.label === "반복" ? 1 : 5
                                    maximumValue: pomodoroSetting.modelData.label === "반복" ? 12 : 120
                                    value: pomodoroSetting.modelData.value
                                    suffix: pomodoroSetting.modelData.suffix
                                    onValueChanged: {
                                        if (pomodoroSetting.modelData.label === "집중") {
                                            window.focusMinutes = value
                                            window.pomodoroSeconds = value * 60
                                        } else if (pomodoroSetting.modelData.label === "휴식") {
                                            window.breakMinutes = value
                                        } else {
                                            window.targetRounds = value
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }

                    PomodoroRing {
                        visible: window.pomodoroMode
                        Layout.alignment: Qt.AlignHCenter
                        Layout.preferredWidth: window.width < 1120 ? 214 : 246
                        Layout.preferredHeight: Layout.preferredWidth
                        progress: 1 - window.pomodoroSeconds / Math.max(1, window.focusMinutes * 60)
                        timeText: window.durationText(window.pomodoroSeconds, false)
                        phaseText: "집중 " + (window.completedRounds + 1) + "회차"
                        roundText: window.completedRounds + " / " + window.targetRounds + "회 완료"
                    }

                    Column {
                        visible: !window.pomodoroMode
                        Layout.alignment: Qt.AlignHCenter
                        spacing: 7
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: window.sessionRunning ? "학습 중" : "준비"; color: window.sessionRunning ? Theme.success : Theme.muted; font.pixelSize: 13; font.weight: Font.DemiBold }
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: window.durationText(window.elapsedSeconds, true); color: Theme.text; font.pixelSize: window.width < 1120 ? 58 : 70; font.weight: Font.Bold }
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "오늘 누적 " + window.durationText(window.todayStudySeconds, true); color: Theme.muted; font.pixelSize: 12 }
                    }

                    Item { Layout.fillHeight: true }

                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: 9
                        ActionButton {
                            text: window.sessionRunning ? window.sessionPaused ? "계속하기" : "일시정지" : "학습 시작"
                            tone: "primary"
                            onClicked: {
                                if (!window.sessionRunning) {
                                    window.startStudySession()
                                    feedback.showMessage("학습을 시작했습니다.")
                                } else {
                                    window.sessionPaused = !window.sessionPaused
                                    feedback.showMessage(window.sessionPaused ? "학습을 잠시 멈췄습니다." : "학습을 계속합니다.")
                                }
                            }
                        }
                        ActionButton {
                            text: "휴식"
                            enabled: window.sessionRunning
                            onClicked: {
                                window.sessionPaused = true
                                feedback.showMessage(window.breakMinutes + "분 휴식을 시작했습니다.")
                            }
                        }
                        ActionButton {
                            text: "학습 종료"
                            tone: "danger"
                            enabled: window.sessionRunning
                            onClicked: {
                                window.endStudySession()
                                feedback.showMessage("학습 기록을 저장했습니다.")
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 38
                        radius: Theme.radius
                        color: window.sessionPaused ? Theme.warningSoft : window.sessionRunning ? Theme.successSoft : Theme.surfaceSoft
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            Text {
                                text: window.sessionPaused ? "●  잠시 멈춤" : window.sessionRunning ? "●  집중 측정 중" : "●  시작 전"
                                color: window.sessionPaused ? "#B45309" : window.sessionRunning ? Theme.success : Theme.muted
                                font.pixelSize: 12
                                font.weight: Font.DemiBold
                            }
                            Item { Layout.fillWidth: true }
                            Text { text: window.cameraVisible ? "카메라 분석 연결됨" : "화면 숨김 · 분석 유지"; color: Theme.muted; font.pixelSize: 11 }
                        }
                    }
                }
            }

            Rectangle {
                objectName: "cameraPanel"
                Layout.preferredWidth: Math.max(250, window.width * 0.25)
                Layout.fillHeight: true
                radius: Theme.radius
                color: Theme.surface
                border.color: Theme.border
                Behavior on Layout.preferredWidth { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "카메라"; color: Theme.text; font.pixelSize: 15; font.weight: Font.Bold }
                        Item { Layout.fillWidth: true }
                        Button {
                            id: cameraToggle
                            Layout.preferredWidth: 38
                            Layout.preferredHeight: 34
                            text: window.cameraVisible ? "◉" : "○"
                            ToolTip.visible: hovered
                            ToolTip.text: window.cameraVisible ? "카메라 화면 숨기기" : "카메라 화면 보이기"
                            onClicked: window.cameraVisible = !window.cameraVisible
                            background: Rectangle { radius: Theme.radius; color: cameraToggle.hovered ? Theme.primarySoft : Theme.surfaceSoft; border.color: Theme.border }
                            contentItem: Text { text: cameraToggle.text; color: Theme.primary; font.pixelSize: 15; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: width * 0.72
                        radius: Theme.radius
                        color: window.cameraVisible ? "#0D1726" : Theme.surfaceSoft
                        clip: true
                        Text { anchors.centerIn: parent; text: window.cameraVisible ? "카메라 미리보기" : "화면 숨김\n분석 유지"; color: window.cameraVisible ? "#8190A5" : Theme.muted; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter; lineHeight: 1.35 }
                        Rectangle {
                            visible: window.cameraVisible
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.verticalCenter: parent.verticalCenter
                            width: 28
                            height: 1
                            color: "#8CA0B8"
                        }
                        Rectangle {
                            visible: window.cameraVisible
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.verticalCenter: parent.verticalCenter
                            width: 1
                            height: 28
                            color: "#8CA0B8"
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Text { text: "현재 상태"; color: Theme.muted; font.pixelSize: 11 }
                        Text {
                            text: window.sessionPaused ? "휴식 중" : window.sessionRunning ? "집중 중" : "준비됨"
                            color: window.sessionPaused ? Theme.warning : window.sessionRunning ? Theme.success : Theme.text
                            font.pixelSize: 22
                            font.weight: Font.Bold
                        }
                        Text {
                            Layout.fillWidth: true
                            text: window.sessionPaused ? "휴식 시간은 집중률에서 제외됩니다." : "얼굴과 시선을 안정적으로 확인하고 있습니다."
                            color: Theme.muted
                            font.pixelSize: 11
                            wrapMode: Text.WordWrap
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 178
                        radius: Theme.radius
                        color: Theme.surfaceSoft
                        StudyTimeline {
                            anchors.fill: parent
                            anchors.margins: 10
                            currentHour: window.currentDateTime.getHours()
                            currentMinute: window.currentDateTime.getMinutes()
                        }
                    }
                }
            }
        }

        PlannerPage {
            visible: window.currentTabIndex === 1
            Layout.fillWidth: true
            Layout.fillHeight: true
            backendObject: window.backendObject
            onFeedbackRequested: function(message) { feedback.showMessage(message) }
        }

        RecordsPage {
            visible: window.currentTabIndex === 2
            Layout.fillWidth: true
            Layout.fillHeight: true
            backendObject: window.backendObject
            onFeedbackRequested: function(message) { feedback.showMessage(message) }
        }

        SettingsPage {
            visible: window.currentTabIndex === 3
            Layout.fillWidth: true
            Layout.fillHeight: true
            backendObject: window.backendObject
            onFeedbackRequested: function(message) { feedback.showMessage(message) }
        }
    }

    Rectangle {
        id: feedback
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
            messageText.text = message
            opacity = 1
            scale = 1
            feedbackTimer.restart()
        }
    }

    onBackendObjectChanged: refreshScheduledTask()
}
