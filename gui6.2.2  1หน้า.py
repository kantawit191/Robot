import sys
import json
import requests
import weakref  # เพิ่ม weakref
from functools import partial
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QPushButton, QScrollArea
from PyQt6.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

# เก็บรายการของ PriceFetcher threads เพื่อป้องกันไม่ให้ถูกลบทิ้งในขณะทำงาน
fetchers = []

# QThread สำหรับดึงราคาจาก Binance
class PriceFetcher(QThread):
    price_fetched = pyqtSignal(str, float)  # สัญญาณเพื่อส่งข้อมูลราคากลับไปที่ GUI
    
    def __init__(self, pair):
        super().__init__()
        self.pair = pair

    def run(self):
        price = get_current_price(self.pair)
        if price is not None:
            self.price_fetched.emit(self.pair, price)

# ฟังก์ชันดึงราคาปัจจุบันจาก Binance API
def get_current_price(pair):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={pair}"
        response = requests.get(url)
        data = response.json()
        
        # ตรวจสอบว่าคีย์ 'price' อยู่ใน data ก่อนที่จะใช้งาน
        if 'price' in data:
            return float(data["price"])
        else:
            print(f"Error: 'price' key not found in API response for {pair}. Response: {data}")
            return None
    except Exception as e:
        print(f"Error fetching price for {pair}: {e}")
        return None


# ฟังก์ชันสำหรับคำนวณจุดซื้อและจุดขาย
def calculate_entry_exit(price_low, price_high=None):
    buy_price = price_low * 1.013  # บวก 1.3% สำหรับจุดซื้อ
    sell_price = price_high * 0.985 if price_high is not None else None  # ลบ 1.5% สำหรับจุดขาย (ถ้ามี high)
    return round(buy_price, 8), round(sell_price, 8) if sell_price is not None else None

# ฟังก์ชันในการโหลดและแสดงข้อมูล
def load_data():
    try:
        with open("high_low_status.json", "r") as file:
            data = json.load(file)
            global pair_low_high
            pair_low_high = {pair: entry for pair, entry in data.items()}

        # ลบข้อมูลเก่าใน layout
        clear_layout(data_layout)

        # โทนสีเขียวแบบไล่ระดับ
        green_shades = [
            "#1E3008", "#28400F", "#325012", "#3D5F16", "#476F1A", "#517F1E",
            "#5B8F21", "#659F25", "#74A93B", "#84B251", "#93BC66", "#A3C57C",
            "#B2CF92", "#C1D9A8"
        ]

        for idx, (pair, entry) in enumerate(sorted(data.items())):
            price_low = entry.get("low")
            price_high = entry.get("high")
            buy_price, sell_price = calculate_entry_exit(price_low, price_high)

            # สร้าง QTextEdit สำหรับแต่ละคู่เงิน
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setFont(QFont("Arial", 10))
            text_edit.setStyleSheet("color: white;")

            # ข้อความแต่ละบรรทัด
            text_content = f"""
คู่เงิน: {pair}
ราคา Low: {price_low}
ราคา High: {price_high if price_high else 'ไม่มี'}
จุดซื้อ: {buy_price}
จุดขาย: {sell_price if sell_price else 'ไม่มี'}
ราคาปัจจุบัน: กำลังโหลด...
"""
            text_edit.setText(text_content.strip())

            # ตั้งค่าสีพื้นหลังบล็อกจากโทนสีเขียว
            color = green_shades[idx % len(green_shades)]
            text_edit.setStyleSheet(f"background-color: {color}; color: white;")

            # เพิ่ม QTextEdit ใน layout
            data_layout.addWidget(text_edit)

            # เริ่ม PriceFetcher thread สำหรับดึงราคาปัจจุบัน
            start_price_fetching(pair, buy_price, sell_price, text_edit)

    except FileNotFoundError:
        error_message("ไม่พบไฟล์ high_low_status.json")
    except json.JSONDecodeError:
        error_message("ไฟล์ JSON ไม่ถูกต้อง")

# ฟังก์ชันสำหรับเริ่ม PriceFetcher thread และตั้งค่าให้ดึงราคาอัตโนมัติทุก 60 วินาที
def start_price_fetching(pair, buy_price, sell_price, text_edit):
    text_edit_ref = weakref.ref(text_edit)  # ใช้ weakref เพื่ออ้างอิง text_edit
    def fetch_price():
        if text_edit_ref() is not None:  # ตรวจสอบว่า text_edit ยังอยู่
            fetcher = PriceFetcher(pair)
            fetcher.price_fetched.connect(partial(update_price, buy_price=buy_price, sell_price=sell_price, text_edit_ref=text_edit_ref))
            fetcher.finished.connect(lambda f=fetcher: fetchers.remove(f) if f in fetchers else None)
            fetchers.append(fetcher)
            fetcher.start()

    fetch_price()  # ดึงราคาทันทีครั้งแรก
    timer = QTimer()
    timer.timeout.connect(fetch_price)
    timer.start(60000)  # 60,000 มิลลิวินาที (60 วินาที)
    text_edit._fetch_timer = timer  # เก็บตัวจับเวลาไว้ใน text_edit

    # หยุด timer เมื่อ text_edit ถูกลบ
    text_edit.destroyed.connect(timer.stop)


  # เพิ่มการใช้งาน weakref (ตรวจสอบว่ามี weakref ในโค้ดส่วนบนแล้ว)

