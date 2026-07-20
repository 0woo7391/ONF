import QtQuick
import QtQuick.Layouts
import ".."

Item {
    id: root

    RowLayout {
        anchors.fill: parent
        spacing: 12

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: Theme.radius
            color: Theme.surface
            border.color: Theme.border
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 8
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "학습시간"; color: Theme.text; font.pixelSize: 14; font.weight: Font.DemiBold }
                    Item { Layout.fillWidth: true }
                    Text { text: "총 21시간 40분"; color: Theme.primary; font.pixelSize: 11; font.weight: Font.DemiBold }
                }
                Canvas {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    onPaint: {
                        var ctx = getContext("2d")
                        ctx.reset()
                        var values = [190, 245, 150, 280, 225, 330, 175]
                        var labels = ["7/20 월", "7/21 화", "7/22 수", "7/23 목", "7/24 금", "7/25 토", "7/26 일"]
                        var left = 26
                        var bottom = 28
                        var plotHeight = height - bottom - 8
                        var slot = (width - left) / 7
                        ctx.font = "9px Segoe UI"
                        ctx.textAlign = "center"
                        ctx.textBaseline = "middle"
                        for (var i = 0; i < 7; i++) {
                            var barHeight = plotHeight * values[i] / 360
                            ctx.fillStyle = i === 5 ? Theme.primary : "#91B7F4"
                            ctx.fillRect(left + i * slot + slot * 0.24, plotHeight - barHeight + 7, slot * 0.52, barHeight)
                            ctx.fillStyle = Theme.muted
                            ctx.fillText(labels[i], left + i * slot + slot / 2, height - 10)
                        }
                    }
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
                spacing: 8
                Text { text: "학습 상태 비교"; color: Theme.text; font.pixelSize: 14; font.weight: Font.DemiBold }
                Canvas {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    onPaint: {
                        var ctx = getContext("2d")
                        ctx.reset()
                        var series = [
                            {color: Theme.success, values: [78, 84, 72, 88, 81, 91, 76]},
                            {color: Theme.primary, values: [70, 77, 65, 82, 74, 87, 69]},
                            {color: Theme.warning, values: [18, 12, 24, 8, 16, 6, 20]},
                            {color: "#8B7CF6", values: [96, 94, 89, 97, 93, 98, 91]}
                        ]
                        var left = 24
                        var bottom = 22
                        var plotWidth = width - left - 8
                        var plotHeight = height - bottom - 8
                        ctx.font = "8px Segoe UI"
                        ctx.textAlign = "right"
                        ctx.textBaseline = "middle"
                        for (var mark = 0; mark <= 100; mark += 25) {
                            var y = 8 + plotHeight * (1 - mark / 100)
                            ctx.strokeStyle = Theme.border
                            ctx.lineWidth = 0.7
                            ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(width - 8, y); ctx.stroke()
                            ctx.fillStyle = Theme.muted
                            ctx.fillText(mark, left - 4, y)
                        }
                        for (var s = 0; s < series.length; s++) {
                            ctx.strokeStyle = series[s].color
                            ctx.fillStyle = series[s].color
                            ctx.lineWidth = 2
                            ctx.beginPath()
                            for (var i = 0; i < 7; i++) {
                                var x = left + plotWidth * i / 6
                                var py = 8 + plotHeight * (1 - series[s].values[i] / 100)
                                if (i === 0) ctx.moveTo(x, py); else ctx.lineTo(x, py)
                            }
                            ctx.stroke()
                            for (var p = 0; p < 7; p++) {
                                var px = left + plotWidth * p / 6
                                var pointY = 8 + plotHeight * (1 - series[s].values[p] / 100)
                                ctx.beginPath(); ctx.arc(px, pointY, 2.5, 0, Math.PI * 2); ctx.fill()
                            }
                        }
                    }
                }
                Row {
                    Layout.alignment: Qt.AlignRight
                    spacing: 10
                    Repeater {
                        model: [
                            {label: "집중률", color: Theme.success},
                            {label: "순공", color: Theme.primary},
                            {label: "이탈", color: Theme.warning},
                            {label: "커버리지", color: "#8B7CF6"}
                        ]
                        delegate: Row {
                            id: legendItem
                            required property var modelData
                            spacing: 4
                            Rectangle { width: 14; height: 3; radius: 2; color: legendItem.modelData.color }
                            Text { text: legendItem.modelData.label; color: Theme.muted; font.pixelSize: 9 }
                        }
                    }
                }
            }
        }
    }
}
