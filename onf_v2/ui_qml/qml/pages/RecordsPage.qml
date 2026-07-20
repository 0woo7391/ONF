pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import ".."
import "../components"

Item {
    id: root
    objectName: "recordsPage"
    property int periodIndex: 1
    signal feedbackRequested(string message)

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            Text { text: "학습 기록"; color: Theme.text; font.pixelSize: 20; font.weight: Font.Bold }
            Item { Layout.fillWidth: true }
            ActionButton { text: "‹"; onClicked: root.feedbackRequested("이전 기간") }
            Rectangle {
                Layout.preferredWidth: 230
                Layout.preferredHeight: 42
                radius: Theme.radius
                color: Theme.surface
                border.color: Theme.border
                Text {
                    anchors.centerIn: parent
                    text: root.periodIndex === 0 ? "2026년 7월 20일" : root.periodIndex === 1 ? "2026년 7월 20일 ~ 7월 26일" : "2026년 7월"
                    color: Theme.text
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                }
            }
            ActionButton { text: "›"; onClicked: root.feedbackRequested("다음 기간") }
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
                        Text { text: "오늘 한눈에"; color: Theme.text; font.pixelSize: 16; font.weight: Font.Bold }
                        Item {
                            Layout.alignment: Qt.AlignHCenter
                            Layout.preferredWidth: 210
                            Layout.preferredHeight: 210
                            Canvas {
                                anchors.fill: parent
                                onPaint: {
                                    var ctx = getContext("2d"); ctx.reset(); var cx=width/2; var cy=height/2; var r=78
                                    ctx.lineWidth=24; ctx.strokeStyle=Theme.border; ctx.beginPath(); ctx.arc(cx,cy,r,0,Math.PI*2); ctx.stroke()
                                    ctx.strokeStyle=Theme.success; ctx.lineCap="round"; ctx.beginPath(); ctx.arc(cx,cy,r,-Math.PI/2,-Math.PI/2+Math.PI*2*.82); ctx.stroke()
                                }
                            }
                            Column { anchors.centerIn: parent; Text { anchors.horizontalCenter: parent.horizontalCenter; text: "82%"; color: Theme.text; font.pixelSize: 38; font.weight: Font.Bold } Text { anchors.horizontalCenter: parent.horizontalCenter; text: "집중률"; color: Theme.muted; font.pixelSize: 11 } }
                        }
                        GridLayout {
                            Layout.fillWidth: true
                            columns: 2
                            Repeater {
                                model: [{l:"공부시간",v:"4시간 32분"},{l:"순공시간",v:"3시간 42분"},{l:"이탈시간",v:"38분"},{l:"최장 집중",v:"54분"}]
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
                        Rectangle { Layout.fillWidth: true; Layout.fillHeight: true; radius: Theme.radius; color: Theme.surfaceSoft; StudyTimeline { anchors.fill: parent; anchors.margins: 18; currentHour: 12; currentMinute: 40 } }
                    }
                }
            }
        }

        WeeklyRecordCharts {
            visible: root.periodIndex === 1
            Layout.fillWidth: true
            Layout.fillHeight: true
        }

        Rectangle {
            visible: root.periodIndex === 2
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: Theme.radius
            color: Theme.surface
            border.color: Theme.border
            MonthlyHeatmap { anchors.fill: parent; anchors.margins: 22 }
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
                Text { text: root.periodIndex === 0 ? "오늘 4회 학습 · 순공 3시간 42분" : root.periodIndex === 1 ? "이번 주 27회 학습 · 평균 집중률 81%" : "7월 19일 학습 · 총 46시간 20분"; color: Theme.muted; font.pixelSize: 11 }
                Item { Layout.fillWidth: true }
                ActionButton { text: "세션 기록 보기"; onClicked: root.feedbackRequested("세션 기록") }
            }
        }
    }
}
