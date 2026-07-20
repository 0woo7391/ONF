import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import ".."
import "../components"

Item {
    id: root
    objectName: "settingsPage"
    signal feedbackRequested(string message)

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            Text { text: "설정"; color: Theme.text; font.pixelSize: 20; font.weight: Font.Bold }
            Item { Layout.fillWidth: true }
            Text { text: "변경한 값은 다음 실행에도 유지됩니다."; color: Theme.muted; font.pixelSize: 10 }
            ActionButton { text: "저장"; tone: "primary"; onClicked: root.feedbackRequested("설정을 저장했습니다.") }
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                width: parent.width
                spacing: 10

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 190
                    radius: Theme.radius
                    color: Theme.surface
                    border.color: Theme.border
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 10
                        Text { text: "카메라와 측정"; color: Theme.text; font.pixelSize: 16; font.weight: Font.Bold }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 18
                            ColumnLayout {
                                Layout.fillWidth: true
                                Text { text: "카메라"; color: Theme.muted; font.pixelSize: 10 }
                                RowLayout {
                                    Layout.fillWidth: true
                                    ComboBox { Layout.fillWidth: true; model: ["Camo Camera", "Integrated Camera", "USB Camera"]; implicitHeight: 40 }
                                    ActionButton { text: "새로고침"; onClicked: root.feedbackRequested("카메라 목록을 새로고침했습니다.") }
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                Text { text: "학습 방식"; color: Theme.muted; font.pixelSize: 10 }
                                ComboBox { Layout.fillWidth: true; model: ["화면 작업", "화면 + 필기"]; implicitHeight: 40 }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                Text { text: "판정 민감도"; color: Theme.muted; font.pixelSize: 10 }
                                ComboBox { Layout.fillWidth: true; model: ["관대함", "보통", "민감함"]; currentIndex: 1; implicitHeight: 40 }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Rectangle { Layout.preferredWidth: 9; Layout.preferredHeight: 9; radius: 5; color: Theme.success }
                            Text { text: "Camo Camera 연결됨"; color: Theme.text; font.pixelSize: 11; font.weight: Font.DemiBold }
                            Item { Layout.fillWidth: true }
                            Text { text: "카메라 화면 숨김 시에도 분석 유지"; color: Theme.muted; font.pixelSize: 10 }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 230
                    radius: Theme.radius
                    color: Theme.surface
                    border.color: Theme.border
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 10
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "집중 알림"; color: Theme.text; font.pixelSize: 16; font.weight: Font.Bold }
                            Item { Layout.fillWidth: true }
                            Switch { checked: true; text: "사용" }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            ColumnLayout {
                                Layout.fillWidth: true
                                Text { text: "주의 이탈 알림"; color: Theme.muted; font.pixelSize: 10 }
                                RowLayout {
                                    ValueStepper { value: 60; minimumValue: 10; maximumValue: 300; suffix: "초" }
                                    Text { text: "지속 시 알림"; color: Theme.muted; font.pixelSize: 10 }
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                Text { text: "알림음"; color: Theme.muted; font.pixelSize: 10 }
                                ComboBox { Layout.fillWidth: true; model: ["선명한 알림", "부드러운 알림", "짧은 벨", "집중 경고"]; implicitHeight: 40 }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "볼륨"; color: Theme.muted; font.pixelSize: 10 }
                            Slider { id: volumeSlider; Layout.fillWidth: true; from: 0; to: 100; value: 65 }
                            TextField { Layout.preferredWidth: 58; text: Math.round(volumeSlider.value) + "%"; horizontalAlignment: Text.AlignHCenter; readOnly: true }
                            ActionButton { text: "테스트"; onClicked: root.feedbackRequested("알림음 65%") }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 180
                    radius: Theme.radius
                    color: Theme.surface
                    border.color: Theme.border
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 12
                        Text { text: "뽀모도로 기본값"; color: Theme.text; font.pixelSize: 16; font.weight: Font.Bold }
                        RowLayout {
                            Layout.fillWidth: true
                            Repeater {
                                model: [{label:"집중",value:25,suffix:"분"},{label:"짧은 휴식",value:5,suffix:"분"},{label:"긴 휴식",value:15,suffix:"분"},{label:"반복",value:4,suffix:"회"}]
                                delegate: ColumnLayout {
                                    id: pomodoroDefault
                                    required property var modelData
                                    Layout.fillWidth: true
                                    Text { text: pomodoroDefault.modelData.label; color: Theme.muted; font.pixelSize: 10 }
                                    ValueStepper { value: pomodoroDefault.modelData.value; suffix: pomodoroDefault.modelData.suffix; minimumValue: 1; maximumValue: 120 }
                                }
                            }
                        }
                        Text { text: "학습 화면에서 세션별로 다시 조정할 수 있습니다."; color: Theme.muted; font.pixelSize: 10 }
                    }
                }
            }
        }
    }
}
