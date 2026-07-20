pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "."
import "components"

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
    property int pomodoroSeconds: focusMinutes * 60
    property int focusMinutes: 25
    property int breakMinutes: 5
    property int targetRounds: 4
    property int completedRounds: 0
    property string currentTask: "영어 독해 지문 2개"
    property date currentDateTime: new Date()

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

    Timer {
        interval: 1000
        repeat: true
        running: true
        onTriggered: {
            window.currentDateTime = new Date()
            if (window.sessionRunning && !window.sessionPaused) {
                window.elapsedSeconds += 1
                if (window.pomodoroMode && window.pomodoroSeconds > 0)
                    window.pomodoroSeconds -= 1
            }
        }
    }

    ListModel {
        id: todayTasks
        ListElement { title: "영어 독해 지문 2개"; detail: "예상 45분"; done: false }
        ListElement { title: "수학 오답노트 정리"; detail: "시간 미지정"; done: false }
        ListElement { title: "한국사 4강 복습"; detail: "예상 30분"; done: true }
        ListElement { title: "과학 개념 문제 20개"; detail: "오후 8시 예정"; done: false }
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
                        required property string modelData
                        text: modelData
                        implicitWidth: 76
                        implicitHeight: 40
                        flat: true
                        contentItem: Text {
                            text: navButton.text
                            color: navButton.text === "학습" ? Theme.primary : Theme.muted
                            font.pixelSize: 14
                            font.weight: navButton.text === "학습" ? Font.DemiBold : Font.Medium
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        background: Rectangle {
                            radius: Theme.radius
                            color: navButton.text === "학습" ? Theme.primarySoft : navButton.hovered ? "#F2F5F8" : "transparent"
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
                            Text { id: taskCount; anchors.centerIn: parent; text: "3개 남음"; color: Theme.primary; font.pixelSize: 11; font.weight: Font.DemiBold }
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        text: "공부할 항목을 눌러 지금 할 일로 선택하세요."
                        color: Theme.muted
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                    }

                    ListView {
                        id: taskList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 7
                        clip: true
                        model: todayTasks
                        delegate: Rectangle {
                            id: taskDelegate
                            required property string title
                            required property string detail
                            required property bool done
                            required property int index
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
                                    onClicked: todayTasks.setProperty(taskDelegate.index, "done", !taskDelegate.done)
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

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Text { text: "지금 할 일"; color: Theme.muted; font.pixelSize: 12 }
                        Text {
                            Layout.fillWidth: true
                            text: window.currentTask
                            color: Theme.text
                            font.pixelSize: 23
                            font.weight: Font.Bold
                            elide: Text.ElideRight
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

                    Column {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: 7
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: window.pomodoroMode ? "집중 " + (window.completedRounds + 1) + "회차" : window.sessionRunning ? "학습 중" : "준비"
                            color: window.sessionRunning ? Theme.success : Theme.muted
                            font.pixelSize: 13
                            font.weight: Font.DemiBold
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: window.pomodoroMode ? window.durationText(window.pomodoroSeconds, false) : window.durationText(window.elapsedSeconds, true)
                            color: Theme.text
                            font.pixelSize: window.width < 1120 ? 58 : 70
                            font.weight: Font.Bold
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: window.pomodoroMode ? window.completedRounds + " / " + window.targetRounds + "회 완료" : "오늘 누적 " + window.durationText(window.elapsedSeconds, true)
                            color: Theme.muted
                            font.pixelSize: 12
                        }
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
                                    window.sessionRunning = true
                                    window.sessionPaused = false
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
                                window.sessionRunning = false
                                window.sessionPaused = false
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
                Layout.preferredWidth: window.cameraVisible ? Math.max(250, window.width * 0.25) : 210
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
                        visible: window.cameraVisible
                        Layout.fillWidth: true
                        Layout.preferredHeight: width * 0.72
                        radius: Theme.radius
                        color: "#0D1726"
                        clip: true
                        Text { anchors.centerIn: parent; text: "카메라 미리보기"; color: "#8190A5"; font.pixelSize: 13 }
                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.verticalCenter: parent.verticalCenter
                            width: 28
                            height: 1
                            color: "#8CA0B8"
                        }
                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.verticalCenter: parent.verticalCenter
                            width: 1
                            height: 28
                            color: "#8CA0B8"
                        }
                    }

                    Rectangle {
                        visible: !window.cameraVisible
                        Layout.fillWidth: true
                        Layout.preferredHeight: 74
                        radius: Theme.radius
                        color: Theme.surfaceSoft
                        Text { anchors.centerIn: parent; text: "화면만 숨겼습니다\n집중 분석은 계속됩니다."; color: Theme.muted; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; lineHeight: 1.35 }
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
                        Layout.minimumHeight: 120
                        radius: Theme.radius
                        color: Theme.surfaceSoft
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 7
                            Text { text: "최근 집중 흐름"; color: Theme.text; font.pixelSize: 12; font.weight: Font.DemiBold }
                            FocusBars { Layout.fillWidth: true; Layout.fillHeight: true }
                            Text { text: "빨강 낮음  ·  노랑 보통  ·  초록 높음  ·  회색 휴식"; color: Theme.muted; font.pixelSize: 9 }
                        }
                    }
                }
            }
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
}
