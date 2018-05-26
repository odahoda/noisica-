#!/usr/bin/python3

# @begin:license
#
# Copyright (c) 2015-2018, Benjamin Niemann <pink@odahoda.de>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# @end:license

import fractions
import logging
from typing import Any, List, Tuple  # pylint: disable=unused-import

from PyQt5.QtCore import Qt
from PyQt5 import QtCore
from PyQt5 import QtGui

from noisicaa.core.typing_extra import down_cast
from noisicaa import audioproc
from noisicaa import core  # pylint: disable=unused-import
from noisicaa import music
from noisicaa.ui import tools
from . import base_track_item

logger = logging.getLogger(__name__)


class EditControlPointsTool(tools.ToolBase):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            type=tools.ToolType.EDIT_CONTROL_POINTS,
            group=tools.ToolGroup.EDIT,
            **kwargs)

        self.__moving_point = None  # type: ControlPoint
        self.__moving_point_original_pos = None  # type: QtCore.QPoint
        self.__moving_point_offset = None  # type: QtCore.QPoint
        self.__move_mode = 'any'
        self.__move_range = None  # type: Tuple[int, int]

    def iconName(self) -> str:
        return 'edit-control-points'

    def mousePressEvent(self, target: Any, evt: QtGui.QMouseEvent) -> None:
        assert isinstance(target, ControlTrackEditorItem), type(target).__name__

        target.updateHighlightedPoint()

        if (evt.button() == Qt.LeftButton
                and evt.modifiers() == Qt.NoModifier
                and target.highlightedPoint() is not None):
            self.__moving_point = target.highlightedPoint()
            self.__moving_point_original_pos = self.__moving_point.pos()
            self.__moving_point_offset = evt.pos() - self.__moving_point.pos()
            self.__move_mode = 'any'

            point_index = self.__moving_point.index

            if point_index > 0:
                range_left = target.points[point_index - 1].pos().x() + 1
            else:
                range_left = 10

            if point_index < len(target.points) - 1:
                range_right = target.points[point_index + 1].pos().x() - 1
            else:
                range_right = target.width() - 11

            self.__move_range = (range_left, range_right)

            evt.accept()
            return

        if (evt.button() == Qt.LeftButton
                and evt.modifiers() == Qt.ShiftModifier
                and target.highlightedPoint() is not None):
            self.send_command_async(music.Command(
                target=target.track.id,
                remove_control_point=music.RemoveControlPoint(
                    point_id=target.highlightedPoint().point_id)))

            evt.accept()
            return

        if evt.button() == Qt.RightButton and self.__moving_point is not None:
            target.setPointPos(self.__moving_point, self.__moving_point_original_pos)
            self.__moving_point = None
            evt.accept()
            return

        super().mousePressEvent(target, evt)

    def mouseMoveEvent(self, target: Any, evt: QtGui.QMouseEvent) -> None:
        assert isinstance(target, ControlTrackEditorItem), type(target).__name__

        if self.__moving_point is not None:
            new_pos = evt.pos() - self.__moving_point_offset

            if evt.modifiers() == Qt.ControlModifier:
                delta = new_pos - self.__moving_point_original_pos
                if self.__move_mode == 'any' and delta.manhattanLength() > 5:
                    if abs(delta.x()) > abs(delta.y()):
                        self.__move_mode = 'horizontal'
                    else:
                        self.__move_mode = 'vertical'
            else:
                self.__move_mode = 'any'

            if self.__move_mode == 'horizontal':
                new_pos.setY(self.__moving_point_original_pos.y())
            elif self.__move_mode == 'vertical':
                new_pos.setX(self.__moving_point_original_pos.x())

            range_left, range_right = self.__move_range
            if new_pos.x() < range_left:
                new_pos.setX(range_left)
            elif new_pos.x() > range_right:
                new_pos.setX(range_right)

            if new_pos.y() < 0:
                new_pos.setY(0)
            elif new_pos.y() > target.height() - 1:
                new_pos.setY(target.height() - 1)

            target.setPointPos(self.__moving_point, new_pos)

            evt.accept()
            return

        target.updateHighlightedPoint()

        super().mouseMoveEvent(target, evt)

    def mouseReleaseEvent(self, target: Any, evt: QtGui.QMouseEvent) -> None:
        assert isinstance(target, ControlTrackEditorItem), type(target).__name__

        if evt.button() == Qt.LeftButton and self.__moving_point is not None:
            pos = self.__moving_point.pos()
            self.__moving_point = None

            if self.__move_mode != 'vertical':
                new_time = target.xToTime(pos.x())
            else:
                new_time = None

            if self.__move_mode != 'horizontal':
                new_value = target.yToValue(pos.y())
            else:
                new_value = None

            self.send_command_async(music.Command(
                target=target.track.id,
                move_control_point=music.MoveControlPoint(
                    point_id=target.highlightedPoint().point_id,
                    time=new_time.to_proto() if new_time is not None else None,
                    value=new_value)))

            evt.accept()
            return

        super().mouseReleaseEvent(target, evt)

    def mouseDoubleClickEvent(self, target: Any, evt: QtGui.QMouseEvent) -> None:
        assert isinstance(target, ControlTrackEditorItem), type(target).__name__

        if evt.button() == Qt.LeftButton and evt.modifiers() == Qt.NoModifier:
            # If the first half of the double click initiated a move,
            # cancel that move now.
            if self.__moving_point is not None:
                target.setPointPos(self.__moving_point, self.__moving_point_original_pos)
                self.__moving_point = None

            time = target.xToTime(evt.pos().x())
            for point in target.track.points:
                if point.time == time:
                    self.send_command_async(music.Command(
                        target=target.track.id,
                        move_control_point=music.MoveControlPoint(
                            point_id=point.id,
                            value=target.yToValue(evt.pos().y()))))
                    break
            else:
                self.send_command_async(music.Command(
                    target=target.track.id,
                    add_control_point=music.AddControlPoint(
                        time=target.xToTime(evt.pos().x()).to_proto(),
                        value=target.yToValue(evt.pos().y()))))

            evt.accept()
            return

        super().mouseDoubleClickEvent(target, evt)


