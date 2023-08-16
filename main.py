import subprocess
import sys
import threading
import time

import qdarktheme
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QTableWidgetItem

from custom_signal_window import CustomSignalWindow
from ui.main import Ui_MainWindow

si = subprocess.STARTUPINFO()
si.dwFlags |= subprocess.STARTF_USESHOWWINDOW


def ping_with_df(target, size):
    command = ['ping', '-f', '-l', str(size), '-n', '1', target]

    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, startupinfo=si)
        output = output.decode('utf-8', 'ignore')
        # print(output)
        if 'Zielnetz nicht erreichbar.' in output:
            print(output)
            return -4
        elif 'Paket msste fragmentiert werden, DF-Flag ist jedoch gesetzt.' in output:
            return -2
        ms = output[:output.find('ms')]
        ms = ms[ms.rfind('=') + 1:]
        return int(ms)
    except subprocess.CalledProcessError as e:
        output = e.output.decode('utf-8', 'ignore')
        if 'Paket msste fragmentiert werden, DF-Flag ist jedoch gesetzt.' in output:
            return -2
        elif f'Ping-Anforderung konnte Host "{target}" nicht finden.' in output:
            return -3
        print("error:", output)
        return -1


class MainWindow(Ui_MainWindow):
    def __init__(self):
        self.app = QtWidgets.QApplication(sys.argv)
        self.main_window = CustomSignalWindow()
        self.setupUi(self.main_window)

        self.pushButton_run.clicked.connect(self.run_clicked)

        self.rows = []

    def show(self):
        self.main_window.show()
        self.app.exec_()

    def run_clicked(self):
        self.pushButton_run.setEnabled(False)
        self.rows.clear()
        threading.Thread(target=self.check_host,
                         args=(self.lineEdit_host.text(), self.lineEdit_start.text(), self.lineEdit_end.text()),
                         daemon=True).start()
        threading.Thread(target=self.scroll_daemon, daemon=True).start()

    def scroll_daemon(self):
        while not self.pushButton_run.isEnabled():
            time.sleep(0.1)
            self.main_window.signal.emit({'func': self.table_scroll_to_last})

    def table_set(self, data):
        self.rows.append(data)
        headers = ['Buffer', 'Packet', 'Info']
        self.tableWidget.clear()
        self.tableWidget.setColumnCount(len(headers))
        self.tableWidget.setHorizontalHeaderLabels(headers)
        self.tableWidget.setRowCount(len(self.rows))
        for i, row in enumerate(self.rows):
            for j, header in enumerate(headers):
                self.tableWidget.setItem(i, j, QTableWidgetItem(str(row[j])))

    def table_scroll_to_last(self):
        self.tableWidget.resizeColumnsToContents()
        self.tableWidget.verticalScrollBar().setSliderPosition(self.tableWidget.verticalScrollBar().maximum())

    def check_host(self, host, start, end):
        start_time = time.time()
        last_size = -1
        for i in range(int(start), int(end)):
            reply_time = ping_with_df(host, i)
            if reply_time >= 0:
                last_size = i
                self.main_window.signal.emit({'func': self.table_set, 'arg': [i, i + 28, f'{reply_time}ms']})
            elif reply_time == -2:
                self.main_window.signal.emit({'func': self.table_set, 'arg': [i, i + 28, 'should be fragmented']})
            elif reply_time == -3:
                self.main_window.signal.emit({'func': self.table_set, 'arg': [i, i + 28, 'host not found']})
        self.main_window.signal.emit({'func': self.table_scroll_to_last})
        self.main_window.signal.emit({
            'func': self.main_window.statusBar().showMessage,
            'arg': f'best MTU ({last_size}) {last_size + 28}'})
        self.pushButton_run.setEnabled(True)
        print(time.time() - start_time)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    qdarktheme.setup_theme("dark")
    main_window = MainWindow()
    main_window.show()
