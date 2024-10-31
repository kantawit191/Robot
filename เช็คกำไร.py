import json
from datetime import datetime, timedelta
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

# ฟังก์ชันสำหรับคำนวณกำไร
def calculate_profit():
    with open('trade_log.json', 'r') as file:
        trades = json.load(file)

    total_profit = 0
    profit_24h = 0
    buy_count = 0
    sell_count = 0

    now = datetime.now()
    time_24h_ago = now - timedelta(hours=24)

    for trade in trades:
        trade_datetime = datetime.strptime(trade['date_time'], '%Y-%m-%d %H:%M:%S')

        if trade['action'] == 'buy':
            buy_count += 1
        elif trade['action'] == 'sell':
            sell_count += 1
            if trade['profit'] is not None:
                total_profit += trade['profit']
                if trade_datetime >= time_24h_ago:
                    profit_24h += trade['profit']

    return profit_24h, total_profit, buy_count, sell_count, time_24h_ago, now

# ฟังก์ชันอัปเดตผลการคำนวณใน GUI
def update_labels():
    profit_24h, total_profit, buy_count, sell_count, time_24h_ago, now = calculate_profit()
    lbl_24h_profit.setText(f"กำไร 24 ชั่วโมง: {profit_24h:.4f} USDT\nช่วงเวลา: {time_24h_ago.strftime('%Y-%m-%d %H:%M:%S')} - {now.strftime('%Y-%m-%d %H:%M:%S')}")
    lbl_total_profit.setText(f"กำไรรวม: {total_profit:.4f} USDT")
    lbl_buy_count.setText(f"จำนวนการซื้อ: {buy_count}")
    lbl_sell_count.setText(f"จำนวนการขาย: {sell_count}")

# สร้างแอปพลิเคชันหลัก
app = QApplication([])

# สร้างหน้าต่างหลัก
window = QWidget()
window.setWindowTitle("สรุปกำไรการเทรด")
window.setGeometry(100, 100, 500, 400)
window.setStyleSheet("background-color: #2b2b2b;")  # สีพื้นหลังโทนเข้ม

# สร้าง layout และ widget สำหรับแสดงข้อมูล
layout = QVBoxLayout()

# สร้างฟอนต์สำหรับ label
font_header = QFont("Arial", 16, QFont.Weight.Bold)
font_normal = QFont("Arial", 14)

# เพิ่ม widget ที่มีฟอนต์และสีสัน
lbl_24h_profit = QLabel("กำไร 24 ชั่วโมง: ")
lbl_24h_profit.setFont(font_normal)
lbl_24h_profit.setStyleSheet("color: #00ffff;")  # สีฟ้าอมเขียว

lbl_total_profit = QLabel("กำไรรวม: ")
lbl_total_profit.setFont(font_normal)
lbl_total_profit.setStyleSheet("color: #7fff00;")  # สีเขียวสด

lbl_buy_count = QLabel("จำนวนการซื้อ: ")
lbl_buy_count.setFont(font_normal)
lbl_buy_count.setStyleSheet("color: #ff8c00;")  # สีส้มเข้ม

lbl_sell_count = QLabel("จำนวนการขาย: ")
lbl_sell_count.setFont(font_normal)
lbl_sell_count.setStyleSheet("color: #ff4500;")  # สีส้มแดง

header_label = QLabel("ข้อมูลการเทรดล่าสุด")
header_label.setFont(font_header)
header_label.setStyleSheet("color: #ffffff;")  # สีขาว
header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

# เพิ่ม widget ลงใน layout
layout.addWidget(header_label)
layout.addWidget(lbl_24h_profit)
layout.addWidget(lbl_total_profit)
layout.addWidget(lbl_buy_count)
layout.addWidget(lbl_sell_count)

# ปุ่มสำหรับรีเฟรชข้อมูล
btn_refresh = QPushButton("รีเฟรชข้อมูล")
btn_refresh.setFont(font_normal)
btn_refresh.setStyleSheet("background-color: #4b0082; color: white;")  # ปรับสีปุ่มเป็นโทนเข้ม (สีม่วงเข้ม)
btn_refresh.clicked.connect(update_labels)
layout.addWidget(btn_refresh)

# ตั้งค่า layout ให้กับหน้าต่างหลัก
window.setLayout(layout)

# เรียกฟังก์ชันอัปเดตข้อมูลครั้งแรก
update_labels()

# แสดงหน้าต่างหลัก
window.show()

# รันแอปพลิเคชัน
app.exec()
