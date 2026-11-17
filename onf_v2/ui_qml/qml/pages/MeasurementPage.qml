pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import ".."
import "../components"

Item {
    id: root
    objectName: "measurementPage"
    property var measurementObject: null
    property bool cameraVisible: true
    property bool writingPreparationVisible: false
    property int writingCountdown: 3
    signal feedbackRequested(string message)

    Connections {
        target: root.measurementObject
        ignoreUnknownSignals: true
        function onScreenValidationFinished() { gazeReport.open() }
    }

    function prepareWritingCalibration() {
        if (!measurementObject)
            return
        if (!measurementObject.cameraConnected) {
            feedbackRequested("카메라가 연결된 뒤 다시 시도하세요.")
            return
        }
        if (!measurementObject.screenReady) {
            feedbackRequested("화면 자세를 먼저 설정하세요.")
            return
        }
        writingCountdown = 3
        writingPreparationVisible = true
        writingCountdownTimer.restart()
    }

    Timer {
        id: writingCountdownTimer
        interval: 1000
        repeat: true
        onTriggered: {
            if (root.writingCountdown > 1) {
                root.writingCountdown -= 1
                return
            }
            stop()
            root.writingPreparationVisible = false
            if (root.measurementObject)
                root.measurementObject.startCalibration("writing")
        }
    }

    function guideX(key) {
        if (key === "left") return 0.28
        if (key === "right") return 0.72
        return 0.5
    }

    function guideY(key) {
        if (key === "up") return 0.30
        if (key === "down") return 0.70
        return 0.5
    }

    RowLayout {
        anchors.fill: parent
        spacing: 12

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumWidth: 560
            radius: Theme.radius
            color: "#0E1726"
            clip: true

            Image {
                id: cameraImage
                anchors.fill: parent
                visible: root.cameraVisible && root.measurementObject && root.measurementObject.cameraConnected
                source: root.measurementObject ? root.measurementObject.frameSource : ""
                fillMode: Image.PreserveAspectFit
                cache: false
                asynchronous: false
            }

            Text {
                anchors.centerIn: parent
                visible: !cameraImage.visible
                text: root.cameraVisible
                    ? (root.measurementObject ? root.measurementObject.cameraMessage : "카메라 준비 중")
                    : "카메라 화면 숨김\n집중 분석은 계속됩니다."
                color: "#A7B3C5"
                font.pixelSize: 14
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                width: parent.width * 0.7
            }

            Item {
                anchors.fill: parent
                visible: cameraImage.visible

                Rectangle {
                    anchors.centerIn: parent
                    width: 34
                    height: 1
                    color: "#B9C5D6"
                    opacity: 0.8
                }
                Rectangle {
                    anchors.centerIn: parent
                    width: 1
                    height: 34
                    color: "#B9C5D6"
                    opacity: 0.8
                }

            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 48
                color: "#CC0E1726"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 15
                    anchors.rightMargin: 12
                    Text {
                        Layout.fillWidth: true
                        text: root.measurementObject ? root.measurementObject.cameraMessage : "카메라 준비 중"
                        color: "#E7EDF6"
                        font.pixelSize: 11
                        elide: Text.ElideRight
                    }
                    Button {
                        id: previewToggle
                        text: root.cameraVisible ? "화면 숨김" : "화면 보기"
                        onClicked: root.cameraVisible = !root.cameraVisible
                        background: Rectangle { radius: Theme.radiusSmall; color: previewToggle.hovered ? "#33445C" : "#243248" }
                        contentItem: Text { text: previewToggle.text; color: "white"; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    }
                }
            }
        }

        ColumnLayout {
            Layout.preferredWidth: 390
            Layout.fillHeight: true
            spacing: 12

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 136
                radius: Theme.radius
                color: Theme.surface
                border.color: Theme.border
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 17
                    spacing: 7
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "측정 상태"; color: Theme.muted; font.pixelSize: 11 }
                        Item { Layout.fillWidth: true }
                        Rectangle {
                            width: 9; height: 9; radius: 5
                            color: root.measurementObject && root.measurementObject.cameraConnected ? Theme.success : Theme.danger
                        }
                    }
                    Text {
                        text: root.measurementObject ? root.measurementObject.statusText : "준비 중"
                        color: root.measurementObject && root.measurementObject.sessionPaused ? Theme.warning : Theme.text
                        font.pixelSize: 25
                        font.weight: Font.Bold
                    }
                    Text {
                        Layout.fillWidth: true
                        text: root.measurementObject ? root.measurementObject.statusDetail : "카메라를 준비하고 있습니다."
                        color: Theme.muted
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: root.measurementObject && root.measurementObject.writingRequired ? 240 : 176
                radius: Theme.radius
                color: Theme.surface
                border.color: Theme.border
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 10
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "기준 자세"; color: Theme.text; font.pixelSize: 15; font.weight: Font.Bold }
                        Item { Layout.fillWidth: true }
                        ActionButton {
                            objectName: "screenValidationButton"
                            text: "시선 검증"
                            implicitHeight: 32
                            enabled: root.measurementObject && root.measurementObject.screenReady
                                && !root.measurementObject.sessionRunning && root.measurementObject.calibrationTarget === ""
                            onClicked: root.measurementObject.startScreenValidation()
                            ToolTip.visible: hovered
                            ToolTip.text: root.measurementObject ? root.measurementObject.gazeMappingMessage : ""
                        }
                    }

                    CalibrationButton {
                        Layout.fillWidth: true
                        label: "화면 자세 설정"
                        ready: root.measurementObject ? root.measurementObject.screenReady : false
                        progress: root.measurementObject ? root.measurementObject.screenCalibrationProgress : 0
                        collecting: root.measurementObject ? root.measurementObject.calibrationTarget === "screen" : false
                        onClicked: { if (root.measurementObject) root.measurementObject.startCalibration("screen") }
                    }
                    CalibrationButton {
                        visible: root.measurementObject ? root.measurementObject.writingRequired : false
                        Layout.fillWidth: true
                        label: "필기 자세 설정"
                        ready: root.measurementObject ? root.measurementObject.writingReady : false
                        progress: root.measurementObject ? root.measurementObject.writingCalibrationProgress : 0
                        collecting: root.measurementObject ? root.measurementObject.calibrationTarget === "writing" : false
                        onClicked: root.prepareWritingCalibration()
                    }
                    Text {
                        Layout.fillWidth: true
                        text: root.measurementObject ? root.measurementObject.calibrationMessage : ""
                        color: Theme.muted
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: Theme.radius
                color: Theme.surface
                border.color: Theme.border
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 11
                    Text { text: "이번 학습"; color: Theme.text; font.pixelSize: 15; font.weight: Font.Bold }
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "학습 시간"; color: Theme.muted; font.pixelSize: 11 }
                        Item { Layout.fillWidth: true }
                        Text { text: root.measurementObject ? formatSeconds(root.measurementObject.elapsedSeconds) : "00:00"; color: Theme.text; font.pixelSize: 17; font.weight: Font.Bold }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "집중률"; color: Theme.muted; font.pixelSize: 11 }
                        Item { Layout.fillWidth: true }
                        Text { text: (root.measurementObject ? root.measurementObject.focusPercent : 0) + "%"; color: Theme.success; font.pixelSize: 17; font.weight: Font.Bold }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "측정 가능 시간"; color: Theme.muted; font.pixelSize: 11 }
                        Item { Layout.fillWidth: true }
                        Text { text: (root.measurementObject ? root.measurementObject.coveragePercent : 0) + "%"; color: Theme.primary; font.pixelSize: 17; font.weight: Font.Bold }
                    }
                    Rectangle {
                        visible: root.measurementObject ? root.measurementObject.sessionPaused : false
                        Layout.fillWidth: true
                        Layout.preferredHeight: 46
                        radius: Theme.radiusSmall
                        color: Theme.warningSoft
                        Text {
                            anchors.centerIn: parent
                            text: root.measurementObject && root.measurementObject.pomodoroPhase === "waiting_next" ? "다음 단계 대기" : "휴식 남은 시간  " + formatSeconds(root.measurementObject ? root.measurementObject.breakRemainingSeconds : 0)
                            color: "#B45309"
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                        }
                    }
                    Item { Layout.fillHeight: true }
                    RowLayout {
                        Layout.fillWidth: true
                        ActionButton {
                            objectName: "measurementBreakAction"
                            Layout.fillWidth: true
                            text: root.measurementObject ? root.measurementObject.breakActionText : "휴식"
                            enabled: root.measurementObject ? root.measurementObject.sessionRunning : false
                            onClicked: { if (root.measurementObject) root.measurementObject.toggleBreak() }
                        }
                        ActionButton {
                            objectName: "measurementEndAction"
                            Layout.fillWidth: true
                            text: "학습 종료"
                            tone: "danger"
                            enabled: root.measurementObject ? root.measurementObject.sessionRunning : false
                            onClicked: { if (root.measurementObject) root.measurementObject.endSession() }
                        }
                    }
                }
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        visible: root.writingPreparationVisible
        z: 100
        color: "#EAF4F7FA"

        ColumnLayout {
            anchors.centerIn: parent
            width: Math.min(parent.width - 48, 620)
            spacing: 18
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: root.writingCountdown
                color: Theme.primary
                font.pixelSize: 76
                font.weight: Font.Bold
            }
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "필기 자세를 준비하세요"
                color: Theme.text
                font.pixelSize: 27
                font.weight: Font.Bold
            }
            Text {
                Layout.fillWidth: true
                text: "카운트다운이 끝나면 종이나 태블릿에 평소처럼 문장 두 줄을 작성하세요.\n시작·중간·완료 시 알림음이 납니다."
                color: Theme.muted
                font.pixelSize: 14
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                lineHeight: 1.35
            }
            ActionButton {
                Layout.alignment: Qt.AlignHCenter
                text: "취소"
                onClicked: {
                    writingCountdownTimer.stop()
                    root.writingPreparationVisible = false
                }
            }
        }
    }

    Dialog {
        id: gazeReport
        objectName: "gazeValidationReport"
        readonly property var rows: root.measurementObject ? root.measurementObject.gazeValidationRows : []
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(620, parent.width - 48)
        modal: true
        padding: 24
        standardButtons: Dialog.Ok
        header: Text {
            text: "시선 검증 결과"
            color: Theme.text
            font.pixelSize: 20
            font.weight: Font.DemiBold
            padding: 24
        }
        background: Rectangle { color: Theme.surface; radius: Theme.radius; border.color: Theme.border }
        contentItem: ColumnLayout {
            spacing: 12
            Text {
                Layout.fillWidth: true
                text: "오차·흔들림은 화면 대각선 대비 비율입니다. 집중 판정은 바뀌지 않습니다."
                color: Theme.muted
                font.pixelSize: 13
                wrapMode: Text.Wrap
            }
            RowLayout {
                Layout.fillWidth: true
                Text { Layout.fillWidth: true; text: "위치"; color: Theme.muted; font.pixelSize: 13 }
                Text { Layout.preferredWidth: 75; text: "중앙값 오차"; color: Theme.muted; font.pixelSize: 13 }
                Text { Layout.preferredWidth: 75; text: "P90 오차"; color: Theme.muted; font.pixelSize: 13 }
                Text { Layout.preferredWidth: 75; text: "흔들림"; color: Theme.muted; font.pixelSize: 13 }
                Text { Layout.preferredWidth: 70; text: "유효 비율"; color: Theme.muted; font.pixelSize: 13 }
            }
            Repeater {
                model: gazeReport.rows.length
                RowLayout {
                    required property int index
                    readonly property var region: gazeReport.rows[index]
                    Layout.fillWidth: true
                    Text {
                        Layout.fillWidth: true
                        text: ({center: "중앙", up: "위쪽", down: "아래쪽", left: "왼쪽", right: "오른쪽"})[parent.region.key]
                        color: Theme.text
                        font.pixelSize: 14
                    }
                    Text { Layout.preferredWidth: 75; text: parent.region.median.toFixed(1) + "%"; color: Theme.text; font.pixelSize: 14 }
                    Text { Layout.preferredWidth: 75; text: parent.region.p90.toFixed(1) + "%"; color: Theme.text; font.pixelSize: 14 }
                    Text { Layout.preferredWidth: 75; text: parent.region.spread.toFixed(1) + "%"; color: Theme.text; font.pixelSize: 14 }
                    Text { Layout.preferredWidth: 70; text: parent.region.valid + "%"; color: Theme.text; font.pixelSize: 14 }
                }
            }
            Text {
                Layout.fillWidth: true
                text: "아직 정확도 합격 여부를 판정하지 않습니다."
                color: Theme.muted
                font.pixelSize: 12
            }
        }
    }

    function formatSeconds(value) {
        var safe = Math.max(0, value)
        var hours = Math.floor(safe / 3600)
        var minutes = Math.floor((safe % 3600) / 60)
        var seconds = Math.floor(safe % 60)
        function two(v) { return v < 10 ? "0" + v : v }
        return hours > 0 ? two(hours) + ":" + two(minutes) + ":" + two(seconds) : two(minutes) + ":" + two(seconds)
    }
}
