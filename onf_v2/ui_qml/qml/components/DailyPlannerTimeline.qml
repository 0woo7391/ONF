import QtQuick
import QtQuick.Controls.Basic
import ".."

Flickable {
    id: root
    objectName: "dailyPlannerTimeline"
    property var plannerTasks: []
    property var hourlyData: []
    property int studyDayStartHour: 0
    clip: true
    contentWidth: width
    contentHeight: 24 * 33
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

    function focusColor(value) {
        if (value < 55) return Theme.danger
        if (value < 78) return Theme.warning
        return Theme.success
    }

    function hourForRow(row) {
        return (studyDayStartHour + row) % 24
    }

    Canvas {
        id: chart
        width: root.width
        height: root.contentHeight
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var startHour = root.studyDayStartHour
            var rows = 24
            var columns = 6
            var labelWidth = 34
            var rowHeight = 33
            var cellWidth = (width - labelWidth - 8) / columns
            ctx.font = "9px Segoe UI"
            ctx.textBaseline = "middle"
            for (var row=0; row<rows; row++) {
                var y=row*rowHeight
                var hour=root.hourForRow(row)
                ctx.fillStyle=Theme.muted
                ctx.fillText((hour<10?"0":"")+hour,2,y+rowHeight/2)
                for(var col=0;col<columns;col++){
                    var x=labelWidth+col*cellWidth
                    ctx.fillStyle="#FAFBFC";ctx.fillRect(x+1,y+1,cellWidth-2,rowHeight-2)
                    ctx.strokeStyle=Theme.border;ctx.lineWidth=.7;ctx.strokeRect(x+1,y+1,cellWidth-2,rowHeight-2)
                }
            }
            for(var dataIndex=0;dataIndex<root.hourlyData.length;dataIndex++){
                var hourly=root.hourlyData[dataIndex]
                var actualRow=(Number(hourly.hour)-startHour+24)%24
                for(var valueIndex=0;valueIndex<Math.min(columns,hourly.values.length);valueIndex++){
                    var focusValue=Number(hourly.values[valueIndex])
                    if(hourly.present ? !hourly.present[valueIndex] : focusValue<=0) continue
                    ctx.fillStyle=root.focusColor(focusValue);ctx.globalAlpha=.86
                    ctx.fillRect(labelWidth+valueIndex*cellWidth+3,actualRow*rowHeight+5,cellWidth-6,rowHeight-10)
                }
            }
            ctx.globalAlpha=1
            function plan(row,col,span,label,complete){
                var x=labelWidth+col*cellWidth+2;var y=row*rowHeight+3
                ctx.strokeStyle=complete?Theme.primary:"#5F8FD8";ctx.lineWidth=complete?2.4:1.5
                ctx.setLineDash(complete?[]:[4,3]);ctx.strokeRect(x,y,cellWidth*span-4,rowHeight-6);ctx.setLineDash([])
                if(label!==""){
                    ctx.fillStyle="#25364D";ctx.font="600 9px Segoe UI";ctx.fillText(label,x+5,y+(rowHeight-6)/2)
                }
            }
            // Derive plan borders from the same tasks shown in the list.
            for(var taskIndex=0;taskIndex<root.plannerTasks.length;taskIndex++){
                var task=root.plannerTasks[taskIndex]
                if(!task.start||task.start.indexOf(":")<0) continue
                var timeParts=task.start.split(":")
                var cursor=Number(timeParts[0])*60+Number(timeParts[1])
                var durationDigits=String(task.duration||"").replace(/[^0-9]/g,"")
                var remaining=durationDigits===""?0:Number(durationDigits)
                if(remaining<=0&&task.end&&task.end.indexOf(":")>=0){
                    var endParts=task.end.split(":")
                    var endMinute=Number(endParts[0])*60+Number(endParts[1])
                    remaining=(endMinute-cursor+24*60)%(24*60)
                }
                cursor=(cursor-startHour*60+24*60)%(24*60)
                var firstSegment=true
                while(remaining>0){
                    var taskRow=Math.floor(cursor/60)
                    if(taskRow<0||taskRow>=rows) break
                    var minuteOffset=cursor%60
                    var segmentMinutes=Math.min(remaining,60-minuteOffset)
                    plan(taskRow,minuteOffset/10,segmentMinutes/10,firstSegment?task.title:"",Number(task.taskState)===1)
                    cursor+=segmentMinutes
                    remaining-=segmentMinutes
                    firstSegment=false
                }
            }
        }
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
    }

    onPlannerTasksChanged: requestTimelinePaint()
    onHourlyDataChanged: requestTimelinePaint()
    onStudyDayStartHourChanged: requestTimelinePaint()
    function requestTimelinePaint() {
        chart.requestPaint()
    }
}
