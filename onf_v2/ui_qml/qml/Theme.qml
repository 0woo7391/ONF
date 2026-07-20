pragma Singleton
import QtQuick

QtObject {
    readonly property color background: "#F4F7FA"
    readonly property color surface: "#FFFFFF"
    readonly property color surfaceSoft: "#F8FAFC"
    readonly property color text: "#191F28"
    readonly property color muted: "#6B7684"
    readonly property color border: "#E3E8EF"
    readonly property color primary: "#2563EB"
    readonly property color primarySoft: "#EAF2FF"
    readonly property color success: "#00B84A"
    readonly property color successSoft: "#EAF9F0"
    readonly property color warning: "#F59E0B"
    readonly property color warningSoft: "#FFF7E6"
    readonly property color danger: "#F04452"
    readonly property color dangerSoft: "#FFF1F2"

    readonly property int radiusSmall: 4
    readonly property int radius: 7
    readonly property int fast: 110
    readonly property int normal: 190
}
