import QtQuick
import ".."

Item {
    id: root
    objectName: "pomodoroRing"
    property real progress: 0.0
    property color progressColor: Theme.success
    property string timeText: "25:00"
    property string phaseText: "집중 1회차"
    property string roundText: "0 / 4회"
    property color textColor: Theme.text
    property color mutedColor: Theme.muted
    property color trackColor: Theme.border
    property string typeface: ""
    property int lineWidth: 13
    property int timePixelSize: 43
    property int timeWeight: Font.Bold
    property string timeObjectName: "pomodoroTimeValue"
    property bool remainingArc: false
    property real paintedProgress: remainingArc ? 1 - progress : progress
    Behavior on paintedProgress { NumberAnimation { duration: StudyStyle.normal; easing.type: Easing.OutCubic } }

    implicitWidth: 246
    implicitHeight: 246

    Canvas {
        id: ring
        anchors.fill: parent
        antialiasing: true
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var radius = Math.min(width, height) / 2 - root.lineWidth
            var cx = width / 2
            var cy = height / 2
            var start = -Math.PI / 2

            ctx.lineWidth = root.lineWidth
            ctx.lineCap = "round"
            ctx.strokeStyle = root.trackColor
            ctx.beginPath()
            ctx.arc(cx, cy, radius, 0, Math.PI * 2)
            ctx.stroke()

            ctx.strokeStyle = root.progressColor
            ctx.beginPath()
            ctx.arc(cx, cy, radius, start, start + Math.PI * 2 * Math.max(0, Math.min(1, root.paintedProgress)))
            ctx.stroke()
        }
    }

    Column {
        anchors.centerIn: parent
        spacing: 7
        Text { anchors.horizontalCenter: parent.horizontalCenter; text: root.phaseText; color: root.mutedColor; font.family: root.typeface; font.pixelSize: 14; font.weight: Font.Normal }
        Text {
            objectName: root.timeObjectName
            width: root.width - 48
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.timeText
            color: root.textColor
            font.family: root.typeface
            font.pixelSize: root.timePixelSize
            font.weight: root.timeWeight
            font.features: {"tnum": 1}
            fontSizeMode: Text.Fit
            minimumPixelSize: 24
            horizontalAlignment: Text.AlignHCenter
        }
        Text { anchors.horizontalCenter: parent.horizontalCenter; text: root.roundText; color: root.mutedColor; font.family: root.typeface; font.pixelSize: 14; font.weight: Font.Normal }
    }

    onProgressChanged: ring.requestPaint()
    onPaintedProgressChanged: ring.requestPaint()
    onProgressColorChanged: ring.requestPaint()
    onWidthChanged: ring.requestPaint()
    onHeightChanged: ring.requestPaint()
    onTrackColorChanged: ring.requestPaint()
    onLineWidthChanged: ring.requestPaint()
    Component.onCompleted: ring.requestPaint()
}
