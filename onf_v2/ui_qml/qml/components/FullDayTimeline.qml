import QtQuick
import QtQuick.Layouts
import ".."

Item {
    id: root
    objectName: "fullDayTimeline"
    property var hourlyData: []

    function focusColor(value) {
        if (value < 55) return Theme.danger
        if (value < 78) return Theme.warning
        return Theme.success
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 7

        RowLayout {
            Layout.fillWidth: true
            Text { text: "선택한 하루 24시간"; color: Theme.text; font.pixelSize: 12; font.weight: Font.DemiBold }
            Item { Layout.fillWidth: true }
            Text { text: "한 칸 10분"; color: Theme.muted; font.pixelSize: 9 }
        }

        Canvas {
            id: chart
            Layout.fillWidth: true
            Layout.fillHeight: true
            antialiasing: true
            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                var rows = 24
                var columns = 6
                var labelWidth = 30
                var rowHeight = (height - 2) / rows
                var cellWidth = (width - labelWidth - 2) / columns
                var demo = [
                    {hour: 8, values: [0, 82, 88, 91, 0, 0]},
                    {hour: 10, values: [72, 76, 84, 89, 81, 0]},
                    {hour: 13, values: [0, 0, 64, 71, 78, 83]},
                    {hour: 19, values: [86, 92, 88, 79, 84, 0]}
                ]
                var source = root.hourlyData.length > 0 ? root.hourlyData : demo

                ctx.textBaseline = "middle"
                ctx.textAlign = "left"
                for (var row = 0; row < rows; row++) {
                    var y = row * rowHeight
                    ctx.fillStyle = Theme.muted
                    ctx.font = "8px Segoe UI"
                    ctx.fillText((row < 10 ? "0" : "") + row, 1, y + rowHeight / 2)
                    for (var column = 0; column < columns; column++) {
                        var x = labelWidth + column * cellWidth
                        ctx.fillStyle = "#FAFBFC"
                        ctx.fillRect(x + 1, y + 1, cellWidth - 2, rowHeight - 2)
                        ctx.strokeStyle = Theme.border
                        ctx.lineWidth = 0.55
                        ctx.strokeRect(x + 1, y + 1, cellWidth - 2, rowHeight - 2)
                    }
                }

                for (var itemIndex = 0; itemIndex < source.length; itemIndex++) {
                    var item = source[itemIndex]
                    var values = item.values || []
                    for (var valueIndex = 0; valueIndex < Math.min(columns, values.length); valueIndex++) {
                        var value = Number(values[valueIndex])
                        if (value <= 0) continue
                        ctx.fillStyle = root.focusColor(value)
                        ctx.globalAlpha = 0.82
                        ctx.fillRect(
                            labelWidth + valueIndex * cellWidth + 2,
                            Number(item.hour) * rowHeight + 2,
                            cellWidth - 4,
                            rowHeight - 4
                        )
                    }
                }
                ctx.globalAlpha = 1
            }
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
        }

        Row {
            Layout.alignment: Qt.AlignRight
            spacing: 6
            Text { text: "낮음"; color: Theme.muted; font.pixelSize: 8 }
            Repeater {
                model: [Theme.danger, Theme.warning, Theme.success]
                delegate: Rectangle { required property color modelData; width: 18; height: 7; radius: 2; color: modelData; opacity: 0.82 }
            }
            Text { text: "높음"; color: Theme.muted; font.pixelSize: 8 }
        }
    }

    onHourlyDataChanged: chart.requestPaint()
}