def update_price(pair, current_price, buy_price, sell_price, text_edit_ref):
    text_edit = text_edit_ref()  # เรียกใช้ weakref เพื่อรับ text_edit ถ้ายังมีอยู่
    if text_edit is not None and not text_edit.isHidden():  # ตรวจสอบว่า text_edit ยังอยู่
        text_content = f"""
คู่เงิน: {pair}
ราคา Low: {pair_low_high[pair]['low']}
ราคา High: {pair_low_high[pair].get('high', 'ไม่มี')}
จุดซื้อ: {buy_price}
จุดขาย: {sell_price if sell_price else 'ไม่มี'}
ราคาปัจจุบัน: {round(current_price, 8)}
"""
        text_edit.setText(text_content.strip())

        # เช็คเงื่อนไขสำหรับการกระพริบสี
        if buy_price and abs(current_price - buy_price) / buy_price < 0.002:
            start_blinking(text_edit, "green")  # กระพริบสีเขียว
        elif sell_price and abs(current_price - sell_price) / sell_price < 0.002:
            start_blinking(text_edit, "red")  # กระพริบสีแดง


# ฟังก์ชันสำหรับเริ่มกระพริบสี
def start_blinking(widget, color):
    def toggle_color():
        if widget:  # ตรวจสอบว่าวิดเจ็ตยังคงอยู่
            current_style = widget.styleSheet()
            new_color = f"rgba(0, 255, 0, 0.3)" if color == "green" else f"rgba(255, 0, 0, 0.3)"
            default_color = "background-color: #3D5F16; color: white;"  # ตั้งค่าสีพื้นหลังเริ่มต้น
            widget.setStyleSheet(f"background-color: {new_color}; color: white;" if "rgba" not in current_style else default_color)

    timer = QTimer()
    timer.timeout.connect(toggle_color)
    timer.start(500)  # กระพริบทุก 500 มิลลิวินาที
    widget._blink_timer = timer  # เก็บตัวจับเวลาไว้ป้องกันไม่ให้ถูกลบ
    widget.destroyed.connect(timer.stop)  # หยุดตัวจับเวลาเมื่อ widget ถูกลบ

# ฟังก์ชันสำหรับแสดงข้อความข้อผิดพลาด
def error_message(message):
    error_label = QTextEdit()
    error_label.setReadOnly(True)
    error_label.setText(message)
    error_label.setStyleSheet("color: red; font-weight: bold;")
    data_layout.addWidget(error_label)

# ฟังก์ชันในการล้าง layout
def clear_layout(layout):
    while layout.count():
        child = layout.takeAt(0)
        if child.widget():
            child.widget().deleteLater()

# สร้างหน้าต่างหลักของ PyQt6
app = QApplication(sys.argv)
window = QWidget()
window.setWindowTitle("จุดซื้อและจุดขาย (รีโหลดอัตโนมัติ)")
window.setGeometry(100, 100, 600, 700)

# Layout หลัก
main_layout = QVBoxLayout()

# ปุ่มโหลดข้อมูล
load_button = QPushButton("โหลดข้อมูล")
load_button.clicked.connect(load_data)
main_layout.addWidget(load_button)

# พื้นที่แสดงข้อมูลด้วย QScrollArea เพื่อให้สามารถเลื่อนดูบล็อกทั้งหมดได้
scroll_area = QScrollArea()
scroll_area.setWidgetResizable(True)

# วิดเจ็ตและ layout สำหรับข้อมูล
data_widget = QWidget()
data_layout = QVBoxLayout()
data_widget.setLayout(data_layout)

scroll_area.setWidget(data_widget)
main_layout.addWidget(scroll_area)

# ตั้งค่ารีโหลดอัตโนมัติทุก 10 วินาที
timer = QTimer()
timer.timeout.connect(load_data)
timer.start(10000)  # 10,000 มิลลิวินาที (10 วินาที)

# จัด layout และแสดง GUI
window.setLayout(main_layout)
window.show()

# เริ่มโปรแกรม GUI
sys.exit(app.exec())