class ControlTrackToolBox(tools.ToolBox):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.addTool(EditControlPointsTool(context=self.context))


class ControlPoint(object):
    def __init__(self, track_item: 'ControlTrackEditorItem', point: music.ControlPoint) -> None:
        self.__track_item = track_item
        self.__point = point

        self.__pos = QtCore.QPoint(
            self.__track_item.timeToX(self.__point.time),
            self.__track_item.valueToY(self.__point.value))

        self.__listeners = [
            self.__point.listeners.add('time', self.onTimeChanged),
            self.__point.listeners.add('value', self.onValueChanged),
        ]

    def close(self) -> None:
        for listener in self.__listeners:
            listener.remove()
        self.__listeners.clear()

    def onTimeChanged(
            self, old_time: audioproc.MusicalTime, new_time: audioproc.MusicalTime) -> None:
        self.__pos = QtCore.QPoint(
            self.__track_item.timeToX(new_time),
            self.__pos.y())
        self.__track_item.rectChanged.emit(self.__track_item.viewRect())

    def onValueChanged(self, old_value: float, new_value: float) -> None:
        self.__pos = QtCore.QPoint(
            self.__pos.x(),
            self.__track_item.valueToY(new_value))
        self.__track_item.rectChanged.emit(self.__track_item.viewRect())

    @property
    def index(self) -> int:
        return self.__point.index

    @property
    def point_id(self) -> int:
        return self.__point.id

    @property
    def time(self) -> audioproc.MusicalTime:
        return self.__point.time

    def pos(self) -> QtCore.QPoint:
        return self.__pos

    def setPos(self, pos: QtCore.QPoint) -> None:
        if pos is None:
            self.__pos = QtCore.QPoint(
                self.__track_item.timeToX(self.__point.time),
                self.__track_item.valueToY(self.__point.value))
        else:
            self.__pos = pos

    def recomputePos(self) -> None:
        self.__pos = QtCore.QPoint(
            self.__track_item.timeToX(self.__point.time),
            self.__track_item.valueToY(self.__point.value))


