import asyncio
import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QTableWidgetItem
from qasync import QEventLoop, asyncSlot

from mtu_tool import MtuTool
from ui.main import Ui_MainWindow


class MainWindow(Ui_MainWindow):
    def __init__(self):
        self.main_window = QMainWindow()
        self.setupUi(self.main_window)

        self.pushButton_run.clicked.connect(self.run_clicked)

        self.headers = ['Buffer', 'Packet', 'Info']
        self.clear_table()

        self.mtu_tool = MtuTool('', 0, 0, self.main_window.statusBar().showMessage)

    def show(self):
        self.main_window.show()

    def add_row(self, row: dict):
        row_count = self.tableWidget.rowCount()
        self.tableWidget.setRowCount(row_count + 1)
        item = None
        for key, value in row.items():
            item = QTableWidgetItem(str(value))
            self.tableWidget.setItem(row_count, self.headers.index(key), item)
        self.tableWidget.scrollToItem(item)

    def clear_table(self):
        self.tableWidget.clear()
        self.tableWidget.setColumnCount(0)
        self.tableWidget.setRowCount(0)
        self.tableWidget.setColumnCount(len(self.headers))
        self.tableWidget.setHorizontalHeaderLabels(self.headers)

    @asyncSlot()
    async def run_clicked(self):
        if self.mtu_tool.set_stop_scan():
            return
        self.pushButton_run.setText('Cancel')
        self.main_window.statusBar().clearMessage()
        self.clear_table()
        self.mtu_tool.host = self.comboBox_host.currentText()
        self.mtu_tool.range_start = int(self.lineEdit_start.text())
        self.mtu_tool.range_stop = int(self.lineEdit_end.text())
        self.mtu_tool.timeout = int(self.lineEdit_timeout.text())
        check_function = self.mtu_tool.check_fast if self.checkBox_fast.isChecked() else self.mtu_tool.check_range
        async for row in check_function():
            self.add_row(row)
        self.tableWidget.resizeColumnsToContents()
        self.pushButton_run.setText('Run')


async def main(app):
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)
    main_window = MainWindow()
    main_window.show()
    await app_close_event.wait()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    asyncio.run(main(app), loop_factory=QEventLoop)
