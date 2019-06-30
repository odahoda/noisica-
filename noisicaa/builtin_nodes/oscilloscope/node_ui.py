#!/usr/bin/python3

# @begin:license
#
# Copyright (c) 2015-2019, Benjamin Niemann <pink@odahoda.de>
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

import logging
from typing import Any, Dict, List, Tuple, Iterable

from PyQt5.QtCore import Qt
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

from noisicaa import core
from noisicaa import music
from noisicaa.ui import slots
from noisicaa.ui import ui_base
from noisicaa.ui.graph import base_node
from . import model

logger = logging.getLogger(__name__)


class Oscilloscope(slots.SlotContainer, QtWidgets.QWidget):
    timeScale, setTimeScale, timeScaleChanged = slots.slot(int, 'timeScale', default=-2)
    yScale, setYScale, yScaleChanged = slots.slot(int, 'yScale', default=0)
    yOffset, setYOffset, yOffsetChanged = slots.slot(float, 'yOffset', default=0.0)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.setMinimumSize(60, 60)

        self.__signal = []  # type: List[Tuple[int, float]]
        self.__insert_pos = 0
        self.__screen_pos = 0
        self.__remainder = 0.0
        self.__hold = False
        self.__prev_sample = 0.0

        self.__timePerPixel = 1.0
        self.__timePerSample = 1.0 / 44100

        self.__bg_color = QtGui.QColor(0, 0, 0)
        self.__border_color = QtGui.QColor(100, 200, 100)
        self.__grid_color = QtGui.QColor(40, 60, 40)
        self.__center_color = QtGui.QColor(60, 100, 60)
        self.__plot_pen = QtGui.QPen(QtGui.QColor(255, 255, 255))
        self.__plot_pen.setWidth(1)
        self.__label_color = QtGui.QColor(100, 160, 100)
        self.__label_font = QtGui.QFont(self.font())
        self.__label_font.setPointSizeF(0.8 * self.__label_font.pointSizeF())
        self.__label_font_metrics = QtGui.QFontMetrics(self.__label_font)

        self.__update_timer = QtCore.QTimer(self)
        self.__update_timer.timeout.connect(self.update)
        self.__update_timer.setInterval(1000 // 20)

        self.timeScaleChanged.connect(self.__timeScaleChanged)
        self.__timeScaleChanged(self.timeScale())

    def __timeScaleChanged(self, value: int) -> None:
        w = self.width() - 10
        if w > 0:
            self.__timePerPixel = [1, 2, 5][value % 3] * 10.0 ** (value // 3) / w
            self.__hold = True

        else:
            self.__timePerPixel = 1.0

    def addValues(self, values: Iterable[float]) -> None:
        for value in values:
            if self.__hold:
                if self.__prev_sample < 0.0 and value >= 0.0:
                    self.__hold = False
                    self.__insert_pos = 0
                    self.__screen_pos = 0
                    self.__remainder = 0.0

            self.__prev_sample = value

            if self.__hold:
                continue

            if self.__timePerPixel >= self.__timePerSample:
                self.__remainder += self.__timePerSample
                if self.__remainder >= 0.0:
                    self.__remainder -= self.__timePerPixel

                    self.__signal.insert(self.__insert_pos, (self.__screen_pos, value))
                    self.__insert_pos += 1

                    while (self.__insert_pos < len(self.__signal)
                           and self.__signal[self.__insert_pos][0] <= self.__screen_pos):
                        del self.__signal[self.__insert_pos]

                    self.__screen_pos += 1

            else:
                self.__signal.insert(self.__insert_pos, (self.__screen_pos, value))
                self.__insert_pos += 1

                while (self.__insert_pos < len(self.__signal)
                       and self.__signal[self.__insert_pos][0] <= self.__screen_pos):
                    del self.__signal[self.__insert_pos]

                self.__remainder += self.__timePerSample
                while self.__remainder >= 0.0:
                    self.__remainder -= self.__timePerPixel
                    self.__screen_pos += 1

            if self.__screen_pos >= self.width() - 10:
                self.__hold = True
                del self.__signal[self.__insert_pos:]

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(100, 100)

    def showEvent(self, evt: QtGui.QShowEvent) -> None:
        self.__update_timer.start()
        super().showEvent(evt)

    def hideEvent(self, evt: QtGui.QHideEvent) -> None:
        self.__update_timer.stop()
        super().hideEvent(evt)

    def paintEvent(self, evt: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        try:
            painter.fillRect(evt.rect(), self.__bg_color)

            w = self.width() - 10
            h = self.height() - 10

            for g in (1, 2, 3, 4, 6, 7, 8, 9, 5, 0, 10):
                if g in (0, 10):
                    color = self.__border_color
                elif g == 5:
                    color = self.__center_color
                else:
                    color = self.__grid_color

                painter.fillRect(int(g * (w - 1) / 10) + 5, 5, 1, h, color)
                painter.fillRect(5, int(g * (h - 1) / 10) + 5, w, 1, color)

            painter.setFont(self.__label_font)
            painter.setPen(self.__label_color)

            time_scale = self.timeScale()
            mul = [1, 2, 5][time_scale % 3]
            time_scale //= 3
            if time_scale <= -4:
                t1 = '%dµs' % (mul * 10 ** (time_scale + 6))
            elif time_scale <= -1:
                t1 = '%dms' % (mul * 10 ** (time_scale + 3))
            else:
                t1 = '%ds' % (mul * 10 ** time_scale)

            t1r = self.__label_font_metrics.boundingRect(t1)
            painter.drawText(
                w + 5 - t1r.width() - 2,
                int(5 * (h - 1) / 10) + 5 + self.__label_font_metrics.capHeight() + 2,
                t1)

            y_scale = [1, 2, 5][self.yScale() % 3] * 10.0 ** (self.yScale() // 3)
            y1 = '%g' % y_scale
            painter.drawText(
                7,
                7 + self.__label_font_metrics.capHeight(),
                y1)

            path = QtGui.QPolygon()
            for x, value in self.__signal:
                if x >= w:
                    break

                value /= y_scale
                value += self.yOffset()
                y = h - int((h - 1) * (value + 1.0) / 2.0)
                path.append(QtCore.QPoint(x + 5, y + 5))

            painter.setPen(self.__plot_pen)
            painter.drawPolyline(path)

        finally:
            painter.end()


class OscilloscopeNodeWidget(ui_base.ProjectMixin, core.AutoCleanupMixin, QtWidgets.QWidget):
    def __init__(self, node: model.Oscilloscope, session_prefix: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.__node = node

        self.__listeners = core.ListenerMap[str]()
        self.add_cleanup_function(self.__listeners.cleanup)

        self.__listeners['node-messages'] = self.audioproc_client.node_messages.add(
            '%016x' % self.__node.id, self.__nodeMessage)

        self.__plot = Oscilloscope()

        self.__time_scale = QtWidgets.QSpinBox()
        self.__time_scale.setRange(-12, 3)
        self.__time_scale.valueChanged.connect(self.__plot.setTimeScale)
        self.__time_scale.setValue(-5)

        self.__y_scale = QtWidgets.QSpinBox()
        self.__y_scale.setRange(-18, 18)
        self.__y_scale.valueChanged.connect(self.__plot.setYScale)
        self.__y_scale.setValue(1)

        self.__y_offset = QtWidgets.QDoubleSpinBox()
        self.__y_offset.setRange(-1.0, 1.0)
        self.__y_offset.setDecimals(2)
        self.__y_offset.setSingleStep(0.05)
        self.__y_offset.valueChanged.connect(self.__plot.setYOffset)
        self.__y_offset.setValue(0.0)

        l2 = QtWidgets.QFormLayout()
        l2.setContentsMargins(0, 0, 0, 0)
        l2.addRow('Time scale:', self.__time_scale)
        l2.addRow('Y scale:', self.__y_scale)
        l2.addRow('Y offset:', self.__y_offset)

        l1 = QtWidgets.QHBoxLayout()
        l1.setContentsMargins(0, 0, 0, 0)
        l1.addLayout(l2)
        l1.addWidget(self.__plot, 1)
        self.setLayout(l1)


    def __nodeMessage(self, msg: Dict[str, Any]) -> None:
        signal_uri = 'http://noisicaa.odahoda.de/lv2/processor_oscilloscope#signal'
        if signal_uri in msg:
            signal = msg[signal_uri]
            self.__plot.addValues(signal)


class OscilloscopeNode(base_node.Node):
    has_window = True

    def __init__(self, *, node: music.BaseNode, **kwargs: Any) -> None:
        assert isinstance(node, model.Oscilloscope), type(node).__name__
        self.__widget = None  # type: QtWidgets.QWidget
        self.__node = node  # type: model.Oscilloscope

        super().__init__(node=node, **kwargs)

    def createBodyWidget(self) -> QtWidgets.QWidget:
        assert self.__widget is None

        body = OscilloscopeNodeWidget(
            node=self.__node,
            session_prefix='inline',
            context=self.context)
        self.add_cleanup_function(body.cleanup)
        body.setAutoFillBackground(False)
        body.setAttribute(Qt.WA_NoSystemBackground, True)

        self.__widget = QtWidgets.QScrollArea()
        self.__widget.setWidgetResizable(True)
        self.__widget.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.__widget.setWidget(body)

        return self.__widget

    def createWindow(self, **kwargs: Any) -> QtWidgets.QWidget:
        window = QtWidgets.QDialog(**kwargs)
        window.setAttribute(Qt.WA_DeleteOnClose, False)
        window.setWindowTitle("Oscilloscope")

        body = OscilloscopeNodeWidget(
            node=self.__node,
            session_prefix='window',
            context=self.context)
        self.add_cleanup_function(body.cleanup)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(body)
        window.setLayout(layout)

        return window