class ControlTrackEditorItem(base_track_item.BaseTrackEditorItem):
    toolBoxClass = ControlTrackToolBox

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.__mouse_pos = None  # type: QtCore.QPoint
        self.__highlighted_point = None  # type: ControlPoint
        self.__playback_time = None  # type: audioproc.MusicalTime

        self.__listeners = []  # type: List[core.Listener]
        self.points = []  # type: List[ControlPoint]

        for point in self.track.points:
            self.addPoint(len(self.points), point)

        self.__listeners.append(self.track.listeners.add(
            'points', self.onPointsChanged))

        self.updateSize()

        self.scaleXChanged.connect(self.__onScaleXChanged)

    def close(self) -> None:
        for points in self.points:
            points.close()
        self.points.clear()
        super().close()

    def __onScaleXChanged(self, scale_x: fractions.Fraction) -> None:
        for cpoint in self.points:
            cpoint.recomputePos()
        self.rectChanged.emit(self.viewRect())

    def updateSize(self) -> None:
        width = 20
        for mref in self.project.property_track.measure_list:
            measure = mref.measure
            width += int(self.scaleX() * measure.duration.fraction)
        self.setSize(QtCore.QSize(width, 120))

    @property
    def track(self) -> music.ControlTrack:
        return down_cast(music.ControlTrack, super().track)

    def setHighlightedPoint(self, cpoint: ControlPoint) -> None:
        if cpoint is not self.__highlighted_point:
            self.__highlighted_point = cpoint
            self.rectChanged.emit(self.viewRect())

    def highlightedPoint(self) -> ControlPoint:
        return self.__highlighted_point

    def updateHighlightedPoint(self) -> None:
        if self.__mouse_pos is None:
            self.setHighlightedPoint(None)
            return

        closest_cpoint = None
        closest_dist = None
        for cpoint in self.points:
            dist = ((cpoint.pos().x() - self.__mouse_pos.x()) ** 2
                    + (cpoint.pos().y() - self.__mouse_pos.y()) ** 2)
            if dist < 20**2 and (closest_dist is None or dist < closest_dist):
                closest_dist = dist
                closest_cpoint = cpoint

        self.setHighlightedPoint(closest_cpoint)

    def setPointPos(self, cpoint: ControlPoint, pos: QtCore.QPoint) -> None:
        cpoint.setPos(pos)
        self.rectChanged.emit(self.viewRect())

    def addPoint(self, insert_index: int, point: music.ControlPoint) -> None:
        cpoint = ControlPoint(track_item=self, point=point)
        self.points.insert(insert_index, cpoint)
        self.rectChanged.emit(self.viewRect())

    def removePoint(self, remove_index: int, point: QtCore.QPoint) -> None:
        cpoint = self.points.pop(remove_index)
        cpoint.close()
        self.rectChanged.emit(self.viewRect())

    def onPointsChanged(self, action: str, *args: Any) -> None:
        if action == 'insert':
            insert_index, point = args
            self.addPoint(insert_index, point)
            self.updateHighlightedPoint()

        elif action == 'delete':
            remove_index, point = args
            self.removePoint(remove_index, point)
            self.updateHighlightedPoint()

        else:
            raise ValueError("Unknown action %r" % action)

    def setPlaybackPos(self, time: audioproc.MusicalTime) -> None:
        if self.__playback_time is not None:
            x = self.timeToX(self.__playback_time)
            self.rectChanged.emit(
                QtCore.QRect(self.viewLeft() + x, self.viewTop(), 2, self.height()))

        self.__playback_time = time

        if self.__playback_time is not None:
            x = self.timeToX(self.__playback_time)
            self.rectChanged.emit(
                QtCore.QRect(self.viewLeft() + x, self.viewTop(), 2, self.height()))

    def valueToY(self, value: float) -> int:
        return int(self.height() - int(self.height() * value))

    def yToValue(self, y: int) -> float:
        return float(self.height() - y) / self.height()

    def timeToX(self, time: audioproc.MusicalTime) -> int:
        x = 10
        for mref in self.project.property_track.measure_list:
            measure = mref.measure
            width = int(self.scaleX() * measure.duration.fraction)

            if time - measure.duration <= audioproc.MusicalTime(0, 1):
                return x + int(width * (time / measure.duration).fraction)

            x += width
            time -= measure.duration

        return x

    def xToTime(self, x: int) -> audioproc.MusicalTime:
        x -= 10
        time = audioproc.MusicalTime(0, 1)
        if x <= 0:
            return time

        for mref in self.project.property_track.measure_list:
            measure = mref.measure
            width = int(self.scaleX() * measure.duration.fraction)

            if x <= width:
                return audioproc.MusicalTime(
                    time + measure.duration * fractions.Fraction(int(x), width))

            time += measure.duration
            x -= width

        return time

    def leaveEvent(self, evt: QtCore.QEvent) -> None:
        self.__mouse_pos = None
        self.setHighlightedPoint(None)
        super().leaveEvent(evt)

    def mousePressEvent(self, evt: QtGui.QMouseEvent) -> None:
        self.__mouse_pos = evt.pos()
        super().mousePressEvent(evt)

    def mouseMoveEvent(self, evt: QtGui.QMouseEvent) -> None:
        self.__mouse_pos = evt.pos()
        super().mouseMoveEvent(evt)

    def mouseReleaseEvent(self, evt: QtGui.QMouseEvent) -> None:
        self.__mouse_pos = evt.pos()
        super().mouseReleaseEvent(evt)

    def mouseDoubleClickEvent(self, evt: QtGui.QMouseEvent) -> None:
        self.__mouse_pos = evt.pos()
        super().mouseDoubleClickEvent(evt)

    def paint(self, painter: QtGui.QPainter, paint_rect: QtCore.QRect) -> None:
        super().paint(painter, paint_rect)

        x = 10
        for mref in self.project.property_track.measure_list:
            measure = down_cast(music.PropertyMeasure, mref.measure)
            width = int(self.scaleX() * measure.duration.fraction)

            if x + width > paint_rect.x() and x < paint_rect.x() + paint_rect.width():
                if mref.is_first:
                    painter.fillRect(x, 0, 2, self.height(), QtGui.QColor(160, 160, 160))
                else:
                    painter.fillRect(x, 0, 1, self.height(), QtGui.QColor(160, 160, 160))

                for i in range(1, measure.time_signature.upper):
                    pos = int(width * i / measure.time_signature.lower)
                    painter.fillRect(x + pos, 0, 1, self.height(), QtGui.QColor(200, 200, 200))

            x += width

        painter.fillRect(x - 2, 0, 2, self.height(), QtGui.QColor(160, 160, 160))

        points = self.points[:]

        px, py = None, None  # type: int, int
        for cpoint in points:
            x = cpoint.pos().x()
            y = cpoint.pos().y()

            if px is not None:
                painter.setPen(Qt.black)
                painter.drawLine(px, py, x, y)

            px, py = x, y

        for cpoint in points:
            x = cpoint.pos().x()
            y = cpoint.pos().y()

            if cpoint is self.__highlighted_point:
                painter.setPen(Qt.black)
                painter.drawLine(x - 4, y - 4, x + 4, y - 4)
                painter.drawLine(x + 4, y - 4, x + 4, y + 4)
                painter.drawLine(x + 4, y + 4, x - 4, y + 4)
                painter.drawLine(x - 4, y + 4, x - 4, y - 4)
                painter.fillRect(x - 3, y - 3, 7, 7, QtGui.QColor(160, 160, 255))
            else:
                painter.setPen(Qt.black)
                painter.drawLine(x - 3, y - 3, x + 3, y - 3)
                painter.drawLine(x + 3, y - 3, x + 3, y + 3)
                painter.drawLine(x + 3, y + 3, x - 3, y + 3)
                painter.drawLine(x - 3, y + 3, x - 3, y - 3)

        if self.__playback_time is not None:
            pos = self.timeToX(self.__playback_time)
            painter.fillRect(pos, 0, 2, self.height(), QtGui.QColor(0, 0, 160))
