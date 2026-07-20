pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import ".."

Item {
    id: root
    objectName: "weeklyRecordCharts"
    property var dayData: []
    readonly property var demoData: [
        {label:"7/20 월",study:190,focus:78,pure:70,away:18},
        {label:"7/21 화",study:245,focus:84,pure:77,away:12},
        {label:"7/22 수",study:150,focus:72,pure:65,away:24},
        {label:"7/23 목",study:280,focus:88,pure:82,away:8},
        {label:"7/24 금",study:225,focus:81,pure:74,away:16},
        {label:"7/25 토",study:330,focus:91,pure:87,away:6},
        {label:"7/26 일",study:175,focus:76,pure:69,away:20}
    ]

    function durationText(minutes) {
        var safe = Math.max(0, Math.round(minutes))
        return Math.floor(safe / 60) + "시간 " + (safe % 60) + "분"
    }

    function totalStudy() {
        var total = 0
        var data = dayData.length > 0 ? dayData : demoData
        for (var i = 0; i < data.length; i++) total += Number(data[i].study)
        return total
    }

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
                    Text { text: "주간 학습 흐름"; color: Theme.text; font.pixelSize: 15; font.weight: Font.Bold }
                    Item { Layout.fillWidth: true }
                    Text { text: "총 " + root.durationText(root.totalStudy()); color: Theme.primary; font.pixelSize: 11; font.weight: Font.DemiBold }
                }

                Canvas {
                    id: weeklyChart
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    antialiasing: true
                    onPaint: {
                        var ctx = getContext("2d")
                        ctx.reset()
                        var data = root.dayData.length > 0 ? root.dayData : root.demoData
                        if (!data || data.length === 0) return
                        var left = 36
                        var right = 34
                        var top = 16
                        var bottom = 34
                        var plotWidth = width - left - right
                        var plotHeight = height - top - bottom
                        var slot = plotWidth / data.length
                        var maxMinutes = 360

                        ctx.font = "8px Segoe UI"
                        ctx.textBaseline = "middle"
                        for (var mark = 0; mark <= 6; mark += 2) {
                            var gridY = top + plotHeight * (1 - mark / 6)
                            ctx.strokeStyle = Theme.border
                            ctx.lineWidth = 0.7
                            ctx.beginPath(); ctx.moveTo(left, gridY); ctx.lineTo(width - right, gridY); ctx.stroke()
                            ctx.fillStyle = Theme.muted
                            ctx.textAlign = "right"
                            ctx.fillText(mark + "h", left - 5, gridY)
                            ctx.textAlign = "left"
                            ctx.fillText(Math.round(mark / 6 * 100) + "%", width - right + 5, gridY)
                        }

                        for (var i = 0; i < data.length; i++) {
                            var barHeight = plotHeight * Math.min(maxMinutes, Number(data[i].study)) / maxMinutes
                            var barX = left + i * slot + slot * 0.23
                            ctx.fillStyle = i === 5 ? Theme.primary : "#AFC9F4"
                            ctx.fillRect(barX, top + plotHeight - barHeight, slot * 0.54, barHeight)
                            ctx.fillStyle = Theme.muted
                            ctx.textAlign = "center"
                            ctx.fillText(data[i].label, left + i * slot + slot / 2, height - 12)
                        }

                        var series = [
                            {key:"focus", color:Theme.success},
                            {key:"pure", color:Theme.primary},
                            {key:"away", color:Theme.warning}
                        ]
                        for (var seriesIndex = 0; seriesIndex < series.length; seriesIndex++) {
                            var item = series[seriesIndex]
                            ctx.strokeStyle = item.color
                            ctx.fillStyle = item.color
                            ctx.lineWidth = 2.2
                            ctx.beginPath()
                            for (var point = 0; point < data.length; point++) {
                                var x = left + point * slot + slot / 2
                                var y = top + plotHeight * (1 - Number(data[point][item.key]) / 100)
                                if (point === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
                            }
                            ctx.stroke()
                            for (var dot = 0; dot < data.length; dot++) {
                                var dotX = left + dot * slot + slot / 2
                                var dotY = top + plotHeight * (1 - Number(data[dot][item.key]) / 100)
                                ctx.beginPath(); ctx.arc(dotX, dotY, 2.6, 0, Math.PI * 2); ctx.fill()
                            }
                        }
                    }
                    onWidthChanged: requestPaint()
                    onHeightChanged: requestPaint()
                }

                Row {
                    Layout.alignment: Qt.AlignRight
                    spacing: 11
                    Repeater {
                        model: [
                            {label:"학습시간",color:"#AFC9F4",bar:true},
                            {label:"집중률",color:Theme.success,bar:false},
                            {label:"순공률",color:Theme.primary,bar:false},
                            {label:"이탈률",color:Theme.warning,bar:false}
                        ]
                        delegate: Row {
                            id: legend
                            required property var modelData
                            spacing: 4
                            Rectangle { width: 15; height: legend.modelData.bar ? 8 : 3; radius: 2; color: legend.modelData.color }
                            Text { text: legend.modelData.label; color: Theme.muted; font.pixelSize: 9 }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.preferredWidth: Math.max(280, root.width * 0.29)
            Layout.fillHeight: true
            radius: Theme.radius
            color: Theme.surface
            border.color: Theme.border

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 6
                Text { text: "일별 요약"; color: Theme.text; font.pixelSize: 15; font.weight: Font.Bold }
                RowLayout {
                    Layout.fillWidth: true
                    Text { Layout.preferredWidth: 62; text: "날짜"; color: Theme.muted; font.pixelSize: 9 }
                    Text { Layout.fillWidth: true; text: "학습"; color: Theme.muted; font.pixelSize: 9; horizontalAlignment: Text.AlignRight }
                    Text { Layout.preferredWidth: 46; text: "집중"; color: Theme.muted; font.pixelSize: 9; horizontalAlignment: Text.AlignRight }
                }
                Repeater {
                    model: root.dayData.length > 0 ? root.dayData : root.demoData
                    delegate: Rectangle {
                        id: daySummary
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 38
                        radius: 6
                        color: daySummary.index === 5 ? Theme.primarySoft : Theme.surfaceSoft
                        required property int index
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 9
                            anchors.rightMargin: 9
                            Text { Layout.preferredWidth: 62; text: daySummary.modelData.label; color: Theme.text; font.pixelSize: 10; font.weight: Font.DemiBold }
                            Text { Layout.fillWidth: true; text: root.durationText(daySummary.modelData.study); color: Theme.text; font.pixelSize: 10; horizontalAlignment: Text.AlignRight }
                            Text { Layout.preferredWidth: 46; text: daySummary.modelData.focus + "%"; color: daySummary.modelData.focus >= 80 ? Theme.success : Theme.warning; font.pixelSize: 10; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignRight }
                        }
                    }
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.border }
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "주간 총합"; color: Theme.text; font.pixelSize: 11; font.weight: Font.Bold }
                    Item { Layout.fillWidth: true }
                    Text { text: root.durationText(root.totalStudy()); color: Theme.primary; font.pixelSize: 13; font.weight: Font.Bold }
                }
            }
        }
    }

    onDayDataChanged: weeklyChart.requestPaint()
}
