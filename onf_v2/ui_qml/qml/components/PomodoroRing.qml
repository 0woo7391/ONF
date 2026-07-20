import QtQuick
import ".."

Item {
    id: root
    objectName: "pomodoroRing"
    property real progress: 0.0
    property string timeText: "25:00"
    property string phaseText: "집중 1회차"
    property string roundText: "0 / 4회"

    implicitWidth: 246
    implicitHeight: 246

    Canvas {
        id: ring
        anchors.fill: parent
        antialiasing: true
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var lineWidth = 13
            var radius = Math.min(width, height) / 2 - lineWidth
            var cx = width / 2
            var cy = height / 2
            var start = -Math.PI / 2

            ctx.lineWidth = lineWidth
            ctx.lineCap = "round"
            ctx.strokeStyle = Theme.border
            ctx.beginPath()
            ctx.arc(cx, cy, radius, 0, Math.PI * 2)
            ctx.stroke()

            ctx.strokeStyle = Theme.success
            ctx.beginPath()
            ctx.arc(cx, cy, radius, start, start + Math.PI * 2 * Math.max(0.015, root.progress))
            ctx.stroke()
        }
    }

    Column {
        anchors.centerIn: parent
        spacing: 7
        Text { anchors.horizontalCenter: parent.horizontalCenter; text: root.phaseText; color: Theme.muted; font.pixelSize: 13; font.weight: Font.DemiBold }
        Text { anchors.horizontalCenter: parent.horizontalCenter; text: root.timeText; color: Theme.text; font.pixelSize: 43; font.weight: Font.Bold }
        Text { anchors.horizontalCenter: parent.horizontalCenter; text: root.roundText; color: Theme.success; font.pixelSize: 12; font.weight: Font.DemiBold }
    }

    onProgressChanged: ring.requestPaint()
    Component.onCompleted: ring.requestPaint()
}
