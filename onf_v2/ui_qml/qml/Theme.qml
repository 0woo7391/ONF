pragma Singleton
import QtQuick

QtObject {
    readonly property color background: StudyStyle.background
    readonly property color surface: "#FFFFFF"
    readonly property color surfaceSoft: StudyStyle.field
    readonly property color text: StudyStyle.ink
    readonly property color muted: StudyStyle.muted
    readonly property color border: StudyStyle.line
    readonly property color primary: StudyStyle.accent
    readonly property color primarySoft: StudyStyle.wash
    readonly property color success: StudyStyle.success
    readonly property color successSoft: "#EAF9F0"
    readonly property color warning: StudyStyle.warning
    readonly property color warningSoft: "#FFF7E6"
    readonly property color danger: StudyStyle.danger
    readonly property color dangerSoft: "#FFF1F2"

    readonly property int radiusSmall: 4
    readonly property int radius: 7
    readonly property int fast: StudyStyle.fast
    readonly property int normal: StudyStyle.normal
}
