from .gui import *

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        try:
            app.setStyleSheet(APP_STYLESHEET)
        except Exception:
            pass
        mainwin = MainWindow()
        mainwin.show()
        app.exec_()
    except Exception:
        logger.exception("GUI Crash!")

