import os
import sys
import time

from .preflight import preflight
from sglib.log import LOG, setup_logging
from sglib.lib.translate import _
from sglib.lib import util
from sgui import (
    shared as glbl_shared,
    project as project_mod,
    widgets,
)
from sgui.main import main as main_window_open
from sgui import sgqt
from sgui.sgqt import (
    create_hintbox,
    QApplication,
    QGuiApplication,
    QMessageBox,
    QStackedWidget,
    QtCore,
    Signal,
)
from sgui.splash import SplashScreen
from sgui.util import setup_theme, ui_scaler_factory
from sgui.welcome import Welcome


class MainStackedWidget(QStackedWidget):
    resized = Signal()

    def __init__(self, *args, **kwargs):
        QStackedWidget.__init__(self, *args, **kwargs)
        self.setObjectName('main_window')
        self.main_window = None
        self.welcome_window = None
        self.splash_screen = None
        self.hardware_dialog = None
        self.next = None
        self.previous = None

    def toggle_full_screen(self):
        fs = self.isFullScreen()
        if fs:
            self.showMaximized()
        else:
            self.showFullScreen()

    def show_main(self):
        if not self.show_splash():
            return
        self.main_window = main_window_open(
            self.splash_screen,
            project_mod.PROJECT_DIR,
        )
        self.addWidget(self.main_window)
        self.setCurrentWidget(self.main_window)

    def show_welcome(self):
        if not self.welcome_window:
            self.welcome_window = Welcome()
            self.addWidget(self.welcome_window.widget)
        self.setCurrentWidget(self.welcome_window.widget)
        self.welcome_window.load_rp()
        self.setWindowTitle('Stargate DAW')

    def start(self):
        if self.show_splash():
            self.show_main()

    def check_hardware(self, _next=None):
        hardware_dialog = widgets.HardwareDialog()
        result = hardware_dialog.check_device()
        if result:
            self.show_hardware_dialog(
                _next if _next else self.show_welcome,
                self.show_welcome,
                result,
            )
            return False
        return True

    def show_splash(self):
        if not self.splash_screen:
            self.splash_screen = SplashScreen(self)
            self.addWidget(self.splash_screen)
        self.setCurrentWidget(self.splash_screen)
        return True

    def show_hardware_dialog(
        self,
        _next,
        previous,
        msg=None,
    ):
        """
        @_next:
            The MainStackedWidget.show_*() method to call upon success
        @_previous:
            The MainStackedWidget.show_*() method to call if the user cancels
        """
        self.next = _next
        self.previous = previous
        if self.hardware_dialog:
            self.removeWidget(self.hardware_dialog)
        hardware_dialog = widgets.HardwareDialog()
        self.hardware_dialog = hardware_dialog.hardware_dialog_factory(msg)
        self.addWidget(self.hardware_dialog)
        self.setCurrentWidget(self.hardware_dialog)

    def closeEvent(self, event):
        self.raise_()
        if glbl_shared.IGNORE_CLOSE_EVENT:
            if sgqt.DIALOG_SHOWING:
                event.ignore()
                LOG.info(
                    "User tried to close the window while a dialog is open"
                )
                return
            event.ignore()
            if glbl_shared.IS_PLAYING:
                LOG.info("User tried to close the window during playback")
                return
            glbl_shared.MAIN_WINDOW.setEnabled(False)
            def _cancel():
                glbl_shared.MAIN_WINDOW.setEnabled(True)
            def _yes():
                glbl_shared.MAIN_WINDOW.prepare_to_quit()
                glbl_shared.IGNORE_CLOSE_EVENT = False
                self.close()
            f_reply = QMessageBox.question(
                self,
                _('Message'),
                _("Are you sure you want to close Stargate DAW?"),
                (
                    QMessageBox.StandardButton.Yes
                    |
                    QMessageBox.StandardButton.Cancel
                ),
                QMessageBox.StandardButton.Cancel,
                callbacks={
                    QMessageBox.StandardButton.Yes: _yes,
                    QMessageBox.StandardButton.Cancel: _cancel,
                },
            )
        else:
            event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resized.emit()

def qt_message_handler(mode, context, message):
    line = (
        f'qt_message_handler: {mode} '
        f'{context.file}:{context.line}:{context.function}'
        f' "{message}"'
    )
    try:
        if mode == QtCore.QtMsgType.QtWarningMsg:
            LOG.warning(line)
        elif mode in (
            QtCore.QtMsgType.QtCriticalMsg,
            QtCore.QtMsgType.QtFatalMsg,
        ):
            LOG.error(line)
        else:
            LOG.info(line)
    except Exception as ex:
        LOG.warning(f'Could not log Qt message: {ex}')


def _setup():
    setup_logging()
    LOG.info(f"sys.argv == {sys.argv}")
    QtCore.qInstallMessageHandler(qt_message_handler)
    try:
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough,
        )
    except Exception as ex:
        LOG.warning(
            "Unable to set "
            "QGuiApplication.setHighDpiScaleFactorRoundingPolicy"
            f" {ex}"
        )
    app = QApplication(sys.argv)
    setup_theme(app)
    create_hintbox()
    return app

def main(args):
    if 'APPDIR' in os.environ:
        LD_LIBRARY_PATH = os.environ.get('LD_LIBRARY_PATH', None)
        LOG.info(f'LD_LIBRARY_PATH={LD_LIBRARY_PATH}')
    global QAPP
    QAPP = _setup()
    QAPP.restoreOverrideCursor()
    from sglib.constants import UI_PIDFILE
    from sglib.lib.pidfile import check_pidfile, create_pidfile
    pid = check_pidfile(UI_PIDFILE)
    if pid is not None:
        msg = (
            f"Detected Stargate is already running with pid {pid}, "
            "please close the other instance first"
        )
        QMessageBox.warning(None, "Error", msg)
        LOG.error(msg)
        sys.exit(0)
    create_pidfile(UI_PIDFILE)
    glbl_shared.MAIN_STACKED_WIDGET = MainStackedWidget()
    glbl_shared.MAIN_STACKED_WIDGET.setMinimumSize(1280, 700)
    glbl_shared.MAIN_STACKED_WIDGET.showMaximized()
    preflight()
    if args.project_file:
        glbl_shared.MAIN_STACKED_WIDGET.start()
    else:
        glbl_shared.MAIN_STACKED_WIDGET.show_welcome()
    exit_code = QAPP.exec()
    #quit_timer = QtCore.QTimer(self)
    #quit_timer.setSingleShot(True)
    #quit_timer.timeout.connect(self.close)
    #quit_timer.start(1000)
    time.sleep(0.3)
    from sgui import main
    main.flush_events()
    LOG.info("Calling os._exit()")
    os.remove(UI_PIDFILE)
    # Work around PyQt SEGFAULT-on-exit issues
    os._exit(exit_code)

