pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import ".."
import "../components"

Item {
    id: root
    objectName: "plannerPage"
    property var backendObject: null
    signal feedbackRequested(string message)

    ListModel {
        id: planModel
        ListElement { taskId: -1; taskState: 0; title: "영어 독해 지문 2개"; start: "09:00"; end: "09:45"; duration: "45분" }
        ListElement { taskId: -2; taskState: 1; title: "수학 오답노트 정리"; start: "11:00"; end: ""; duration: "60분" }
        ListElement { taskId: -3; taskState: 2; title: "한국사 4강 복습"; start: ""; end: ""; duration: "30분" }
        ListElement { taskId: -4; taskState: 0; title: "과학 개념 문제 20개"; start: "20:00"; end: "21:00"; duration: "60분" }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            Text { text: "오늘의 학습 계획"; color: Theme.text; font.pixelSize: 20; font.weight: Font.Bold }
            Item { Layout.fillWidth: true }
            ActionButton { text: "‹"; onClicked: { if (root.backendObject) root.backendObject.shiftPlannerDate(-1); root.feedbackRequested("이전 날짜") } }
            Rectangle {
                Layout.preferredWidth: 190
                Layout.preferredHeight: 42
                radius: Theme.radius
                color: Theme.surface
                border.color: Theme.border
                Text { anchors.centerIn: parent; text: root.backendObject ? root.backendObject.plannerDayLabel : "2026년 7월 20일"; color: Theme.text; font.pixelSize: 13; font.weight: Font.DemiBold }
            }
            ActionButton { text: "›"; onClicked: { if (root.backendObject) root.backendObject.shiftPlannerDate(1); root.feedbackRequested("다음 날짜") } }
            Rectangle {
                Layout.preferredWidth: 88
                Layout.preferredHeight: 42
                radius: Theme.radius
                color: Theme.dangerSoft
                Column {
                    anchors.centerIn: parent
                    spacing: 1
                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: "D-148"; color: Theme.danger; font.pixelSize: 14; font.weight: Font.Bold }
                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: "시험"; color: Theme.muted; font.pixelSize: 9 }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumWidth: 560
                radius: Theme.radius
                color: Theme.surface
                border.color: Theme.border

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 9

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 7
                        TextField {
                            id: taskInput
                            Layout.fillWidth: true
                            implicitHeight: 40
                            placeholderText: "오늘 할 공부를 입력하세요"
                            onAccepted: addButton.clicked()
                        }
                        TextField { id: startInput; Layout.preferredWidth: 72; implicitHeight: 40; placeholderText: "시작"; inputMask: "99:99" }
                        TextField { id: endInput; Layout.preferredWidth: 72; implicitHeight: 40; placeholderText: "종료"; inputMask: "99:99" }
                        TextField { id: durationInput; Layout.preferredWidth: 72; implicitHeight: 40; placeholderText: "_분" }
                        ActionButton {
                            id: addButton
                            text: "+"
                            tone: "primary"
                            onClicked: {
                                if (taskInput.text.trim() === "") {
                                    root.feedbackRequested("할 일을 입력하세요.")
                                    return
                                }
                                if (root.backendObject) {
                                    if (!root.backendObject.addPlannerTask(taskInput.text, startInput.text, endInput.text, durationInput.text)) {
                                        root.feedbackRequested("계획을 추가하지 못했습니다.")
                                        return
                                    }
                                } else {
                                    planModel.append({taskId: -(planModel.count + 10), taskState: 0, title: taskInput.text, start: startInput.text, end: endInput.text, duration: durationInput.text})
                                }
                                taskInput.clear(); startInput.clear(); endInput.clear(); durationInput.clear()
                                root.feedbackRequested("계획을 추가했습니다.")
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text { Layout.preferredWidth: 34; text: "상태"; color: Theme.muted; font.pixelSize: 10 }
                        Text { Layout.fillWidth: true; text: "할 일"; color: Theme.muted; font.pixelSize: 10 }
                        Text { Layout.preferredWidth: 72; text: "시작"; color: Theme.muted; font.pixelSize: 10 }
                        Text { Layout.preferredWidth: 72; text: "종료"; color: Theme.muted; font.pixelSize: 10 }
                        Text { Layout.preferredWidth: 72; text: "예상"; color: Theme.muted; font.pixelSize: 10 }
                        Item { Layout.preferredWidth: 34 }
                    }

                    ListView {
                        id: planList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 6
                        clip: true
                        model: root.backendObject ? root.backendObject.plannerTasks : planModel
                        delegate: Rectangle {
                            id: planRow
                            required property int index
                            required property int taskId
                            required property int taskState
                            required property string title
                            required property string start
                            required property string end
                            required property string duration
                            width: planList.width
                            height: 52
                            radius: Theme.radius
                            color: planRow.taskState === 1 ? Theme.successSoft : planRow.taskState === 2 ? Theme.warningSoft : Theme.surfaceSoft
                            border.color: Theme.border

                            function commit() {
                                if (root.backendObject) {
                                    root.backendObject.updatePlannerTask(planRow.taskId, titleEdit.text, startEdit.text, endEdit.text, durationEdit.text)
                                } else {
                                    planModel.setProperty(planRow.index, "title", titleEdit.text)
                                    planModel.setProperty(planRow.index, "start", startEdit.text)
                                    planModel.setProperty(planRow.index, "end", endEdit.text)
                                    planModel.setProperty(planRow.index, "duration", durationEdit.text)
                                }
                            }

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 7
                                anchors.rightMargin: 7
                                spacing: 7

                                Button {
                                    id: stateButton
                                    Layout.preferredWidth: 30
                                    Layout.preferredHeight: 30
                                    text: planRow.taskState === 1 ? "✓" : planRow.taskState === 2 ? "Ⅱ" : "○"
                                    ToolTip.visible: hovered
                                    ToolTip.text: planRow.taskState === 0 ? "완료로 변경" : planRow.taskState === 1 ? "보류로 변경" : "공란으로 변경"
                                    onClicked: {
                                        if (root.backendObject)
                                            root.backendObject.cyclePlannerTask(planRow.taskId)
                                        else
                                            planModel.setProperty(planRow.index, "taskState", (planRow.taskState + 1) % 3)
                                    }
                                    background: Rectangle { radius: 6; color: planRow.taskState === 1 ? Theme.success : planRow.taskState === 2 ? Theme.warning : Theme.surface; border.color: planRow.taskState === 0 ? "#B8C0CB" : "transparent" }
                                    contentItem: Text { text: stateButton.text; color: planRow.taskState === 0 ? Theme.muted : "white"; font.pixelSize: 13; font.weight: Font.Bold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                }

                                TextField {
                                    id: titleEdit
                                    Layout.fillWidth: true
                                    text: planRow.title
                                    font.pixelSize: 12
                                    selectByMouse: true
                                    background: Item {}
                                    onEditingFinished: planRow.commit()
                                }
                                TextField {
                                    id: startEdit
                                    Layout.preferredWidth: 72
                                    text: planRow.start
                                    placeholderText: "--:--"
                                    horizontalAlignment: Text.AlignHCenter
                                    background: Item {}
                                    onEditingFinished: planRow.commit()
                                }
                                TextField {
                                    id: endEdit
                                    Layout.preferredWidth: 72
                                    text: planRow.end
                                    placeholderText: "--:--"
                                    horizontalAlignment: Text.AlignHCenter
                                    background: Item {}
                                    onEditingFinished: planRow.commit()
                                }
                                TextField {
                                    id: durationEdit
                                    Layout.preferredWidth: 72
                                    text: planRow.duration
                                    placeholderText: "--분"
                                    horizontalAlignment: Text.AlignHCenter
                                    background: Item {}
                                    onEditingFinished: planRow.commit()
                                }
                                Button {
                                    id: deleteButton
                                    Layout.preferredWidth: 30
                                    Layout.preferredHeight: 30
                                    text: "×"
                                    onClicked: {
                                        if (root.backendObject)
                                            root.backendObject.deletePlannerTask(planRow.taskId)
                                        else
                                            planModel.remove(planRow.index)
                                        root.feedbackRequested("계획을 삭제했습니다.")
                                    }
                                    background: Rectangle { radius: 6; color: deleteButton.hovered ? Theme.dangerSoft : "transparent" }
                                    contentItem: Text { text: deleteButton.text; color: Theme.danger; font.pixelSize: 18; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "○ 공란"; color: Theme.muted; font.pixelSize: 10 }
                        Text { text: "✓ 완료"; color: Theme.success; font.pixelSize: 10 }
                        Text { text: "Ⅱ 보류"; color: Theme.warning; font.pixelSize: 10 }
                        Item { Layout.fillWidth: true }
                        Text { text: "시간은 선택 입력"; color: Theme.muted; font.pixelSize: 10 }
                    }
                }
            }

            Rectangle {
                Layout.preferredWidth: Math.max(350, root.width * 0.34)
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
                        Text { text: "실제 학습 타임라인"; color: Theme.text; font.pixelSize: 15; font.weight: Font.Bold }
                        Item { Layout.fillWidth: true }
                        Text { text: "순공 3시간 42분"; color: Theme.success; font.pixelSize: 11; font.weight: Font.DemiBold }
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: Theme.radius
                        color: Theme.surfaceSoft
                        DailyPlannerTimeline { anchors.fill: parent; anchors.margins: 12 }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Rectangle { Layout.preferredWidth: 24; Layout.preferredHeight: 8; radius: 2; color: Theme.success }
                        Text { text: "실제 집중도"; color: Theme.muted; font.pixelSize: 9 }
                        Item { Layout.fillWidth: true }
                        Text { text: "점선 계획 · 실선 완료"; color: Theme.muted; font.pixelSize: 9 }
                    }
                }
            }
        }
    }
}
