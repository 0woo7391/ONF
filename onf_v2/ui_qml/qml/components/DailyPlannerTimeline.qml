import QtQuick
import QtQuick.Controls.Basic
import ".."

Flickable {
    id: root
    clip: true
    contentWidth: width
    contentHeight: 620
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

    function focusColor(value) {
        if (value < 55) return Theme.danger
        if (value < 78) return Theme.warning
        return Theme.success
    }

    Canvas {
        width: root.width
        height: root.contentHeight
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var startHour = 6
            var rows = 18
            var columns = 6
            var labelWidth = 34
            var rowHeight = 33
            var cellWidth = (width - labelWidth - 8) / columns
            var actual = [
                {row:3,col:0,span:3,values:[84,91,78],label:"영어"},
                {row:5,col:0,span:4,values:[72,79,88,86],label:"수학"},
                {row:8,col:2,span:3,values:[64,75,82],label:"한국사"},
                {row:14,col:0,span:5,values:[88,92,85,76,81],label:"과학"}
            ]
            ctx.font = "9px Segoe UI"
            ctx.textBaseline = "middle"
            for (var row=0; row<rows; row++) {
                var y=row*rowHeight
                var hour=(startHour+row)%24
                ctx.fillStyle=Theme.muted
                ctx.fillText((hour<10?"0":"")+hour,2,y+rowHeight/2)
                for(var col=0;col<columns;col++){
                    var x=labelWidth+col*cellWidth
                    ctx.fillStyle="#FAFBFC";ctx.fillRect(x+1,y+1,cellWidth-2,rowHeight-2)
                    ctx.strokeStyle=Theme.border;ctx.lineWidth=.7;ctx.strokeRect(x+1,y+1,cellWidth-2,rowHeight-2)
                }
            }
            function plan(row,col,span,label,complete){
                var x=labelWidth+col*cellWidth+2;var y=row*rowHeight+3
                ctx.strokeStyle=complete?Theme.primary:"#7DA7E8";ctx.lineWidth=complete?2.4:1.3
                ctx.setLineDash(complete?[]:[4,3]);ctx.strokeRect(x,y,cellWidth*span-4,rowHeight-6);ctx.setLineDash([])
                ctx.fillStyle=Theme.primary;ctx.font="8px Segoe UI";ctx.fillText(label,x+4,y+(rowHeight-6)/2)
            }
            plan(3,0,4,"영어 독해",true)
            plan(5,0,6,"수학 오답",true)
            plan(8,2,3,"한국사",false)
            plan(14,0,6,"과학 문제",false)
            for(var i=0;i<actual.length;i++){
                var item=actual[i]
                for(var j=0;j<item.span;j++){
                    ctx.fillStyle=root.focusColor(item.values[j]);ctx.globalAlpha=.78
                    ctx.fillRect(labelWidth+(item.col+j)*cellWidth+3,item.row*rowHeight+5,cellWidth-6,rowHeight-10)
                }
            }
            ctx.globalAlpha=1
        }
    }
}
