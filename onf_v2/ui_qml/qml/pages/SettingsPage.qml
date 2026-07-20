pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import ".."
import "../components"

Item {
    id: root
    objectName: "settingsPage"
    property var backendObject: null
    readonly property var storedSettings: backendObject ? backendObject.settings : ({})
    property int focusDefaultValue: storedSettings.pomodoro_focus_minutes || 25
    property int shortBreakDefaultValue: storedSettings.pomodoro_short_break_minutes || 5
    property int longBreakDefaultValue: storedSettings.pomodoro_long_break_minutes || 15
    property int cycleDefaultValue: storedSettings.pomodoro_cycles || 4
    signal feedbackRequested(string message)

    function saveValues() {
        if (backendObject) {
            backendObject.saveSettings({
                camera_index: cameraCombo.currentIndex,
                work_mode: workModeCombo.currentIndex === 1 ? "screen_writing" : "screen",
                mode: ["weak", "normal", "strong"][sensitivityCombo.currentIndex],
                sound_enabled: soundSwitch.checked,
                attention_alert_seconds: alertDelay.value,
                alert_sound: ["impact", "chime", "digital", "soft"][soundCombo.currentIndex],
                alert_volume: Math.round(volumeSlider.value),
                pomodoro_focus_minutes: focusDefaultValue,
                pomodoro_short_break_minutes: shortBreakDefaultValue,
                pomodoro_long_break_minutes: longBreakDefaultValue,
                pomodoro_cycles: cycleDefaultValue
            })
        }
        feedbackRequested("설정을 저장했습니다.")
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            Text { text: "설정"; color: Theme.text; font.pixelSize: 20; font.weight: Font.Bold }
            Item { Layout.fillWidth: true }
            Text { text: "변경한 값은 다음 실행에도 유지됩니다."; color: Theme.muted; font.pixelSize: 10 }
            ActionButton { text: "저장"; tone: "primary"; onClicked: root.saveValues() }
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
                                    ComboBox { id: cameraCombo; Layout.fillWidth: true; model: ["Camera 0", "Camera 1", "Camera 2", "Camera 3"]; currentIndex: root.storedSettings.camera_index || 0; implicitHeight: 40 }
                                    ActionButton { text: "새로고침"; onClicked: root.feedbackRequested("카메라 목록을 새로고침했습니다.") }
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                Text { text: "학습 방식"; color: Theme.muted; font.pixelSize: 10 }
                                ComboBox { id: workModeCombo; Layout.fillWidth: true; model: ["화면 작업", "화면 + 필기"]; currentIndex: root.storedSettings.work_mode === "screen_writing" ? 1 : 0; implicitHeight: 40 }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                Text { text: "판정 민감도"; color: Theme.muted; font.pixelSize: 10 }
                                ComboBox { id: sensitivityCombo; Layout.fillWidth: true; model: ["관대함", "보통", "민감함"]; currentIndex: root.storedSettings.mode === "weak" ? 0 : root.storedSettings.mode === "strong" ? 2 : 1; implicitHeight: 40 }
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
                            Switch { id: soundSwitch; checked: root.storedSettings.sound_enabled === undefined ? true : root.storedSettings.sound_enabled; text: "사용" }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            ColumnLayout {
                                Layout.fillWidth: true
                                Text { text: "주의 이탈 알림"; color: Theme.muted; font.pixelSize: 10 }
                                RowLayout {
                                    ValueStepper { id: alertDelay; value: root.storedSettings.attention_alert_seconds || 60; minimumValue: 10; maximumValue: 300; suffix: "초" }
                                    Text { text: "지속 시 알림"; color: Theme.muted; font.pixelSize: 10 }
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                Text { text: "알림음"; color: Theme.muted; font.pixelSize: 10 }
                                ComboBox { id: soundCombo; Layout.fillWidth: true; model: ["강한 경고", "선명한 벨", "디지털 알림", "부드러운 알림"]; currentIndex: Math.max(0, ["impact", "chime", "digital", "soft"].indexOf(root.storedSettings.alert_sound)); implicitHeight: 40 }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "볼륨"; color: Theme.muted; font.pixelSize: 10 }
                            Slider { id: volumeSlider; Layout.fillWidth: true; from: 0; to: 100; value: root.storedSettings.alert_volume === undefined ? 65 : root.storedSettings.alert_volume }
                            TextField { Layout.preferredWidth: 58; text: Math.round(volumeSlider.value) + "%"; horizontalAlignment: Text.AlignHCenter; readOnly: true }
                            ActionButton {
                                text: "테스트"
                                onClicked: {
                                    if (root.backendObject)
                                        root.backendObject.testAlert(Math.round(volumeSlider.value), ["impact", "chime", "digital", "soft"][soundCombo.currentIndex])
                                    root.feedbackRequested("알림음 " + Math.round(volumeSlider.value) + "%")
                                }
                            }
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
                                    required property int index
                                    Layout.fillWidth: true
                                    Text { text: pomodoroDefault.modelData.label; color: Theme.muted; font.pixelSize: 10 }
                                    ValueStepper {
                                        id: defaultStepper
                                        value: pomodoroDefault.index === 0 ? root.focusDefaultValue : pomodoroDefault.index === 1 ? root.shortBreakDefaultValue : pomodoroDefault.index === 2 ? root.longBreakDefaultValue : root.cycleDefaultValue
                                        suffix: pomodoroDefault.modelData.suffix
                                        minimumValue: 1
                                        maximumValue: 120
                                        onValueChanged: {
                                            if (pomodoroDefault.index === 0) root.focusDefaultValue = value
                                            else if (pomodoroDefault.index === 1) root.shortBreakDefaultValue = value
                                            else if (pomodoroDefault.index === 2) root.longBreakDefaultValue = value
                                            else root.cycleDefaultValue = value
                                        }
                                    }
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
