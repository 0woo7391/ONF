import QtQuick
import QtQuick.Layouts
import ".."

Item {
    id: root
    objectName: "studyTimeline"
    property int currentHour: 12
    property int currentMinute: 0
    property var hourlyData: []
    property var plannerTasks: []
    property string visibleRange: rangeText()
    property bool initialized: false
    implicitHeight: 230

    function hourLabel(offset) {
        var hour = (currentHour + offset + 24) % 24
        return hour < 10 ? "0" + hour : "" + hour
    }

    function focusColor(value) {
        var score = Math.max(0, Math.min(1, value / 100))
        var from = score < 0.5 ? [233, 93, 105] : [235, 184, 56]
        var to = score < 0.5 ? [235, 184, 56] : [36, 173, 110]
        var fraction = score < 0.5 ? score * 2 : (score - 0.5) * 2
        return Qt.rgba((from[0] + (to[0] - from[0]) * fraction) / 255,
                       (from[1] + (to[1] - from[1]) * fraction) / 255,
                       (from[2] + (to[2] - from[2]) * fraction) / 255, 1)
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
            StudyText { text: "실제 학습"; font.pixelSize: 16; font.weight: Font.Medium }
            Item { Layout.fillWidth: true }
            StudyText { text: root.rangeText(); color: StudyStyle.muted; font.pixelSize: 14 }
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
                var labelWidth = 38
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

                function focusForHour(hour) {
                    for (var dataIndex = 0; dataIndex < root.hourlyData.length; dataIndex++) {
                        if (Number(root.hourlyData[dataIndex].hour) === hour)
                            return root.hourlyData[dataIndex]
                    }
                    return {values: []}
                }

                ctx.font = "14px " + StudyStyle.family
                ctx.textAlign = "left"
                ctx.textBaseline = "middle"
                for (var row = 0; row < rows; row++) {
                    var y = rowTops[row]
                    var visibleRowHeight = rowHeights[row]
                    var emphasis = root.rowOpacity(row)
                    ctx.font = (row === 3 ? "600 22px " : "14px ") + StudyStyle.family
                    ctx.fillStyle = row === 3 ? StudyStyle.ink : StudyStyle.muted
                    ctx.globalAlpha = row === 3 ? 1 : Math.max(0.52, emphasis)
                    ctx.fillText(root.hourLabel(row - 3), 1, y + visibleRowHeight / 2)
                    ctx.globalAlpha = 1

                    for (var column = 0; column < columns; column++) {
                        var x = labelWidth + column * cellWidth
                        ctx.fillStyle = "#FAFBFC"
                        ctx.globalAlpha = row === 3 ? 1 : 0.48 + emphasis * 0.32
                        ctx.fillRect(x + 1, y + 1, cellWidth - 2, visibleRowHeight - 2)
                        ctx.strokeStyle = StudyStyle.line
                        ctx.lineWidth = 0.7
                        ctx.strokeRect(x + 1, y + 1, cellWidth - 2, visibleRowHeight - 2)
                        ctx.globalAlpha = 1

                        var rowData = focusForHour((root.currentHour + row - 3 + 24) % 24)
                        var rowValues = rowData.values || []
                        var value = column < rowValues.length ? Number(rowValues[column]) : 0
                        if (rowData.present ? rowData.present[column] : value > 0) {
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

                function planned(row, column, span, label, complete) {
                    var x = labelWidth + column * cellWidth + 2
                    var y = rowTops[row] + 3
                    var plannedHeight = rowHeights[row] - 6
                    ctx.setLineDash(complete ? [] : [4, 3])
                    ctx.strokeStyle = complete ? "#45878B" : "#95B8BD"
                    ctx.lineWidth = complete ? 2.2 : 1.4
                    ctx.globalAlpha = root.rowOpacity(row)
                    ctx.strokeRect(x, y, cellWidth * span - 4, plannedHeight)
                    ctx.setLineDash([])
                    if (label !== "") {
                        ctx.save()
                        ctx.beginPath()
                        ctx.rect(x + 3, y, Math.max(0, cellWidth * span - 10), plannedHeight)
                        ctx.clip()
                        ctx.fillStyle = StudyStyle.ink
                        ctx.font = "14px " + StudyStyle.family
                        ctx.fillText(label, x + 4, y + plannedHeight / 2)
                        ctx.restore()
                    }
                    ctx.globalAlpha = 1
                }

                function visibleRow(hour) {
                    for (var visibleIndex = 0; visibleIndex < rows; visibleIndex++) {
                        if ((root.currentHour + visibleIndex - 3 + 24) % 24 === hour)
                            return visibleIndex
                    }
                    return -1
                }

                for (var taskIndex = 0; taskIndex < root.plannerTasks.length; taskIndex++) {
                    var task = root.plannerTasks[taskIndex]
                    if (!task.start || task.start.indexOf(":") < 0) continue
                    var startParts = task.start.split(":")
                    var cursor = Number(startParts[0]) * 60 + Number(startParts[1])
                    var durationDigits = String(task.duration || "").replace(/[^0-9]/g, "")
                    var remaining = durationDigits === "" ? 0 : Number(durationDigits)
                    var firstSegment = true
                    while (remaining > 0) {
                        var hour = Math.floor(cursor / 60) % 24
                        var planRow = visibleRow(hour)
                        var minuteOffset = cursor % 60
                        var segmentMinutes = Math.min(remaining, 60 - minuteOffset)
                        if (planRow >= 0)
                            planned(planRow, minuteOffset / 10, segmentMinutes / 10, firstSegment ? task.title : "", Number(task.taskState) === 1)
                        cursor += segmentMinutes
                        remaining -= segmentMinutes
                        firstSegment = false
                    }
                }
            }
        }

        Row {
            Layout.alignment: Qt.AlignRight
            spacing: 11
            Row {
                spacing: 4
                Rectangle { width: 22; height: 8; radius: 2; color: "#24AD6E" }
                StudyText { text: "집중도"; color: StudyStyle.muted; font.pixelSize: 14 }
            }
            Row {
                spacing: 4
                Canvas {
                    width: 22
                    height: 10
                    onPaint: {
                        var ctx = getContext("2d")
                        ctx.reset()
                        ctx.strokeStyle = "#95B8BD"
                        ctx.lineWidth = 1.2
                        ctx.setLineDash([3, 2])
                        ctx.strokeRect(1, 1, width - 2, height - 2)
                    }
                }
                StudyText { text: "계획"; color: StudyStyle.muted; font.pixelSize: 14 }
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
    onHourlyDataChanged: chart.requestPaint()
    onWidthChanged: chart.requestPaint()
    onHeightChanged: chart.requestPaint()
    onPlannerTasksChanged: chart.requestPaint()
    Component.onCompleted: {
        initialized = true
        chart.requestPaint()
    }
}
