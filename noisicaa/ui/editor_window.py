#!/usr/bin/python3

# Still need to figure out how to pass around the app reference, disable
# message "Access to a protected member .. of a client class"
# pylint: disable=W0212

import logging
import textwrap
import pprint
import os.path
import enum

from PyQt5.QtCore import Qt, QSize, pyqtSignal, pyqtProperty
from PyQt5.QtGui import QPalette, QColor, QBrush, QIcon, QPixmap, QPainter, QFont
from PyQt5.QtWidgets import (
    QAction,
    QFrame,
    QMessageBox,
    QMainWindow,
    QDockWidget,
    QWidget,
    QTabWidget,
    QStackedWidget,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsRectItem,
    QHBoxLayout,
    QVBoxLayout,
    QFileDialog,
    QToolBar,
    QStatusBar,
    QLineEdit,
    QToolButton,
    QButtonGroup,
)
from PyQt5.QtGui import QKeySequence

from noisicaa import music
from ..instr.library import InstrumentLibrary
from ..exceptions import RestartAppException, RestartAppCleanException
from ..ui_state import UpdateUIState
from .command_shell import CommandShell
from .settings import SettingsDialog
from .project_view import ProjectView
from .instrument_library import InstrumentLibraryDialog
from .flowlayout import FlowLayout
from ..constants import DATA_DIR
from .dock_widget import DockWidget
from .tool_dock import ToolsDockWidget
from .tracks_dock import TracksDockWidget
from .track_properties_dock import TrackPropertiesDockWidget
from ..importers.abc import ABCImporter, ImporterError
from .load_history import LoadHistoryWidget

logger = logging.getLogger(__name__)


class CommandShellDockWidget(DockWidget):
    def __init__(self, parent):
        super().__init__(
            parent=parent,
            identifier='command_shell',
            title="Command Shell",
            allowed_areas=Qt.AllDockWidgetAreas,
            initial_area=Qt.BottomDockWidgetArea,
            initial_visible=False)
        command_shell = CommandShell(parent=self)
        self.setWidget(command_shell)


