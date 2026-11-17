pragma Singleton
import QtQuick

QtObject {
    readonly property color ink: "#20262D"
    readonly property color muted: "#626B75"
    readonly property color line: "#E1E6E9"
    readonly property color accent: "#137B76"
    readonly property color wash: "#EAF5F2"
    readonly property color background: "#FAFBFB"
    readonly property color field: "#F5F7F7"
    readonly property color disabled: "#626B75"
    readonly property color warning: "#946311"
    readonly property color success: "#16834B"
    readonly property color danger: "#C3424E"
    property bool motionEnabled: true
    readonly property int fast: motionEnabled ? 120 : 0
    readonly property int normal: motionEnabled ? 180 : 0
    readonly property string family: regular.name
    property FontLoader regular: FontLoader { source: "assets/fonts/SUIT-Regular.ttf" }
    property FontLoader medium: FontLoader { source: "assets/fonts/SUIT-Medium.ttf" }
    property FontLoader semibold: FontLoader { source: "assets/fonts/SUIT-SemiBold.ttf" }
}
