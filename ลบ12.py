import sys
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, 
                             QPushButton, QComboBox, QMessageBox, QHBoxLayout, QSpacerItem, 
                             QSizePolicy, QTableWidget, QTableWidgetItem, QLineEdit)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

class TradeLogApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trade Log Manager and Status")
        self.setGeometry(100, 100, 645, 900)  # ขนาดหน้าต่างใหญ่ขึ้น

        # ตั้งค่า Style Sheet สำหรับหน้าต่างหลักและ Table
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2E1A47;  /* สีม่วงเข้มสำหรับพื้นหลังด้านนอก */
            }
            QTableWidget {
                background-color: #3A1E59;  /* สีม่วงเข้มสำหรับพื้นหลังของตาราง */
                border: 2px solid #7B27D0; /* กรอบสีม่วงรอบตาราง */
                color: white;  /* ตัวอักษรสีขาว */
            }
            QHeaderView::section {
                background-color: #5D1AA4; /* สีม่วงเข้มสำหรับส่วนหัวของตาราง */
                color: white;  /* สีตัวอักษรในหัวตาราง */
                border: 1px solid #7B27D0;
            }
            QTableWidget QTableCornerButton::section {
                background-color: #5D1AA4; /* มุมซ้ายบนของตาราง */
                border: 1px solid #7B27D0;
            }
            QTableWidget::item:selected {
                background-color: #7B27D0; /* สีม่วงสดสำหรับแถวที่เลือก */
                color: white;
            }
            QTableWidget::item {
                border: 1px solid #7B27D0; /* ขอบสีม่วงสำหรับแต่ละเซลล์ */
            }
            QPushButton {
                background-color: #7B27D0; /* ปุ่มสีม่วง */
                color: white;
                font-size: 14px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #9337E8; /* ปุ่มเปลี่ยนสีเมื่อ hover */
            }
        """)

        # Layout และ Widget
        layout = QVBoxLayout()

        # Label และ QLineEdit สำหรับการค้นหา
        self.search_label = QLabel("ค้นหาคู่เงิน:")
        self.search_input = QLineEdit()
        self.search_input.textChanged.connect(self.filter_table)  # เรียกฟังก์ชันกรองตารางเมื่อมีการเปลี่ยนแปลงข้อความ

        layout.addWidget(self.search_label)
        layout.addWidget(self.search_input)

        # Dropdown สำหรับเลือกไฟล์
        file_label = QLabel("Select JSON File:")
        file_label.setFont(QFont("Arial", 14))
        file_label.setStyleSheet("color: #D8DEE9;")
        layout.addWidget(file_label)

        self.comboBox_file = QComboBox()
        self.comboBox_file.setFont(QFont("Arial", 12))
        self.comboBox_file.addItems(["trade_log.json", "trade_status1.json", "trade_status2.json"])
        self.comboBox_file.setStyleSheet("""
            QComboBox {
                background-color: #4C566A;
                color: #ECEFF4;
                border-radius: 5px;
                padding: 5px;
            }
            QComboBox:hover {
                background-color: #5E81AC;
            }
        """)
        self.comboBox_file.currentIndexChanged.connect(self.load_data)
        layout.addWidget(self.comboBox_file)

        # Table เพื่อแสดงข้อมูล
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)  # เลือกทั้งแถวเมื่อคลิกหรือค้นหา
        layout.addWidget(self.table)

        # ปุ่มสำหรับลบรายการที่เลือก
        self.delete_button = QPushButton("ลบรายการที่เลือก")
        self.delete_button.setFont(QFont("Arial", 14))
        self.delete_button.setFixedSize(200, 50)
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #5E81AC;
                color: #ECEFF4;
                border-radius: 10px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #88C0D0;
            }
        """)
        self.delete_button.clicked.connect(self.confirm_delete)
        layout.addWidget(self.delete_button)

        # ตั้ง layout
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Load initial data
        self.load_data()

    def load_data(self):
        file_name = self.comboBox_file.currentText()
        try:
            with open(file_name, 'r') as file:
                self.trade_data = json.load(file)
                if file_name == "trade_log.json":
                    self.display_trade_log(self.trade_data)
                else:
                    self.display_trade_status(self.trade_data)
        except FileNotFoundError:
            QMessageBox.critical(self, "Error", f"File {file_name} not found.")
            self.trade_data = {}
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Error", f"File {file_name} is not a valid JSON file.")
            self.trade_data = {}

    def display_trade_log(self, data):
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['วันที่', 'คู่เงิน', 'จำนวนคอยล์', 'ไม้ที่', 'Action (Buy/Sell)'])
        self.table.setRowCount(len(data))

        # ปรับความกว้างของคอลัมน์
        self.table.setColumnWidth(0, 180)  # ปรับความกว้างของคอลัมน์วันที่ให้กว้างขึ้น

        colors = [
            QColor("#9337E8"),  # สีม่วงจากภาพสำหรับวันที่
            QColor("#7B27D0"),  # สีม่วงจากภาพสำหรับคู่เงิน
            QColor("#6E22B7"),  # สีม่วงจากภาพสำหรับจำนวนคอยล์
            QColor("#5D1AA4"),  # สีม่วงจากภาพสำหรับไม้ที่
            QColor("#430F74")   # สีม่วงเข้มจากภาพสำหรับ action (buy/sell)
        ]

        text_color = QColor("#FFFFFF")  # สีตัวอักษรขาว
        font = QFont()
        font.setPointSize(12)

        for row, trade in enumerate(data):
            self.add_colored_item(row, 0, trade['date_time'], colors[0], text_color, font)
            self.add_colored_item(row, 1, trade['symbol'], colors[1], text_color, font)
            self.add_colored_item(row, 2, str(trade['quantity']), colors[2], text_color, font)
            self.add_colored_item(row, 3, str(trade['buy_number']), colors[3], text_color, font)
            self.add_colored_item(row, 4, trade['action'], colors[4], text_color, font)

    def display_trade_status(self, data):
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['คู่เงิน', 'สถานะ', 'ราคา', 'จำนวน'])
        self.table.setRowCount(len(data))

        font = QFont()
        font.setPointSize(12)

        for row, (pair, info) in enumerate(data.items()):
            self.add_colored_item(row, 0, pair, QColor("#7B27D0"), QColor("#FFFFFF"), font)
            self.add_colored_item(row, 1, info['status'], QColor("#6E22B7"), QColor("#FFFFFF"), font)
            self.add_colored_item(row, 2, str(info['buy_price']), QColor("#9337E8"), QColor("#FFFFFF"), font)
            self.add_colored_item(row, 3, str(info['quantity']), QColor("#5D1AA4"), QColor("#FFFFFF"), font)

    def add_colored_item(self, row, column, text, bg_color, text_color, font):
        """ เพิ่มข้อมูลลงในตารางพร้อมสีพื้นหลังม่วงและตัวอักษรขาว """
        item = QTableWidgetItem(text)
        item.setBackground(bg_color)
        item.setForeground(text_color)
        item.setFont(font)
        self.table.setItem(row, column, item)

    def confirm_delete(self):
        """ ฟังก์ชันยืนยันการลบ """
        selected_row = self.table.currentRow()  # ดึงแถวที่เลือก
        if selected_row != -1:
            selected_file = self.comboBox_file.currentText()
            symbol = self.table.item(selected_row, 1 if selected_file == "trade_log.json" else 0).text()

            # แสดงกล่องข้อความยืนยันการลบ
            reply = QMessageBox.question(self, "Confirm Delete", 
                                         f"คุณต้องการลบรายการนี้หรือไม่?", 
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.delete_selected_item()

    def delete_selected_item(self):
        selected_row = self.table.currentRow()  # ดึงแถวที่เลือก
        if selected_row != -1:
            selected_file = self.comboBox_file.currentText()

            if selected_file == "trade_log.json":
                del self.trade_data[selected_row]  # ลบเฉพาะแถวที่เลือกตาม index
            else:
                pair = self.table.item(selected_row, 0).text()
                del self.trade_data[pair]  # ลบรายการตามคู่เงิน

            # เขียนข้อมูลกลับไปยังไฟล์ JSON
            with open(selected_file, 'w') as file:
                json.dump(self.trade_data, file, indent=4)

            QMessageBox.information(self, 'Success', 'รายการถูกลบเรียบร้อยแล้ว')

            # โหลดข้อมูลใหม่และกรองตามคำค้นหา
            self.load_data()  # โหลดข้อมูลใหม่
            self.filter_table()  # เรียกฟังก์ชันกรองข้อมูลอีกครั้งตามคำค้นหา
        else:
            QMessageBox.warning(self, 'Warning', 'กรุณาเลือกรายการที่จะลบ')

    def filter_table(self):
        search_term = self.search_input.text().lower()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1 if self.comboBox_file.currentText() == "trade_log.json" else 0)
            if item is not None:
                if search_term in item.text().lower():
                    self.table.setRowHidden(row, False)
                else:
                    self.table.setRowHidden(row, True)

def main():
    app = QApplication(sys.argv)
    window = TradeLogApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
