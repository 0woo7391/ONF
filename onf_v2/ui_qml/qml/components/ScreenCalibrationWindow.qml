pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Window
import ".."

Window {
    id: root
    objectName: "screenCalibrationWindow"
    color: Theme.background
    flags: Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
    modality: Qt.ApplicationModal
    visible: false
    title: "화면 작업 영역 설정"

    property var measurementObject: null
    property bool closingAfterCalibration: false
    property string pendingTargetKey: "center"
    property string displayedTargetKey: "center"
    property int pendingRunId: -1
    property int pendingStageIndex: -1
    property int displayedRunId: -1
    property int displayedStageIndex: -1
    property bool targetNeedsAck: false
    property bool stagePromptVisible: true
    property string lastDisplaySignature: ""
    readonly property bool validating: measurementObject ? measurementObject.screenValidationActive : false
    readonly property var targets: measurementObject ? measurementObject.calibrationTargets : []
    readonly property var displayedTarget: targets.filter(function(item) { return item.key === root.displayedTargetKey })[0] || ({state: "waiting", progress: 0})
    readonly property bool failed: measurementObject ? measurementObject.screenCalibrationFailed : false
    readonly property string targetState: failed ? "failed" : displayedTarget.state
    readonly property bool collectionStable: measurementObject ? measurementObject.screenTargetStable : false
    readonly property int sampledCount: targets.filter(function(item) { return item.state === "sampled" }).length

    function directionLabel(key) {
        return ({center: "중앙", up: "위쪽", down: "아래쪽", left: "왼쪽", right: "오른쪽"})[key] || key
    }

    function stateLabel(state) {
        if (state === "collecting") return root.collectionStable ? "안정 수집 중" : "수집 준비"
        return ({waiting: "대기", settling: "준비", paused: "일시 중단", sampled: "수집 완료", failed: "재시도 필요"})[state] || "대기"
    }

    function stateColor(state, key) {
        if (state === "sampled" || (state === "collecting" && root.collectionStable)) return Theme.success
        if (state === "settling" || state === "collecting" || state === "paused"
            || (state === "waiting" && key === root.pendingTargetKey)) return Theme.warning
        if (state === "failed") return Theme.danger
        return Theme.muted
    }

    function promptLabel(key) {
        if (key === "left") return "왼쪽 점을 보세요"
        if (key === "right") return "오른쪽 점을 보세요"
        if (key === "up") return "위쪽 점을 보세요"
        if (key === "down") return "아래쪽 점을 보세요"
        return "중앙 점을 보세요"
    }

    function cancelAndClose() {
        closingAfterCalibration = true
        if (measurementObject)
            measurementObject.cancelCalibration()
        close()
    }

    function openOn(screenValue) {
        if (screenValue)
            screen = screenValue
        closingAfterCalibration = false
        pendingTargetKey = measurementObject.calibrationGuide || "center"
        displayedTargetKey = pendingTargetKey
        pendingRunId = measurementObject.calibrationRunId
        pendingStageIndex = measurementObject.calibrationStageIndex
        targetNeedsAck = false
        lastDisplaySignature = ""
        stagePromptVisible = true
        stagePromptTimer.restart()
        showFullScreen()
        requestActivate()
    }

    function finishAndClose() {
        if (!visible)
            return
        closingAfterCalibration = true
        close()
    }

    onClosing: function(close) {
        var shouldCancel = !closingAfterCalibration && measurementObject
                           && (measurementObject.calibrationTarget === "screen" || measurementObject.calibrationTarget === "validation" || root.failed)
        closingAfterCalibration = true
        targetNeedsAck = false
        stagePromptTimer.stop()
        if (shouldCancel)
            measurementObject.cancelCalibration()
        close.accepted = true
    }

    onFrameSwapped: {
        if (visible && !root.failed && !stagePromptVisible && target.opacity >= 0.999 && measurementObject) {
            var center = target.mapToItem(root.contentItem, target.width / 2, target.height / 2)
            var display = {
                u: center.x / root.width, v: center.y / root.height,
                width: root.width, height: root.height,
                screenName: Screen.name, screenX: Screen.virtualX, screenY: Screen.virtualY,
                screenWidth: Screen.width, screenHeight: Screen.height,
                dpr: Screen.devicePixelRatio
            }
            var signature = JSON.stringify(display)
            if (!targetNeedsAck && signature === lastDisplaySignature)
                return
            targetNeedsAck = false
            lastDisplaySignature = signature
            measurementObject.screenTargetDisplayed(displayedRunId, displayedStageIndex, displayedTargetKey, display)
        }
    }

    Shortcut {
        sequence: "Esc"
        context: Qt.ApplicationShortcut
        enabled: root.visible
        onActivated: root.cancelAndClose()
    }

    Connections {
        target: root.measurementObject
        enabled: root.measurementObject !== null
        ignoreUnknownSignals: true
        function onStateChanged() {
            if (!root.visible)
                return
            if (root.failed) {
                stagePromptTimer.stop()
                root.stagePromptVisible = false
                root.targetNeedsAck = false
                var failedTargets = root.measurementObject.calibrationTargets.filter(function(item) { return item.state === "failed" })
                if (failedTargets.length > 0)
                    root.displayedTargetKey = failedTargets[0].key
                return
            }
            if (root.measurementObject.calibrationTarget !== "screen" && root.measurementObject.calibrationTarget !== "validation")
                return
            var key = root.measurementObject.calibrationGuide || "center"
            var runId = root.measurementObject.calibrationRunId
            var stageIndex = root.measurementObject.calibrationStageIndex
            if (key === root.pendingTargetKey && runId === root.pendingRunId && stageIndex === root.pendingStageIndex)
                return
            root.pendingTargetKey = key
            root.pendingRunId = runId
            root.pendingStageIndex = stageIndex
            root.targetNeedsAck = false
            root.stagePromptVisible = true
            stagePromptTimer.restart()
        }
    }

    Timer {
        id: stagePromptTimer
        objectName: "calibrationStagePromptTimer"
        interval: 1100
        repeat: false
        onTriggered: {
            root.displayedTargetKey = root.pendingTargetKey
            root.displayedRunId = root.pendingRunId
            root.displayedStageIndex = root.pendingStageIndex
            root.stagePromptVisible = false
            root.targetNeedsAck = true
            root.lastDisplaySignature = ""
        }
    }

    Rectangle {
        id: header
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 72
        color: Theme.surface
        RowLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 20
            Text {
                text: root.validating ? "시선 검증" : "화면 작업 영역 설정"
                color: Theme.text
                font.pixelSize: 20
                font.weight: Font.DemiBold
            }
            Text {
                Layout.fillWidth: true
                text: root.failed ? "수집 중단" : root.validating ? "별도 표본 · 집중 판정 유지" : "표본 수집 · 방향 검증 전"
                color: root.failed ? Theme.danger : Theme.muted
                font.pixelSize: 14
                elide: Text.ElideRight
            }
            Text {
                text: root.sampledCount + " / " + root.targets.length + " 수집"
                color: Theme.muted
                font.pixelSize: 14
            }
            ActionButton {
                objectName: "cancelCalibrationButton"
                text: "취소"
                onClicked: root.cancelAndClose()
            }
        }
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 1
            color: Theme.border
        }
    }

    Item {
        id: targetArea
        objectName: "calibrationTargetArea"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: header.bottom
        anchors.bottom: stages.top

        Item {
            id: target
            objectName: "calibrationTarget"
            property string key: root.displayedTargetKey
            readonly property var validationPosition: root.validating && root.measurementObject
                ? root.measurementObject.validationTargetPositions[key] : null
            readonly property real horizontalRatio: validationPosition ? validationPosition[0] : key === "left" ? 0.16 : key === "right" ? 0.84 : 0.5
            readonly property real verticalRatio: validationPosition ? validationPosition[1] : key === "up" ? 0.16 : key === "down" ? 0.84 : 0.5
            readonly property real instructionReserve: root.failed ? instruction.height : 112
            readonly property real preferredY: Math.max(12, Math.min(targetArea.height - height - 12, root.height * verticalRatio - header.height - height / 2))
            readonly property bool instructionAbove: key === "down" || preferredY + height + instructionReserve + 14 > targetArea.height - 12
            x: Math.max(12, Math.min(targetArea.width - width - 12, targetArea.width * horizontalRatio - width / 2))
            y: instructionAbove ? Math.min(targetArea.height - height - 12, Math.max(preferredY, instructionReserve + 26)) : preferredY
            width: 96
            height: 96
            opacity: root.stagePromptVisible ? 0 : 1
            Behavior on opacity { NumberAnimation { duration: Theme.fast } }

            Canvas {
                id: acquisitionRing
                objectName: "calibrationAcquisitionRing"
                anchors.fill: parent
                property real fill: Math.max(0, Math.min(1, root.displayedTarget.progress))
                property color stroke: root.validating ? Theme.muted : root.stateColor(root.targetState, target.key)
                Behavior on fill { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }
                onFillChanged: requestPaint()
                onStrokeChanged: requestPaint()
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.reset()
                    ctx.lineWidth = 2
                    ctx.lineCap = "round"
                    var radius = width / 2 - 6
                    ctx.strokeStyle = stroke
                    ctx.beginPath()
                    ctx.arc(width / 2, height / 2, radius, 0, Math.PI * 2)
                    ctx.stroke()
                    if (fill > 0) {
                        ctx.lineWidth = 6
                        ctx.strokeStyle = stroke
                        ctx.beginPath()
                        ctx.arc(width / 2, height / 2, radius, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * fill)
                        ctx.stroke()
                    }
                }
            }
            Rectangle {
                anchors.centerIn: parent
                width: 14
                height: 14
                radius: 7
                color: root.validating ? Theme.muted : root.stateColor(root.targetState, target.key)
                Behavior on color { ColorAnimation { duration: Theme.fast } }
            }
        }

        Column {
            id: instruction
            objectName: "calibrationInstruction"
            width: Math.min(380, targetArea.width - 32)
            x: Math.max(16, Math.min(targetArea.width - width - 16, target.x + target.width / 2 - width / 2))
            y: target.instructionAbove ? target.y - height - 14 : target.y + target.height + 14
            spacing: 10
            visible: !root.stagePromptVisible
            Text {
                width: parent.width
                text: root.failed ? "부족한 방향을 다시 수집하세요" : root.promptLabel(target.key)
                color: root.failed ? Theme.danger : Theme.text
                font.pixelSize: 18
                font.weight: Font.DemiBold
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
            }
            Text {
                objectName: "calibrationReason"
                width: parent.width
                text: root.targetState === "collecting"
                    ? root.collectionStable ? "표본을 안정적으로 수집하고 있습니다." : "표본 안정성을 확인하고 있습니다."
                    : root.measurementObject ? root.measurementObject.calibrationMessage : "카메라 분석을 기다리고 있습니다."
                color: Theme.muted
                font.pixelSize: 14
                lineHeight: 1.25
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
            }
            ActionButton {
                objectName: "retryCalibrationButton"
                anchors.horizontalCenter: parent.horizontalCenter
                visible: root.failed
                text: "부족한 방향 다시 수집"
                tone: "primary"
                onClicked: root.measurementObject.retryScreenCalibration()
            }
        }

        Column {
            anchors.centerIn: parent
            width: parent.width - 48
            spacing: 14
            visible: root.stagePromptVisible
            Text {
                width: parent.width
                text: root.promptLabel(root.pendingTargetKey)
                color: Theme.text
                font.pixelSize: 40
                font.weight: Font.DemiBold
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
            }
            Text {
                width: parent.width
                text: "잠시 후 점이 표시됩니다"
                color: Theme.muted
                font.pixelSize: 16
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }

    Rectangle {
        id: stages
        objectName: "calibrationStages"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 96
        color: Theme.surface
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: Theme.border
        }
        RowLayout {
            anchors.centerIn: parent
            width: Math.min(parent.width - 32, 820)
            spacing: 12
            Repeater {
                model: root.targets.length
                delegate: ColumnLayout {
                    id: stage
                    required property int index
                    readonly property var entry: root.targets[index]
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    spacing: 8
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: root.directionLabel(stage.entry.key)
                        color: Theme.text
                        font.pixelSize: 16
                        font.weight: Font.DemiBold
                    }
                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: 6
                        Text {
                            text: stage.entry.state === "sampled" ? "✓" : stage.entry.state === "failed" ? "!" : stage.entry.state === "paused" ? "Ⅱ" : "●"
                            color: root.stateColor(stage.entry.state, stage.entry.key)
                            font.pixelSize: 12
                        }
                        Text {
                            text: root.stateLabel(stage.entry.state)
                            color: Theme.muted
                            font.pixelSize: 13
                        }
                    }
                }
            }
        }
    }
}
