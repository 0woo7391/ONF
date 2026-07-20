pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import ".."
import "../components"

Item {
    id: root
    objectName: "recordsPage"
    property var backendObject: null
    property int periodIndex: 1
    readonly property var dailyData: backendObject ? backendObject.dailySummary : ({study:"4시간 32분",focus:"3시간 42분",away:"38분",break:"12분",unscored:"4분",ratio:82,longest:"54분"})
    signal feedbackRequested(string message)

    function weeklyTotalMinutes() {
        if (!backendObject) return 1300
        var total = 0
        for (var i = 0; i < backendObject.weeklyRecords.length; i++) total += Number(backendObject.weeklyRecords[i].study)
        return total
    }

    function weeklyFocusRatio() {
        if (!backendObject) return 81
        var weighted = 0
        var total = 0
        for (var i = 0; i < backendObject.weeklyRecords.length; i++) {
            var item = backendObject.weeklyRecords[i]
            weighted += Number(item.study) * Number(item.focus)
            total += Number(item.study)
        }
        return total > 0 ? Math.round(weighted / total) : 0
    }

    function minutesText(minutes) {
        return Math.floor(minutes / 60) + "시간 " + Math.round(minutes % 60) + "분"
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            Text { text: "학습 기록"; color: Theme.text; font.pixelSize: 20; font.weight: Font.Bold }
            Item { Layout.fillWidth: true }
            ActionButton { text: "‹"; onClicked: { if (root.backendObject) root.backendObject.shiftRecords(root.periodIndex, -1); root.feedbackRequested("이전 기간") } }
            Rectangle {
                Layout.preferredWidth: 230
                Layout.preferredHeight: 42
                radius: Theme.radius
                color: Theme.surface
                border.color: Theme.border
                Text {
                    anchors.centerIn: parent
                    text: root.backendObject ? (root.periodIndex === 0 ? root.backendObject.dayLabel : root.periodIndex === 1 ? root.backendObject.weekLabel : root.backendObject.monthLabel) : root.periodIndex === 0 ? "2026년 7월 20일" : root.periodIndex === 1 ? "2026년 7월 20일 ~ 7월 26일" : "2026년 7월"
                    color: Theme.text
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                }
            }
            ActionButton { text: "›"; onClicked: { if (root.backendObject) root.backendObject.shiftRecords(root.periodIndex, 1); root.feedbackRequested("다음 기간") } }
            Row {
                spacing: 4
                Repeater {
                    model: ["일간", "주간", "월간"]
                    delegate: Button {
                        id: periodButton
                        required property int index
                        required property string modelData
                        width: 66
                        height: 38
                        text: modelData
                        onClicked: root.periodIndex = index
                        background: Rectangle { radius: Theme.radius; color: root.periodIndex === periodButton.index ? Theme.primarySoft : Theme.surface; border.color: root.periodIndex === periodButton.index ? "#BFD5FF" : Theme.border }
                        contentItem: Text { text: periodButton.text; color: root.periodIndex === periodButton.index ? Theme.primary : Theme.muted; font.pixelSize: 12; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    }
                }
            }
        }

        Item {
            visible: root.periodIndex === 0
            Layout.fillWidth: true
            Layout.fillHeight: true

            RowLayout {
                anchors.fill: parent
                spacing: 12
                Rectangle {
                    Layout.preferredWidth: 330
                    Layout.fillHeight: true
                    radius: Theme.radius
                    color: Theme.surface
                    border.color: Theme.border
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 12
                        Text { text: "하루 한눈에"; color: Theme.text; font.pixelSize: 16; font.weight: Font.Bold }
                        Item {
                            Layout.alignment: Qt.AlignHCenter
                            Layout.preferredWidth: 210
                            Layout.preferredHeight: 210
                            Canvas {
                                id: dailyDonut
                                anchors.fill: parent
                                onPaint: {
                                    var ctx = getContext("2d"); ctx.reset(); var cx=width/2; var cy=height/2; var r=78
                                    ctx.lineWidth=24; ctx.strokeStyle=Theme.border; ctx.beginPath(); ctx.arc(cx,cy,r,0,Math.PI*2); ctx.stroke()
                                    ctx.strokeStyle=Theme.success; ctx.lineCap="round"; ctx.beginPath(); ctx.arc(cx,cy,r,-Math.PI/2,-Math.PI/2+Math.PI*2*root.dailyData.ratio/100); ctx.stroke()
                                }
                            }
                            Column { anchors.centerIn: parent; Text { anchors.horizontalCenter: parent.horizontalCenter; text: root.dailyData.ratio + "%"; color: Theme.text; font.pixelSize: 38; font.weight: Font.Bold } Text { anchors.horizontalCenter: parent.horizontalCenter; text: "집중률"; color: Theme.muted; font.pixelSize: 11 } }
                        }
                        GridLayout {
                            Layout.fillWidth: true
                            columns: 2
                            Repeater {
                                model: [{l:"공부시간",v:root.dailyData.study},{l:"순공시간",v:root.dailyData.focus},{l:"이탈시간",v:root.dailyData.away},{l:"최장 집중",v:root.dailyData.longest}]
                                delegate: Column { id: dailyMetric; required property var modelData; Layout.fillWidth: true; spacing: 2; Text{text:dailyMetric.modelData.l;color:Theme.muted;font.pixelSize:10} Text{text:dailyMetric.modelData.v;color:Theme.text;font.pixelSize:14;font.weight:Font.DemiBold} }
                            }
                        }
                        Item { Layout.fillHeight: true }
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
                        Text { text: "시간별 학습"; color: Theme.text; font.pixelSize: 16; font.weight: Font.Bold }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: Theme.radius
                            color: Theme.surfaceSoft
                            FullDayTimeline {
                                anchors.fill: parent
                                anchors.margins: 14
                                hourlyData: root.backendObject ? root.backendObject.dailyHourlyData : []
                            }
                        }
                    }
                }
            }
        }

        WeeklyRecordCharts {
            visible: root.periodIndex === 1
            Layout.fillWidth: true
            Layout.fillHeight: true
            dayData: root.backendObject ? root.backendObject.weeklyRecords : []
        }

        Rectangle {
            visible: root.periodIndex === 2
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: Theme.radius
            color: Theme.surface
            border.color: Theme.border
            MonthlyHeatmap {
                anchors.fill: parent
                anchors.margins: 22
                levels: root.backendObject ? root.backendObject.monthlyLevels : [0,1,2,3,2,0,1,1,2,4,3,2,1,0,2,3,4,4,3,2,1,0,1,3,4,2,1,0,1,2,2]
                summary: root.backendObject ? root.backendObject.monthlySummary : ({study:"46시간 20분",focus:"38시간 12분",ratio:82,days:19,longest:"8일"})
                monthLabel: root.backendObject ? root.backendObject.monthLabel : "2026년 7월"
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            radius: Theme.radius
            color: Theme.surface
            border.color: Theme.border
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 14
                anchors.rightMargin: 14
                Text { text: root.periodIndex === 0 ? "선택한 날 · 순공 " + root.dailyData.focus : root.periodIndex === 1 ? "선택한 주 · 총 " + root.minutesText(root.weeklyTotalMinutes()) + " · 평균 집중률 " + root.weeklyFocusRatio() + "%" : "선택한 달 · " + (root.backendObject ? root.backendObject.monthlySummary.days : 19) + "일 학습"; color: Theme.muted; font.pixelSize: 11 }
                Item { Layout.fillWidth: true }
                ActionButton { text: "세션 기록 보기"; onClicked: root.feedbackRequested("세션 기록") }
            }
        }
    }

    onDailyDataChanged: dailyDonut.requestPaint()
}
