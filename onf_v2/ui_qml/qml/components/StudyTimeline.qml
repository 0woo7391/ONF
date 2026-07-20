import QtQuick
import QtQuick.Layouts
import ".."

Item {
    id: root
    objectName: "studyTimeline"
    property int currentHour: 12
    property int currentMinute: 0
    property string visibleRange: rangeText()
    property bool initialized: false
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

    function rowOpacity(row) {
        var distance = Math.abs(row - 3)
        if (distance === 0) return 1.0
        if (distance === 1) return 0.72
        if (distance === 2) return 0.52
        return 0.38
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
            transform: Translate { id: hourShift; y: 0 }
            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                var labelWidth = 28
                var top = 2
                var rows = 7
                var columns = 6
                var currentRowScale = 1.5
                var rowHeight = (height - top - 2) / (rows - 1 + currentRowScale)
                var cellWidth = (width - labelWidth - 2) / columns
                var rowTops = []
                var rowHeights = []
                var nextTop = top
                for (var rowIndex = 0; rowIndex < rows; rowIndex++) {
                    var sizedHeight = rowIndex === 3 ? rowHeight * currentRowScale : rowHeight
                    rowTops.push(nextTop)
                    rowHeights.push(sizedHeight)
                    nextTop += sizedHeight
                }
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
                    var y = rowTops[row]
                    var visibleRowHeight = rowHeights[row]
                    var emphasis = root.rowOpacity(row)
                    ctx.font = row === 3 ? "bold 14px Segoe UI" : "9px Segoe UI"
                    ctx.fillStyle = row === 3 ? Theme.primary : Theme.muted
                    ctx.globalAlpha = row === 3 ? 1 : Math.max(0.52, emphasis)
                    ctx.fillText(root.hourLabel(row - 3), 1, y + visibleRowHeight / 2)
                    ctx.globalAlpha = 1

                    for (var column = 0; column < columns; column++) {
                        var x = labelWidth + column * cellWidth
                        ctx.fillStyle = "#FAFBFC"
                        ctx.globalAlpha = row === 3 ? 1 : 0.48 + emphasis * 0.32
                        ctx.fillRect(x + 1, y + 1, cellWidth - 2, visibleRowHeight - 2)
                        ctx.strokeStyle = Theme.border
                        ctx.lineWidth = 0.7
                        ctx.strokeRect(x + 1, y + 1, cellWidth - 2, visibleRowHeight - 2)
                        ctx.globalAlpha = 1

                        var value = focus[row][column]
                        if (value > 0) {
                            ctx.fillStyle = root.focusColor(value)
                            ctx.globalAlpha = 0.92 * emphasis
                            ctx.fillRect(
                                x + 2,
                                y + 3,
                                cellWidth - 4,
                                visibleRowHeight - 6
                            )
                            ctx.globalAlpha = 1
                        }
                    }
                }

                function planned(row, column, span, label) {
                    var x = labelWidth + column * cellWidth + 2
                    var y = rowTops[row] + 3
                    var plannedHeight = rowHeights[row] - 6
                    ctx.setLineDash([4, 3])
                    ctx.strokeStyle = "#7DA7E8"
                    ctx.lineWidth = 1.3
                    ctx.globalAlpha = root.rowOpacity(row)
                    ctx.strokeRect(x, y, cellWidth * span - 4, plannedHeight)
                    ctx.setLineDash([])
                    ctx.fillStyle = Theme.primary
                    ctx.font = "8px Segoe UI"
                    ctx.fillText(label, x + 4, y + plannedHeight / 2)
                    ctx.globalAlpha = 1
                }

                planned(0, 1, 2, "영어 독해")
                planned(3, 3, 2, "수학 오답")
                planned(5, 0, 3, "한국사")
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
        }
    }

    ParallelAnimation {
        id: hourTransition
        NumberAnimation {
            target: hourShift
            property: "y"
            from: 18
            to: 0
            duration: 240
            easing.type: Easing.OutCubic
        }
        SequentialAnimation {
            NumberAnimation { target: chart; property: "opacity"; from: 0.58; to: 0.82; duration: 80 }
            NumberAnimation { target: chart; property: "opacity"; from: 0.82; to: 1.0; duration: 160 }
        }
    }

    onCurrentHourChanged: {
        chart.requestPaint()
        if (initialized)
            hourTransition.restart()
    }
    onCurrentMinuteChanged: chart.requestPaint()
    Component.onCompleted: {
        initialized = true
        chart.requestPaint()
    }
}
