import sys
import json
import requests
import weakref
from functools import partial
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QScrollArea
from PyQt6.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

fetchers = []

# QThread สำหรับดึงราคาจาก Binance
class PriceFetcher(QThread):
    price_fetched = pyqtSignal(str, float)

    def __init__(self, pair):
        super().__init__()
        self.pair = pair

    def run(self):
        price = get_current_price(self.pair)
        if price is not None:
            self.price_fetched.emit(self.pair, price)

def get_current_price(pair):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={pair}"
        response = requests.get(url)
        data = response.json()
        if 'price' in data:
            return float(data["price"])
        else:
            print(f"Error: 'price' key not found in API response for {pair}. Response: {data}")
            return None
    except Exception as e:
        print(f"Error fetching price for {pair}: {e}")
        return None

def calculate_entry_exit(price_low, price_high=None):
    buy_price = price_low * 1.013
    sell_price = price_high * 0.985 if price_high is not None else None
    return round(buy_price, 8), round(sell_price, 8) if sell_price is not None else None

def load_data_from_file(file_name, layout):
    try:
        with open(file_name, "r") as file:
            data = json.load(file)

        clear_layout(layout)

        # โทนสีม่วงสำหรับบล็อกข้อมูล
        purple_shades = [
            "#9337E8", "#7B27D0", "#6E22B7", "#5D1AA4", "#430F74"
        ]

        for idx, (pair, entry) in enumerate(sorted(data.items())):
            price_low = entry.get("low")
            price_high = entry.get("high")
            buy_price, sell_price = calculate_entry_exit(price_low, price_high)

            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setFont(QFont("Arial", 10))
            text_edit.setStyleSheet("color: white;")

            text_content = f"""
คู่เงิน: {pair}
ราคา Low: {price_low}
ราคา High: {price_high if price_high else 'ไม่มี'}
จุดซื้อ: {buy_price}
จุดขาย: {sell_price if sell_price else 'ไม่มี'}
ราคาปัจจุบัน: กำลังโหลด...
"""
            text_edit.setText(text_content.strip())

            # ตั้งค่าสีพื้นหลังบล็อกจากโทนสีม่วง
            color = purple_shades[idx % len(purple_shades)]
            text_edit.setStyleSheet(f"background-color: {color}; color: white;")

            layout.addWidget(text_edit)

            start_price_fetching(pair, buy_price, sell_price, text_edit, data)

    except FileNotFoundError:
        error_message(f"ไม่พบไฟล์ {file_name}", layout)
    except json.JSONDecodeError:
        error_message(f"ไฟล์ JSON ไม่ถูกต้องใน {file_name}", layout)

def start_price_fetching(pair, buy_price, sell_price, text_edit, data):
    text_edit_ref = weakref.ref(text_edit)
    def fetch_price():
        if text_edit_ref() is not None:
            fetcher = PriceFetcher(pair)
            fetcher.price_fetched.connect(partial(update_price, buy_price=buy_price, sell_price=sell_price, text_edit_ref=text_edit_ref, data=data))
            fetcher.finished.connect(lambda f=fetcher: fetchers.remove(f) if f in fetchers else None)
            fetchers.append(fetcher)
            fetcher.start()

    fetch_price()
    timer = QTimer()
    timer.timeout.connect(fetch_price)
    timer.start(60000)
    text_edit._fetch_timer = timer
    text_edit.destroyed.connect(timer.stop)

def update_price(pair, current_price, buy_price, sell_price, text_edit_ref, data):
    text_edit = text_edit_ref()
    if text_edit is not None and not text_edit.isHidden():
        text_content = f"""
คู่เงิน: {pair}
ราคา Low: {data[pair]['low']}
ราคา High: {data[pair].get('high', 'ไม่มี')}
จุดซื้อ: {buy_price}
จุดขาย: {sell_price if sell_price else 'ไม่มี'}
ราคาปัจจุบัน: {round(current_price, 8)}
"""
        text_edit.setText(text_content.strip())

        if buy_price and abs(current_price - buy_price) / buy_price < 0.002:
            start_blinking(text_edit, "green")
        elif sell_price and abs(current_price - sell_price) / sell_price < 0.002:
            start_blinking(text_edit, "red")

def start_blinking(widget, color):
    def toggle_color():
        if widget:
            current_style = widget.styleSheet()
            new_color = f"rgba(0, 255, 0, 0.3)" if color == "green" else f"rgba(255, 0, 0, 0.3)"
            default_color = "background-color: #3D5F16; color: white;"
            widget.setStyleSheet(f"background-color: {new_color}; color: white;" if "rgba" not in current_style else default_color)

    timer = QTimer()
    timer.timeout.connect(toggle_color)
    timer.start(500)
    widget._blink_timer = timer
    widget.destroyed.connect(timer.stop)

def error_message(message, layout):
    error_label = QTextEdit()
    error_label.setReadOnly(True)
    error_label.setText(message)
    error_label.setStyleSheet("color: red; font-weight: bold;")
    layout.addWidget(error_label)

def clear_layout(layout):
    while layout.count():
        child = layout.takeAt(0)
        if child.widget():
            child.widget().deleteLater()

app = QApplication(sys.argv)
window = QWidget()
window.setWindowTitle("จุดซื้อและจุดขาย (รีโหลดอัตโนมัติ)")
window.setGeometry(100, 100, 1200, 400)

main_layout = QHBoxLayout()

# สีปุ่มตามโทนสีม่วงที่ต้องการ
button_colors = ["#9337E8", "#7B27D0", "#6E22B7", "#5D1AA4", "#430F74"]

file_layouts = {}
for idx, file_name in enumerate(["high_low_status1.json", "high_low_status2.json", "high_low_status3.json"]):
    file_widget = QWidget()
    file_layout = QVBoxLayout()
    file_widget.setLayout(file_layout)
    file_layouts[file_name] = file_layout

    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setWidget(file_widget)
    
    # วางเลย์เอาต์หลักสำหรับแต่ละคอลัมน์ (scroll area + button)
    column_layout = QVBoxLayout()
    column_layout.addWidget(scroll_area)

    # ปุ่มโหลดข้อมูล
    load_button = QPushButton(f"โหลดข้อมูลจาก {file_name}")
    load_button.setStyleSheet(f"background-color: {button_colors[idx % len(button_colors)]}; color: white;")
    load_button.clicked.connect(partial(load_data_from_file, file_name, file_layout))
    column_layout.addWidget(load_button)

    # เพิ่มคอลัมน์ลงใน layout หลัก
    main_layout.addLayout(column_layout)

window.setLayout(main_layout)
window.show()

sys.exit(app.exec())
