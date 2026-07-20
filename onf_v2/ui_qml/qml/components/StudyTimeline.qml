import QtQuick
import QtQuick.Layouts
import ".."

Item {
    id: root
    objectName: "studyTimeline"
    property int currentHour: 12
    property int currentMinute: 0
    property string visibleRange: rangeText()
    implicitHeight: 230

    function hourLabel(offset) {
        var hour = (currentHour + offset + 24) % 24
        return hour < 10 ? "0" + hour : "" + hour
    }

    function focusColor(value) {
        if (value < 55) return Theme.danger
        if (value < 78) return Theme.warning
        return Theme.success
    }

    function rangeText() {
        return hourLabel(-3) + ":00 — " + hourLabel(3) + ":59"
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 6

        RowLayout {
            Layout.fillWidth: true
            Text { text: "실시간 학습 타임라인"; color: Theme.text; font.pixelSize: 12; font.weight: Font.DemiBold }
            Item { Layout.fillWidth: true }
            Text { text: root.rangeText(); color: Theme.muted; font.pixelSize: 9 }
        }

        Canvas {
            id: chart
            Layout.fillWidth: true
            Layout.fillHeight: true
            antialiasing: true
            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                var labelWidth = 28
                var top = 2
                var rows = 7
                var columns = 6
                var rowHeight = (height - top - 2) / rows
                var cellWidth = (width - labelWidth - 2) / columns
                var focus = [
                    [0, 0, 0, 0, 0, 0],
                    [0, 0, 82, 88, 91, 76],
                    [68, 72, 85, 89, 0, 0],
                    [91, 86, 78, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0]
                ]

                ctx.font = "9px Segoe UI"
                ctx.textAlign = "left"
                ctx.textBaseline = "middle"
                for (var row = 0; row < rows; row++) {
                    var y = top + row * rowHeight
                    ctx.fillStyle = Theme.muted
                    ctx.fillText(root.hourLabel(row - 3), 1, y + rowHeight / 2)

                    for (var column = 0; column < columns; column++) {
                        var x = labelWidth + column * cellWidth
                        ctx.fillStyle = row === 3 ? "#F3F7FD" : "#FAFBFC"
                        ctx.fillRect(x + 1, y + 1, cellWidth - 2, rowHeight - 2)
                        ctx.strokeStyle = Theme.border
                        ctx.lineWidth = 0.7
                        ctx.strokeRect(x + 1, y + 1, cellWidth - 2, rowHeight - 2)

                        var value = focus[row][column]
                        if (value > 0) {
                            ctx.fillStyle = root.focusColor(value)
                            ctx.globalAlpha = 0.86
                            ctx.fillRect(x + 2, y + 3, cellWidth - 4, rowHeight - 6)
                            ctx.globalAlpha = 1
                        }
                    }
                }

                function planned(row, column, span, label) {
                    var x = labelWidth + column * cellWidth + 2
                    var y = top + row * rowHeight + 3
                    ctx.setLineDash([4, 3])
                    ctx.strokeStyle = "#7DA7E8"
                    ctx.lineWidth = 1.3
                    ctx.strokeRect(x, y, cellWidth * span - 4, rowHeight - 6)
                    ctx.setLineDash([])
                    ctx.fillStyle = Theme.primary
                    ctx.font = "8px Segoe UI"
                    ctx.fillText(label, x + 4, y + (rowHeight - 6) / 2)
                }

                planned(0, 1, 2, "영어 독해")
                planned(3, 3, 2, "수학 오답")
                planned(5, 0, 3, "한국사")

                var currentColumn = Math.min(5, Math.floor(root.currentMinute / 10))
                var currentX = labelWidth + currentColumn * cellWidth + 1
                var currentY = top + 3 * rowHeight + 1
                ctx.strokeStyle = Theme.primary
                ctx.lineWidth = 2
                ctx.strokeRect(currentX, currentY, cellWidth - 2, rowHeight - 2)
            }
        }

        Row {
            Layout.alignment: Qt.AlignRight
            spacing: 11
            Row {
                spacing: 4
                Rectangle { width: 22; height: 8; radius: 2; color: Theme.success }
                Text { text: "집중도"; color: Theme.muted; font.pixelSize: 9 }
            }
            Row {
                spacing: 4
                Canvas {
                    width: 22
                    height: 10
                    onPaint: {
                        var ctx = getContext("2d")
                        ctx.reset()
                        ctx.strokeStyle = "#7DA7E8"
                        ctx.lineWidth = 1.2
                        ctx.setLineDash([3, 2])
                        ctx.strokeRect(1, 1, width - 2, height - 2)
                    }
                }
                Text { text: "계획"; color: Theme.muted; font.pixelSize: 9 }
            }
            Row {
                spacing: 4
                Rectangle { width: 10; height: 10; radius: 2; color: "transparent"; border.color: Theme.primary; border.width: 2 }
                Text { text: "현재"; color: Theme.muted; font.pixelSize: 9 }
            }
        }
    }

    onCurrentHourChanged: chart.requestPaint()
    onCurrentMinuteChanged: chart.requestPaint()
    Component.onCompleted: chart.requestPaint()
}
