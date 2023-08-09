#!/usr/bin/python3
import threading
import subprocess
import os
import sys
import datetime
import mimetypes
from getpass import getpass
from subprocess import Popen, PIPE
from threading import Thread
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QWidget, QLineEdit, QPushButton, QTableWidget,
                             QMessageBox, QTableWidgetItem, QMenu, QAction,
                             QInputDialog, QDesktopWidget, QHeaderView)

class MyTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        if (isinstance(other, QTableWidgetItem)):
            my_value = self.data(Qt.UserRole)
            other_value = other.data(Qt.UserRole)

            if (my_value is not None and other_value is not None):
                return my_value < other_value

        return super(MyTableWidgetItem, self).__lt__(other)

class MyTableWidget(QTableWidget):
    def __init__(self, rows, columns, parent=None):
        super().__init__(rows, columns, parent)

    def lessThan(self, item1, item2):
        column = self.sortColumn()
        if column in [2, 3]:  # columns "Size" and "Time"
            return item1.data(Qt.UserRole) < item2.data(Qt.UserRole)
        else:
            return super().lessThan(item1, item2)

class MainWindow(QMainWindow):
    update_finished = pyqtSignal()  # New signal
    def __init__(self):
        super().__init__()
        widget = QWidget(self)
        self.searching = False
        self.selected_item = None  # Set initial value
        self.layout = QVBoxLayout(widget)
        self.setCentralWidget(widget)

        self.search_layout = QHBoxLayout()
        self.layout.addLayout(self.search_layout)
        
        self.line_edit = QLineEdit(self)
        self.search_layout.addWidget(self.line_edit)
        # ... Existing code ...
        self.update_finished.connect(self.enable_update_button)  # Connect the signal to a slot

        self.search_button = QPushButton('Search', self)
        self.search_button.clicked.connect(self.search_clicked)
        self.search_layout.addWidget(self.search_button)

        self.update_index_button = QPushButton('Update Index', self)
        self.update_index_button.clicked.connect(self.update_index_clicked)
        self.search_layout.addWidget(self.update_index_button)

        # Create QTableWidget
        self.table_widget = MyTableWidget(0, 5, self)
        self.table_widget.setHorizontalHeaderLabels(['Filename', 'Path', 'Size', 'Time', 'Filetype'])

        # Set column width
        self.table_widget.setColumnWidth(0, 160)  # Filename
        self.table_widget.setColumnWidth(1, 300)  # Path
        self.table_widget.setColumnWidth(2, 100)  # Time
        self.table_widget.setColumnWidth(3, 190)  # Size  
        # Set the stretch for the filetype
        self.table_widget.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)

        self.layout.addWidget(self.table_widget)
        self.table_widget.itemSelectionChanged.connect(self.handle_item_selection_changed)
        self.table_widget.itemDoubleClicked.connect(self.open_file_double_click)
        self.line_edit.returnPressed.connect(self.search_clicked)  # Create a signal for enter key press in lineEdit
        self.line_edit.setFocus()  # Put the focus on the lineEdit
                # Enable Sorting
        self.table_widget.setSortingEnabled(True)
        self.updateGeometry()
        # Get the geometry of the screen
        screen = QDesktopWidget().screenGeometry()

        # Calculate the center point of the screen
        center_point = screen.center()

        # Move the center point of the window to the center point of the screen
        self.move(center_point.x() - self.width() // 2, center_point.y() - self.height() // 2)

    def open_file_double_click(self, item):
        self.table_widget.selectRow(item.row())  # Select the row of the double-clicked item
        self.open_file()  # Call the open_file method

    def enable_update_button(self):
        self.update_index_button.setEnabled(True)
    def contextMenuEvent(self, event):
        context_menu = QMenu(self)

        open_dir_action = QAction("Open Directory", self)
        open_file_action = QAction("Open File", self)
        copy_filename_action = QAction("Copy Filename", self)
        copy_filepath_action = QAction("Copy Filepath", self)
        delete_selected_action = QAction("Delete", self)

        # connect actions to the functions
        open_dir_action.triggered.connect(self.open_directory)
        open_file_action.triggered.connect(self.open_file)
        copy_filename_action.triggered.connect(self.copy_filename)
        copy_filepath_action.triggered.connect(self.copy_filepath)
        delete_selected_action.triggered.connect(self.delete_selected)

        context_menu.addAction(open_dir_action)
        context_menu.addAction(open_file_action)
        context_menu.addSeparator()
        context_menu.addAction(copy_filename_action)
        context_menu.addAction(copy_filepath_action)
        context_menu.addSeparator()
        context_menu.addAction(delete_selected_action)
        
        context_menu.exec_(event.globalPos())

    def handle_item_selection_changed(self):
        self.selected_item = self.table_widget.currentItem()

    def open_directory(self):
        if self.selected_item:
            row = self.selected_item.row()
            item = self.table_widget.item(row, 1)
            if item:
                path = item.text()
                if os.path.isdir(path):
                    subprocess.run(['nautilus', path])
                else:
                    subprocess.run(['nautilus', '--select', path])
            else:
                QMessageBox.information(self, "Invalid path", "The selected item does not have a valid path.")
        else:
            QMessageBox.information(self, "No selection", "Please select an item first.")

    def open_file(self):
        if self.selected_item:
            row = self.selected_item.row()
            item = self.table_widget.item(row, 1)
            if item:
                path = item.text()
                if os.path.exists(path):  # It's necessary to check whether the file path exists.
                    subprocess.run(['xdg-open', path])
            else:
                QMessageBox.information(self, "Invalid path", "The selected item does not have a valid path.")
        else:
            QMessageBox.information(self, "No selection", "Please select an item first.")

    def sort_by(self, col, descending):
        if col == "time":
            self.table_widget.sortItems(2, Qt.DescendingOrder if descending else Qt.AscendingOrder)
            
        elif col == "size":
            self.table_widget.sortItems(3, Qt.DescendingOrder if descending else Qt.AscendingOrder)

    def copy_filename(self):
        self.copy_to_clipboard(0)

    def copy_filepath(self):
        self.copy_to_clipboard(1)

    def copy_to_clipboard(self, index):
        selected_items = self.table_widget.selectedItems()
        if len(selected_items) > 0:
            copied_str = ''
            for item in selected_items:
                row = item.row()
                item = self.table_widget.item(row, index)
                if item:
                    copied_str += item.text() + '\n'
            QApplication.clipboard().setText(copied_str)
        else:
            QMessageBox.information(self, "No selection", "Please select an item first.")

    def updateGeometry(self):
        total_width, total_height = self.calculateSize()
        # Add a little offset
        total_width += 20
        # total_height += 100      
        total_height=600  
        self.resize(total_width, total_height)

    def calculateSize(self):
        total_width = self.table_widget.verticalHeader().width()
        for i in range(self.table_widget.columnCount()):
            total_width += self.table_widget.columnWidth(i)

        total_height = self.table_widget.horizontalHeader().height()
        for i in range(self.table_widget.rowCount()):
            total_height += self.table_widget.rowHeight(i)
        return total_width, total_height

    def update_index_clicked(self):
        # Ask for password
        password, ok = QInputDialog.getText(self, 'Password', 'Enter password:', QLineEdit.Password)
        if ok:
            command = ['sudo', '-S', 'updatedb']
            Thread(target=self.run_updatedb, args=(command, password, self.update_finished), daemon=True).start()
        # 禁用按钮
        self.update_index_button.setEnabled(False)

    def delete_selected(self):
        selected_items = self.table_widget.selectedItems()
        if len(selected_items) > 0:
            confirm_msg_box = QMessageBox(self)
            confirm_msg_box.setWindowTitle("Confirm deletion")
            confirm_msg_box.setText("Are you sure you want to delete the selected files?")
            confirm_msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            response = confirm_msg_box.exec_()
            if response != QMessageBox.Yes:
                return
            for item in selected_items:
                row = item.row()
                item = self.table_widget.item(row, 1)
                if item:
                    path = item.text()
                    try:
                        if os.path.isfile(path):
                            os.remove(path)
                        elif os.path.isdir(path):
                            os.rmdir(path)  # This will only remove empty directories
                        self.table_widget.removeRow(row)
                    except OSError as e:
                        QMessageBox.critical(self, "Error", "Failed to delete file: " + str(e))
        else:
            QMessageBox.information(self, "No selection", "Please select an item first.")
            
    def run_updatedb(command, password, signal):
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.stdin.write(password.encode())
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            print("Failed to update index. Error: " + stderr.decode())  # You can replace this with a PyQt5 messagebox
        else:
            print("Index updated successfully.")  # You can replace this with a PyQt5 messagebox
        signal.emit()  # Emit the signal when the method is done


    def human_readable_size(self, size):
        # Convert bytes to a human readable string
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        unit = 0
        while size >= 1024 and unit < len(units) - 1:
            size /= 1024
            unit += 1
        return f"{size:.1f} {units[unit]}"

    def _search_files(self):
        try:
            filename = self.line_edit.text().strip()
            if not filename:
                return
            
            exact_match = False
            if filename.startswith('"') and filename.endswith('"'):
                filename = filename[1:-1]
                exact_match = True

            keywords = filename.split()

            longest_keyword = max(keywords, key=len)
            search_path = '/' in filename
            if search_path:
                command = ['locate', '-i', longest_keyword]
            else:
                command = ['locate', '-i', '-b', longest_keyword]

            process = Popen(command, stdout=PIPE, stderr=PIPE)
            stdout, stderr = process.communicate()

            lines = filter(os.path.exists, stdout.decode().split("\n"))
            for line in lines:
                if line and os.path.exists(line):
                    if search_path:
                        match_string = line
                    else:
                        match_string = os.path.basename(line)
                    # print("match_string:", match_string)
                    # print("keywords:", keywords)
                    # for kw in keywords:
                    #     print(f"'{kw.lower()}' in '{match_string.lower()}' is {kw.lower() in match_string.lower()}")
                    if not all(kw.lower() in match_string.lower() for kw in keywords):
                        continue
                    if exact_match and match_string != filename:
                        continue
                    size_in_bytes = os.path.getsize(line)
                    timestamp = os.path.getmtime(line)
                    readable_time = datetime.datetime.fromtimestamp(timestamp).isoformat()
                    readable_size = self.human_readable_size(size_in_bytes)

                    # Add the information to the table widget
                    row_position = self.table_widget.rowCount()
                    self.table_widget.insertRow(row_position)
                    # Extract the filename from the path
                    filename = os.path.basename(line)
                    # Create a QTableWidgetItem for the filename and add it to the table
                    name_item = MyTableWidgetItem(filename)
                    name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)  # Disable editing
                    self.table_widget.setItem(row_position, 0, name_item)

                    # 其他的列（如文件名、路径、文件类型）可以照旧处理
                    # self.table_widget.setItem(row_position, 0, QTableWidgetItem(os.path.basename(line)))
                    self.table_widget.setItem(row_position, 1, QTableWidgetItem(line))

                    # Create the QTableWidgetItem with MyTableWidgetItem
                    size_item = MyTableWidgetItem(readable_size)
                    size_item.setData(Qt.UserRole, size_in_bytes)
                    size_item.setFlags(size_item.flags() & ~Qt.ItemIsEditable)  # Disable editing
                    self.table_widget.setItem(row_position, 2, size_item)
                    time_item = QTableWidgetItem(readable_time)
                    time_item.setData(Qt.UserRole, timestamp)
                    self.table_widget.setItem(row_position, 3, time_item)

                    # Guess the file type
                    file_type, _ = mimetypes.guess_type(line)
                    if file_type is None:
                        file_type = "Unknown"

                    self.table_widget.setItem(row_position, 4, QTableWidgetItem(file_type))
        finally:
            self.searching = False
            # Enable sorting after adding data
            self.table_widget.setSortingEnabled(True)

    def search_clicked(self):
        # If already searching, don't start another search
        if self.searching:
            return
        # Disable sorting before adding data
        self.table_widget.setSortingEnabled(False)
        self.table_widget.setRowCount(0)
        self.searching = True

        # Start search in a new thread
        search_thread = threading.Thread(target=self._search_files)
        search_thread.start()

        

def update_index_button(self):
    QMessageBox.information(self, '', 'Update Index button clicked.')

app = QApplication(sys.argv)
main_window = MainWindow()
main_window.show()
sys.exit(app.exec_())
