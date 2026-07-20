pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import ".."

Item {
    id: root
    property var levels: [0,1,2,3,2,0,1, 1,2,4,3,2,1,0, 2,3,4,4,3,2,1, 0,1,3,4,2,1,0, 1,2,2]
    property var summary: ({study:"46시간 20분",focus:"38시간 12분",ratio:82,days:19,longest:"8일"})
    property string monthLabel: "7월"

    ColumnLayout {
        anchors.fill: parent
        spacing: 16
        RowLayout {
            Layout.fillWidth: true
            Column {
                Text { text: root.monthLabel + " 학습 잔디"; color: Theme.text; font.pixelSize: 16; font.weight: Font.Bold }
                Text { text: root.summary.days + "일 학습 · " + root.summary.study; color: Theme.muted; font.pixelSize: 11 }
            }
            Item { Layout.fillWidth: true }
            Text { text: "최장 연속 " + root.summary.longest; color: Theme.success; font.pixelSize: 12; font.weight: Font.DemiBold }
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 22

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 8

                GridLayout {
                    Layout.fillWidth: true
                    columns: 7
                    columnSpacing: 8
                    Repeater {
                        model: ["일", "월", "화", "수", "목", "금", "토"]
                        delegate: Text {
                            id: weekdayLabel
                            required property string modelData
                            Layout.fillWidth: true
                            text: weekdayLabel.modelData
                            color: Theme.muted
                            font.pixelSize: 10
                            font.weight: Font.DemiBold
                            horizontalAlignment: Text.AlignHCenter
                        }
                    }
                }

                GridLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    columns: 7
                    columnSpacing: 8
                    rowSpacing: 8
                    Repeater {
                        model: 31
                        delegate: Rectangle {
                            id: dayCell
                            required property int index
                            property int level: root.levels[index] || 0
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: 48
                            radius: 6
                            color: level === 0 ? "#EEF1F4" : level === 1 ? "#CFF3DC" : level === 2 ? "#91DEAC" : level === 3 ? "#3CCB70" : "#00A843"
                            Text { anchors.centerIn: parent; text: dayCell.index + 1; color: dayCell.level >= 3 ? "white" : Theme.muted; font.pixelSize: 11; font.weight: Font.DemiBold }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillHeight: true
                Layout.preferredWidth: 1
                color: Theme.border
            }

            ColumnLayout {
                Layout.preferredWidth: 260
                Layout.fillHeight: true
                spacing: 16

                Text { text: "이번 달 한눈에"; color: Theme.text; font.pixelSize: 14; font.weight: Font.Bold }
                Repeater {
                    model: [
                        {label: "총 공부시간", value: root.summary.study},
                        {label: "순공시간", value: root.summary.focus},
                        {label: "평균 집중률", value: root.summary.ratio + "%"},
                        {label: "학습한 날", value: root.summary.days + "일"}
                    ]
                    delegate: RowLayout {
                        id: monthMetric
                        required property var modelData
                        Layout.fillWidth: true
                        Text { text: monthMetric.modelData.label; color: Theme.muted; font.pixelSize: 11 }
                        Item { Layout.fillWidth: true }
                        Text { text: monthMetric.modelData.value; color: Theme.text; font.pixelSize: 14; font.weight: Font.DemiBold }
                    }
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.border }
                Text { text: "주차별 순공시간"; color: Theme.text; font.pixelSize: 12; font.weight: Font.DemiBold }
                Repeater {
                    model: [
                        {label: "1주", value: 0.64, time: "7시간 10분"},
                        {label: "2주", value: 0.82, time: "9시간 14분"},
                        {label: "3주", value: 1.0, time: "11시간 18분"},
                        {label: "4주", value: 0.71, time: "8시간 02분"}
                    ]
                    delegate: ColumnLayout {
                        id: weeklyMetric
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: 4
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: weeklyMetric.modelData.label; color: Theme.muted; font.pixelSize: 10 }
                            Item { Layout.fillWidth: true }
                            Text { text: weeklyMetric.modelData.time; color: Theme.text; font.pixelSize: 10; font.weight: Font.DemiBold }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 7
                            radius: 4
                            color: Theme.surfaceSoft
                            Rectangle {
                                width: parent.width * weeklyMetric.modelData.value
                                height: parent.height
                                radius: parent.radius
                                color: Theme.success
                            }
                        }
                    }
                }
                Item { Layout.fillHeight: true }
                Row {
                    Layout.alignment: Qt.AlignRight
                    spacing: 5
                    Text { text: "적게"; color: Theme.muted; font.pixelSize: 9 }
                    Repeater {
                        model: ["#EEF1F4", "#CFF3DC", "#91DEAC", "#3CCB70", "#00A843"]
                        delegate: Rectangle { required property string modelData; width: 16; height: 16; radius: 4; color: modelData }
                    }
                    Text { text: "많이"; color: Theme.muted; font.pixelSize: 9 }
                }
            }
        }
    }
}
