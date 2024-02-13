import sys
import sqlite3
from PyQt5.QtCore import QTimer, QDateTime, pyqtSlot, Qt
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QGridLayout, QGroupBox, QMessageBox, QSizePolicy, QComboBox, QInputDialog, QHBoxLayout, QCheckBox, QScrollArea, QMainWindow, QAction, QMenu
import pyotp  # Importing the pyotp library for OTP generation
import pyperclip  # Importing the pyperclip library for clipboard operations
from functools import partial

APP_VERSION = "1.0.0"  # Define your application version here

class OTPApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Pythy')
        self.db_conn = self.create_db_connection()
        self.initUI()

    def create_db_connection(self):
        # Create or connect to the SQLite database
        conn = sqlite3.connect('otp_secrets.db')
        cursor = conn.cursor()
        # Create the table to store OTP secrets if it does not exist
        cursor.execute('''CREATE TABLE IF NOT EXISTS otp_secrets
                          (id INTEGER PRIMARY KEY, application TEXT, secret_key TEXT)''')
        conn.commit()
        return conn

    def initUI(self):
        self.menuBar().setNativeMenuBar(False)
        file_menu = self.menuBar().addMenu('File')
        about_menu = self.menuBar().addMenu('About')

        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about_dialog)
        about_menu.addAction(about_action)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText('Search Applications...')
        self.search_box.textChanged.connect(self.populate_application_list)
        layout.addWidget(self.search_box)

        # Scroll area for the group box containing the list of applications
        self.scroll_area = QScrollArea()
        layout.addWidget(self.scroll_area)

        # Group box to display list of applications and their OTPs
        self.group_box_list = QGroupBox('Applications')
        self.grid_layout = QGridLayout()
        self.grid_layout.setColumnStretch(0, 1)
        self.grid_layout.setColumnStretch(1, 1)
        self.grid_layout.setColumnStretch(2, 1)
        self.group_box_list.setLayout(self.grid_layout)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.group_box_list)

        # Add application input fields and button
        self.group_box_input = QGroupBox('Add Application')
        input_layout = QGridLayout()

        self.application_name_label = QLabel('Application Name:')
        self.application_name_input = QLineEdit()
        input_layout.addWidget(self.application_name_label, 0, 0)
        input_layout.addWidget(self.application_name_input, 0, 1)

        self.secret_key_label = QLabel('Secret Key:')
        self.secret_key_input = QLineEdit()
        input_layout.addWidget(self.secret_key_label, 1, 0)
        input_layout.addWidget(self.secret_key_input, 1, 1)

        self.add_button = QPushButton('Add Application')
        self.add_button.clicked.connect(self.add_application)
        input_layout.addWidget(self.add_button, 2, 0, 1, 2)

        self.group_box_input.setLayout(input_layout)
        layout.addWidget(self.group_box_input)

        self.populate_application_list()

    def populate_application_list(self):
        # Clear the current content of the grid layout
        for i in reversed(range(self.grid_layout.count())):
            self.grid_layout.itemAt(i).widget().setParent(None)

        # Retrieve applications and their secret keys from the database
        cursor = self.db_conn.cursor()
        cursor.execute('SELECT id, application, secret_key FROM otp_secrets')
        applications = cursor.fetchall()
        filtered_applications = [app for app in applications if self.search_box.text().lower() in app[1].lower()]

        for i, (id, application, secret_key) in enumerate(filtered_applications):
            label_app = QLabel(application)
            self.grid_layout.addWidget(label_app, i, 0)

            # Create a reveal & copy button
            otp_label = QLabel('')
            otp_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            reveal_button = QPushButton('Reveal and Copy')
            reveal_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            reveal_button.clicked.connect(partial(self.reveal_and_copy, otp_label, reveal_button, secret_key))
            self.grid_layout.addWidget(reveal_button, i, 1)
            self.grid_layout.addWidget(otp_label, i, 1)
            otp_label.hide()

            # Create a timer label
            timer_label = QLabel('')
            self.grid_layout.addWidget(timer_label, i, 2)
            # Start a timer for each OTP
            timer = QTimer(self)
            timer.timeout.connect(partial(self.update_otp_and_timer, otp_label, timer_label, secret_key))
            timer.start(1000)  # Update every second

            # Create the Options dropdown menu
            options_dropdown = QComboBox()
            options_dropdown.addItem('Options')
            options_dropdown.addItems(['Delete', 'Rename'])
            options_dropdown.currentIndexChanged.connect(partial(self.handle_options_selection, options_dropdown, id))
            self.grid_layout.addWidget(options_dropdown, i, 3)

    def add_application(self):
        application = self.application_name_input.text()
        secret_key = self.secret_key_input.text().replace(" ", "")  # Remove spaces from the secret key
        if not application or not secret_key:
            QMessageBox.warning(self, 'Warning', 'Both Application Name and Secret Key are required!')
            return
        # Insert the application and secret key into the database
        cursor = self.db_conn.cursor()
        cursor.execute('INSERT INTO otp_secrets (application, secret_key) VALUES (?, ?)', (application, secret_key))
        self.db_conn.commit()
        # Refresh the application list
        self.populate_application_list()
        # Clear input fields
        self.application_name_input.clear()
        self.secret_key_input.clear()

    @pyqtSlot()
    def reveal_and_copy(self, label, button, secret_key):
        # Calculate the OTP
        totp = pyotp.TOTP(secret_key)
        otp = totp.now()
        # Copy OTP to clipboard
        pyperclip.copy(otp)
        # Show OTP label
        label.setText(otp)
        label.show()
        # Hide button
        button.hide()
        # Set up timer to clear OTP label and show button after 10 seconds
        QTimer.singleShot(10000, lambda: self.hide_otp_label_and_show_button(label, button))

    @pyqtSlot()
    def hide_otp_label_and_show_button(self, label, button):
        label.setText('')
        label.hide()
        button.show()

    @pyqtSlot()
    def update_otp_and_timer(self, label, timer_label, secret_key):
        # Calculate the OTP
        totp = pyotp.TOTP(secret_key)
        otp = totp.now()
        label.setText(otp)
        # Calculate remaining time until the next OTP
        remaining_time = totp.interval - (int(QDateTime.currentSecsSinceEpoch()) % totp.interval)
        timer_label.setText(f"Next OTP in {remaining_time} seconds")

    @pyqtSlot()
    def handle_options_selection(self, dropdown, id):
        option = dropdown.currentText()
        if option == 'Delete':
            self.delete_application(id)
            dropdown.setCurrentIndex(0)
        elif option == 'Rename':
            new_name, ok_pressed = QInputDialog.getText(self, "Rename Application", "Enter new name:", QLineEdit.Normal, "")
            if ok_pressed and new_name.strip():
                self.rename_application(id, new_name)
                dropdown.setCurrentIndex(0)

    def delete_application(self, id):
        # Confirmation dialog
        reply = QMessageBox.question(self, 'Delete Application', 'Are you sure you want to delete this application? You may not be able to access your application without your 2FA code!',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            # Delete the application from the database
            cursor = self.db_conn.cursor()
            cursor.execute('DELETE FROM otp_secrets WHERE id = ?', (id,))
            self.db_conn.commit()
            # Refresh the application list
            self.populate_application_list()

    def rename_application(self, id, new_name):
        # Update the application name in the database
        cursor = self.db_conn.cursor()
        cursor.execute('UPDATE otp_secrets SET application = ? WHERE id = ?', (new_name, id))
        self.db_conn.commit()
        # Refresh the application list
        self.populate_application_list()

    def show_about_dialog(self):
        QMessageBox.about(self, 'About OTP Generator', f'OTP Generator Version {APP_VERSION}')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    otp_app = OTPApp()
    otp_app.resize(450, 400)  # Set a slightly larger size
    otp_app.show()
    sys.exit(app.exec_())
