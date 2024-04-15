import sys
import threading
import time

import qdarktheme
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QTableWidgetItem
from pythonping import ping

from custom_signal_window import CustomSignalWindow
from ui.main import Ui_MainWindow


def ping_socket(target, size, timeout):
    try:
        result = ping(target, size=size, verbose=False, df=True, timeout=int(timeout) / 1000, count=1)
        if result.stats_packets_lost >= 1:
            return -5, 'timeout'
        return result.rtt_avg_ms, f'{result.rtt_avg_ms:.1f}ms'
    except OSError as e:
        if e.winerror == 10040:
            return -2, 'should be fragmented'
        print(e)
    except RuntimeError as e:
        if 'Cannot resolve address' in str(e):
            return -3, 'host not found'
        print(e)
    return -1, 'error'


class MainWindow(Ui_MainWindow):
    def __init__(self):
        self.app = QtWidgets.QApplication(sys.argv)
        self.main_window = CustomSignalWindow()
        self.setupUi(self.main_window)

        self.pushButton_run.clicked.connect(self.run_clicked)

        self.table_set_headers()

        self.thread_running = False
        self.thread_exit = False

    def show(self):
        self.main_window.show()
        self.app.exec()

    def run_clicked(self):
        if self.thread_running:
            self.thread_exit = True
            return
        self.pushButton_run.setText('Cancel')
        self.main_window.statusBar().clearMessage()
        self.tableWidget.clear()
        self.tableWidget.setRowCount(0)
        self.table_set_headers()
        self.thread_running = True
        self.thread_exit = False
        check_function = self.check_host_fast if self.checkBox_fast.isChecked() else self.check_host
        threading.Thread(target=check_function,
                         args=(self.comboBox_host.currentText(), self.lineEdit_start.text(), self.lineEdit_end.text(),
                               self.lineEdit_timeout.text()),
                         daemon=True).start()
        threading.Thread(target=self.scroll_daemon, daemon=True).start()

    def scroll_daemon(self):
        while self.thread_running:
            time.sleep(0.1)
            self.main_window.signal.emit({'func': self.table_scroll_to_last})

    def table_set(self, data):
        row_count: int = self.tableWidget.rowCount() + 1
        self.tableWidget.setRowCount(row_count)
        for j, column in enumerate(data):
            self.tableWidget.setItem(row_count - 1, j, QTableWidgetItem(str(column)))

    def table_set_headers(self):
        headers = ['Buffer', 'Packet', 'Info']
        self.tableWidget.setColumnCount(len(headers))
        self.tableWidget.setHorizontalHeaderLabels(headers)

    def table_scroll_to_last(self):
        self.tableWidget.resizeColumnsToContents()
        self.tableWidget.verticalScrollBar().setSliderPosition(self.tableWidget.verticalScrollBar().maximum())

    def check_host_fast(self, host, start, end, timeout):
        start_time = time.time()
        fast_search = {'start': int(start), 'end': int(end)}
        while fast_search['start'] < fast_search['end']:
            if self.thread_exit:
                break
            step = fast_search['end'] - fast_search['start']
            step = int(step / 2)
            if step == 0:
                step = 1
            size_try = fast_search['start'] + step
            reply_time, message = ping_socket(host, size_try, timeout)
            self.main_window.signal.emit({'func': self.table_set, 'arg': [size_try, size_try + 28, message]})
            print(fast_search['start'], fast_search['end'], step, size_try)
            if reply_time >= 0:
                fast_search['start'] = size_try
                continue
            fast_search['end'] = size_try - 1
        print(fast_search['start'], fast_search['end'])
        self.main_window.signal.emit({'func': self.table_scroll_to_last})
        self.main_window.signal.emit({
            'func': self.main_window.statusBar().showMessage,
            'arg': f"best MTU ({fast_search['start']}) {fast_search['start'] + 28}"})
        self.thread_running = False
        self.main_window.signal.emit({'func': self.pushButton_run.setText, 'arg': 'Run'})
        print(time.time() - start_time)

    def check_host(self, host, start, end, timeout):
        start_time = time.time()
        last_size = -1
        for i in range(int(start), int(end)):
            if self.thread_exit:
                break
            reply_time, message = ping_socket(host, i, timeout)
            if reply_time >= 0:
                last_size = i
            self.main_window.signal.emit({'func': self.table_set, 'arg': [i, i + 28, message]})
        self.main_window.signal.emit({'func': self.table_scroll_to_last})
        self.main_window.signal.emit({
            'func': self.main_window.statusBar().showMessage,
            'arg': f'best MTU ({last_size}) {last_size + 28}'})
        self.thread_running = False
        self.main_window.signal.emit({'func': self.pushButton_run.setText, 'arg': 'Run'})
        print(time.time() - start_time)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    qdarktheme.setup_theme("dark")
    main_window = MainWindow()
    main_window.show()