class EditorWindow(QMainWindow):
    # Could not figure out how to define a signal that takes either an instance
    # of a specific class or None.
    currentProjectChanged = pyqtSignal(object)
    currentSheetChanged = pyqtSignal(object)
    currentTrackChanged = pyqtSignal(object)

    def __init__(self, app):
        super().__init__()

        self._app = app

        self._docks = []
        self._settings_dialog = SettingsDialog(self)

        # self._instrument_library_dialog = InstrumentLibraryDialog(
        #     self, self._app, self._app.instrument_library)

        self._current_project_view = None

        self.setWindowTitle("noisicaä")
        self.resize(800, 600)

        self.createActions()
        self.createMenus()
        self.createToolBar()
        self.createStatusBar()
        self.createDockWidgets()

        self._project_tabs = QTabWidget(self)
        self._project_tabs.setUsesScrollButtons(True)
        self._project_tabs.setTabsClosable(True)
        self._project_tabs.setMovable(True)
        self._project_tabs.setDocumentMode(True)
        self._project_tabs.tabCloseRequested.connect(self.onCloseProjectTab)
        self._project_tabs.currentChanged.connect(self.onCurrentProjectTabChanged)

        self._start_view = self.createStartView()

        self._main_area = QStackedWidget(self)
        self._main_area.addWidget(self._project_tabs)
        self._main_area.addWidget(self._start_view)
        self._main_area.setCurrentIndex(1)
        self.setCentralWidget(self._main_area)

        self.restoreGeometry(
            self._app.settings.value('mainwindow/geometry', b''))
        self.restoreState(
            self._app.settings.value('mainwindow/state', b''))

    def createStartView(self):
        view = QWidget(self)

        gscene = QGraphicsScene()
        gscene.addText("Some fancy logo goes here")

        gview = QGraphicsView(self)
        gview.setBackgroundRole(QPalette.Window)
        gview.setFrameShape(QFrame.NoFrame)
        gview.setBackgroundBrush(QBrush(Qt.NoBrush))
        gview.setScene(gscene)

        layout = QVBoxLayout()
        layout.addWidget(gview)
        view.setLayout(layout)

        return view

    def createActions(self):
        self._new_project_action = QAction(
            "New", self,
            shortcut=QKeySequence.New,
            statusTip="Create a new project",
            triggered=self.onNewProject)

        self._open_project_action = QAction(
            "Open", self,
            shortcut=QKeySequence.Open,
            statusTip="Open an existing project",
            triggered=self.onOpenProject)

        self._import_action = QAction(
            "Import", self,
            statusTip="Import a file into the current project.",
            triggered=self.onImport)

        self._render_action = QAction(
            "Render", self,
            statusTip="Render sheet into an audio file.",
            triggered=self.onRender)

        self._save_project_action = QAction(
            "Save", self,
            shortcut=QKeySequence.Save,
            statusTip="Save the current project",
            triggered=self.onSaveProject)

        self._close_current_project_action = QAction(
            "Close", self,
            shortcut=QKeySequence.Close,
            statusTip="Close the current project",
            triggered=self.onCloseCurrentProjectTab,
            enabled=False)

        self._restart_action = QAction(
            "Restart", self,
            shortcut="F5", shortcutContext=Qt.ApplicationShortcut,
            statusTip="Restart the application", triggered=self.restart)

        self._restart_clean_action = QAction(
            "Restart clean", self,
            shortcut="Ctrl+Shift+F5", shortcutContext=Qt.ApplicationShortcut,
            statusTip="Restart the application in a clean state",
            triggered=self.restart_clean)

        self._quit_action = QAction(
            "Quit", self,
            shortcut=QKeySequence.Quit, shortcutContext=Qt.ApplicationShortcut,
            statusTip="Quit the application", triggered=self.quit)

        self._crash_action = QAction(
            "Crash", self,
            triggered=self.crash)

        self._dump_project_action = QAction(
            "Dump Project", self,
            triggered=self.dumpProject)

        self._dump_pipeline_action = QAction(
            "Dump Player Pipeline", self,
            triggered=self.dumpPipeline)

        self._about_action = QAction(
            "About", self,
            statusTip="Show the application's About box",
            triggered=self.about)

        self._aboutqt_action = QAction(
            "About Qt", self,
            statusTip="Show the Qt library's About box",
            triggered=self._app.aboutQt)

        self._open_settings_action = QAction(
            "Settings", self,
            statusTip="Open the settings dialog.",
            triggered=self.openSettings)

        self._open_instrument_library_action = QAction(
            "Instrument Library", self,
            statusTip="Open the instrument library dialog.",
            triggered=self.openInstrumentLibrary)

        self._add_score_track_action = QAction(
            "Score", self,
            statusTip="Add a new score track to the current sheet.",
            triggered=self.onAddScoreTrack,
            enabled=False)

        self._player_start_action = QAction(
            QIcon.fromTheme('media-playback-start'),
            "Play",
            self, triggered=self.onPlayerStart)
        self._player_pause_action = QAction(
            QIcon.fromTheme('media-playback-pause'),
            "Pause",
            self, triggered=self.onPlayerPause)
        self._player_stop_action = QAction(
            QIcon.fromTheme('media-playback-stop'),
            "Stop",
            self, triggered=self.onPlayerStop)

    def createMenus(self):
        menu_bar = self.menuBar()

        self._project_menu = menu_bar.addMenu("Project")
        self._project_menu.addAction(self._new_project_action)
        self._project_menu.addAction(self._open_project_action)
        self._project_menu.addAction(self._save_project_action)
        self._project_menu.addAction(self._close_current_project_action)
        self._project_menu.addSeparator()
        self._project_menu.addAction(self._import_action)
        self._project_menu.addAction(self._render_action)
        self._project_menu.addSeparator()
        self._project_menu.addAction(self._open_instrument_library_action)
        self._project_menu.addSeparator()
        self._project_menu.addAction(self._open_settings_action)
        self._project_menu.addSeparator()
        self._project_menu.addAction(self._quit_action)

        self._edit_menu = menu_bar.addMenu("Edit")
        add_track_menu = self._edit_menu.addMenu("Add Track")
        add_track_menu.addAction(self._add_score_track_action)

        self._view_menu = menu_bar.addMenu("View")

        if self._app.runtime_settings.dev_mode:
            menu_bar.addSeparator()
            self._dev_menu = menu_bar.addMenu("Dev")
            self._dev_menu.addAction(self._dump_project_action)
            self._dev_menu.addAction(self._dump_pipeline_action)
            self._dev_menu.addAction(self._restart_action)
            self._dev_menu.addAction(self._restart_clean_action)
            self._dev_menu.addAction(self._crash_action)
            self._dev_menu.addAction(self._app.show_edit_areas_action)

        menu_bar.addSeparator()

        self._help_menu = menu_bar.addMenu("Help")
        self._help_menu.addAction(self._about_action)
        self._help_menu.addAction(self._aboutqt_action)

    def createToolBar(self):
        self.toolbar = QToolBar()
        self.toolbar.setObjectName('toolbar:main')
        self.toolbar.addAction(self._player_start_action)
        #elf.toolbar.addAction(self._player_pause_action)
        self.toolbar.addAction(self._player_stop_action)

        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

    def createStatusBar(self):
        self.statusbar = QStatusBar()

        self.player_status = LoadHistoryWidget(100, 30)
        self.player_status.setToolTip("Load of the playback engine.")
        self.statusbar.addPermanentWidget(self.player_status)

        self.setStatusBar(self.statusbar)

    def createDockWidgets(self):
        self.tools_dock = ToolsDockWidget(self)
        self._docks.append(self.tools_dock)

        self._tracks_dock = TracksDockWidget(self)
        self._docks.append(self._tracks_dock)

        self._track_properties_dock = TrackPropertiesDockWidget(self)
        self._docks.append(self._track_properties_dock)

        self._docks.append(CommandShellDockWidget(self))

    def storeState(self):
        logger.info("Saving current EditorWindow geometry.")
        self._app.settings.setValue('mainwindow/geometry', self.saveGeometry())
        self._app.settings.setValue('mainwindow/state', self.saveState())

        self._settings_dialog.storeState()

    def setInfoMessage(self, msg):
        self.statusbar.showMessage(msg)

    def updateView(self):
        for idx in range(self._project_tabs.count()):
            project_view = self._project_tabs.widget(idx)
            project_view.updateView()

    def about(self):
        QMessageBox.about(
            self, "About noisicaä",
            textwrap.dedent("""\
                Some text goes here...
                """))

    def crash(self):
        raise RuntimeError("Something bad happened")

    def dumpProject(self):
        if self._project_tabs.count() > 0:
            project = self.getCurrentProject()
            logger.info('Project dump:\n%s', pprint.pformat(project.serialize()))

    def dumpPipeline(self):
        self._app.pipeline.dump()

    def restart(self):
        raise RestartAppException("Restart requested by user.")

    def restart_clean(self):
        raise RestartAppCleanException("Clean restart requested by user.")

    def quit(self):
        self._app.quit()

    def openSettings(self):
        self._settings_dialog.show()
        self._settings_dialog.activateWindow()

    def openInstrumentLibrary(self):
        self._app.instrument_library.dispatch_command(
            '/ui_state',
            UpdateUIState(visible=True))

    def closeEvent(self, event):
        logger.info("CloseEvent received")
        event.ignore()
        self._app.quit()
        return

        for idx in range(self._project_tabs.count()):
            view = self._project_tabs.widget(idx)
            closed = view.close()
            if not closed:
                event.ignore()
                return
            self._project_tabs.removeTab(idx)

        event.accept()
        self._app.quit()

    def closeAll(self):
        while self._project_tabs.count() > 0:
            view = self._project_tabs.widget(0)
            view.close()
            self._project_tabs.removeTab(0)
        self._settings_dialog.close()
        self.close()

    def setCurrentProjectView(self, project_view):
        if project_view == self._current_project_view:
            return

        if self._current_project_view is not None:
            self._current_project_view.currentSheetChanged.disconnect(
                self.currentSheetChanged)

        if project_view is not None:
            project_view.currentSheetChanged.connect(
                self.currentSheetChanged)

        self._current_project_view = project_view

        if project_view is not None:
            self.currentProjectChanged.emit(project_view.project)
            self.currentSheetChanged.emit(project_view.currentSheetView().sheet)
        else:
            self.currentProjectChanged.emit(None)
            self.currentSheetChanged.emit(None)

    def addProjectView(self, project):
        view = ProjectView(self._app, self, project)
        view.setCurrentTool(self.tools_dock.currentTool())
        self.tools_dock.toolChanged.connect(view.setCurrentTool)

        idx = self._project_tabs.addTab(view, project.name)

        self._project_tabs.setCurrentIndex(idx)
        self._close_current_project_action.setEnabled(True)
        self._add_score_track_action.setEnabled(True)
        self._main_area.setCurrentIndex(0)

    def removeProjectView(self, project):
        for idx in range(self._project_tabs.count()):
            view = self._project_tabs.widget(idx)
            if view.project is project:
                self._project_tabs.removeTab(idx)
                if self._project_tabs.count() == 0:
                    self._main_area.setCurrentIndex(1)
                self._close_current_project_action.setEnabled(
                    self._project_tabs.count() > 0)
                self._add_score_track_action.setEnabled(
                    self._project_tabs.count() > 0)
                break
        else:
            raise ValueError("No view for project found.")

    def onCloseCurrentProjectTab(self):
        view = self._project_tabs.currentWidget()
        closed = view.close()
        if closed:
            self._app.removeProject(view.project)

    def onCurrentProjectTabChanged(self, idx):
        project_view = self._project_tabs.widget(idx)
        self.setCurrentProjectView(project_view)

    def onCloseProjectTab(self, idx):
        view = self._project_tabs.widget(idx)
        closed = view.close()
        if closed:
            self._app.removeProject(view.project)

    def getCurrentProject(self):
        view = self._project_tabs.currentWidget()
        return view.project

    def onNewProject(self):
        path, open_filter = QFileDialog.getSaveFileName(
            parent=self,
            caption="Select Project File",
            #directory=self.ui_state.get(
            #    'instruments_add_dialog_path', ''),
            filter="All Files (*);;noisicaä Projects (*.emp)",
            #initialFilter=self.ui_state.get(
            #'instruments_add_dialog_path', ''),
        )
        if not path:
            return

        task = self._app.process.event_loop.create_task(
            self.call_with_exc(self._app.createProject(path)))

    def onOpenProject(self):
        path, open_filter = QFileDialog.getOpenFileName(
            parent=self,
            caption="Open Project",
            #directory=self.ui_state.get(
            #'instruments_add_dialog_path', ''),
            filter="All Files (*);;noisicaä Projects (*.emp)",
            #initialFilter=self.ui_state.get(
            #    'instruments_add_dialog_path', ''),
        )
        if not path:
            return

        self._app.process.event_loop.create_task(
            self.call_with_exc(self._app.openProject(path)))

    async def call_with_exc(self, coroutine):
        try:
            return await coroutine
        except:
            import sys
            sys.excepthook(*sys.exc_info())
        # project = EditorProject(self._app)
        # try:
        #     project.open(path)
        # except music.FileError as exc:
        #     errorbox = QMessageBox()
        #     errorbox.setWindowTitle("Failed to open project")
        #     errorbox.setText("Failed to open project from path %s." % path)
        #     errorbox.setInformativeText(str(exc))
        #     errorbox.setIcon(QMessageBox.Warning)
        #     errorbox.addButton("Close", QMessageBox.AcceptRole)
        #     errorbox.exec_()

        # else:
        #     self._app.addProject(project)

    def onImport(self):
        path, open_filter = QFileDialog.getOpenFileName(
            parent=self,
            caption="Import file",
            #directory=self.ui_state.get(
            #'instruments_add_dialog_path', ''),
            filter="All Files (*);;ABC (*.abc)",
            #initialFilter=self.ui_state.get(
            #    'instruments_add_dialog_path', ''),
        )
        if not path:
            return

        importer = ABCImporter()
        try:
            importer.import_file(path, self.getCurrentProject())
        except ImporterError as exc:
            errorbox = QMessageBox()
            errorbox.setWindowTitle("Failed to import file")
            errorbox.setText("Failed import file from path %s." % path)
            errorbox.setInformativeText(str(exc))
            errorbox.setIcon(QMessageBox.Warning)
            errorbox.addButton("Close", QMessageBox.AcceptRole)
            errorbox.exec_()

    def onRender(self):
        view = self._project_tabs.currentWidget()
        view.onRender()

    def onSaveProject(self):
        project = self.getCurrentProject()
        project.create_checkpoint()

    def onAddScoreTrack(self):
        view = self._project_tabs.currentWidget()
        view.onAddTrack('score')

    def onPlayerStart(self):
        view = self._project_tabs.currentWidget()
        view.onPlayerStart()

    def onPlayerPause(self):
        view = self._project_tabs.currentWidget()
        view.onPlayerPause()

    def onPlayerStop(self):
        view = self._project_tabs.currentWidget()
        view.onPlayerStop()
