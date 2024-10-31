import json
import os
import requests
import threading
import time
import datetime
from binance import ThreadedWebsocketManager
from binance.client import Client
from binance.enums import SIDE_BUY, SIDE_SELL, ORDER_TYPE_MARKET
from binance.helpers import round_step_size

# ตั้งค่าการเชื่อมต่อกับ Binance API
api_key = 'p1r1mhhGCXQzCKc7lpsFRmyh6cC3atITqnlS1EmPpPhNzF94yzrUgswCduSBxkNv'
api_secret = '7TmBEWVaHjegI0DgbMtHc53gvVOoy0Un9FkWpcr5dcds9yPHEj7yEp7luDsZlQO1'
client = Client(api_key, api_secret)

# ตัวแปรที่ใช้ในการกำหนดเงื่อนไขและเปอร์เซ็นต์ต่าง ๆ
TARGET_BUY_PERCENT = 1.3
TARGET_SELL_PERCENT = 1.5
SOFT_STOP_LOSS_PERCENT = 0.6
HARD_STOP_LOSS_PERCENT = 30.0

latest_balance = {'free': 0.0}

# ฟังก์ชันการแจ้งเตือนผ่าน Line Notify
def line_notify(message):
    token = 'puFAa0PR2fLxUIgy8xaNkbMBJ4vjNoz0HanESBZ3rMA'
    url = 'https://notify-api.line.me/api/notify'
    headers = {'Authorization': f'Bearer {token}'}
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data = {'message': f"{now} - {message}"}
    response = requests.post(url, headers=headers, data=data)
    if response.status_code != 200:
        print(f"การแจ้งเตือน Line ไม่สำเร็จ: {response.status_code}")

# ฟังก์ชันสำหรับการแจ้งเตือนใน CMD
def cmd_notify(message):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{now} - {message}")

# ฟังก์ชันสำหรับการคำนวณค่าธรรมเนียม
def calculate_fee(amount, fee_percentage=0.1):
    return amount * (fee_percentage / 100)

# ฟังก์ชันสำหรับบันทึกและโหลดข้อมูล High และ Low
def save_high_low(high_low_data):
    with open('high_low_status.json', 'w') as file:
        json.dump(high_low_data, file, indent=4)
    cmd_notify("บันทึกข้อมูล High และ Low เรียบร้อยแล้ว")

def load_high_low():
    if os.path.exists('high_low_status.json'):
        with open('high_low_status.json', 'r') as file:
            return json.load(file)
    else:
        return {}

# ฟังก์ชันสำหรับบันทึกและโหลดสถานะการซื้อขาย
def save_status(trade_data):
    with open('trade_status.json', 'w') as file:
        json.dump(trade_data, file, indent=4)

def load_status():
    if os.path.exists('trade_status.json'):
        with open('trade_status.json', 'r') as file:
            return json.load(file)
    else:
        return {}

# ฟังก์ชันสำหรับอัปเดตยอดเงินในบัญชี
def update_balance():
    global latest_balance
    while True:
        try:
            balance = client.get_asset_balance(asset='USDT')
            latest_balance['free'] = float(balance['free'])
            cmd_notify(f"ยอดเงินในบัญชี (อัปเดตล่าสุด): {latest_balance['free']} USDT")
        except Exception as e:
            cmd_notify(f"ข้อผิดพลาดในการอัปเดตยอดเงินในบัญชี: {str(e)}")
        time.sleep(60)


# ฟังก์ชันสำหรับโหลดข้อมูลการซื้อขายจากไฟล์ trade_log.json
def load_trade_log():
    log_file = 'trade_log.json'
    
    # ตรวจสอบว่ามีไฟล์ log หรือไม่ ถ้าไม่มีก็สร้างใหม่
    if not os.path.exists(log_file):
        try:
            with open(log_file, 'w') as file:
                json.dump([], file)  # สร้างไฟล์ใหม่พร้อมลิสต์ว่างเปล่า
                cmd_notify(f"สร้างไฟล์ {log_file} สำเร็จ")
        except Exception as e:
            cmd_notify(f"ไม่สามารถสร้างไฟล์ {log_file} ได้: {str(e)}")
            return []
    
    # โหลดข้อมูลจากไฟล์ log
    try:
        with open(log_file, 'r') as file:
            trade_log = json.load(file)
        cmd_notify(f"โหลดข้อมูลจาก {log_file} สำเร็จ")
        return trade_log
    except Exception as e:
        cmd_notify(f"ไม่สามารถโหลดข้อมูลจาก {log_file} ได้: {str(e)}")
        return []

# ฟังก์ชันสำหรับบันทึกข้อมูลการซื้อขาย
def log_trade(action, symbol, quantity, price, trade_type, status, profit=None):
    log_file = 'trade_log.json'
    
    if not os.path.exists(log_file):
        try:
            with open(log_file, 'w') as file:
                json.dump([], file)
                cmd_notify(f"สร้างไฟล์ {log_file} สำเร็จ")
        except Exception as e:
            cmd_notify(f"ไม่สามารถสร้างไฟล์ {log_file} ได้: {str(e)}")
            return

    try:
        with open(log_file, 'r') as file:
            trade_data = json.load(file)
    except Exception as e:
        cmd_notify(f"ไม่สามารถอ่านไฟล์ {log_file} ได้: {str(e)}")
        trade_data = []

    # บันทึกรายการการซื้อขายใหม่
    trade_record = {
        "date_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "action": action,
        "symbol": symbol,
        "quantity": quantity,
        "price": price,
        "trade_type": trade_type,
        "status": status,
        "profit": profit
    }

    trade_data.append(trade_record)

    try:
        with open(log_file, 'w') as file:
            json.dump(trade_data, file, indent=4)
        cmd_notify(f"บันทึกข้อมูลการซื้อขาย {action} สำหรับ {symbol} เรียบร้อยแล้ว")
    except Exception as e:
        cmd_notify(f"ไม่สามารถบันทึกข้อมูลลงในไฟล์ {log_file} ได้: {str(e)}")


def place_buy_order(symbol, buy_usdt_amount, lowest_price, trade_status):
    global latest_balance
    fee_percentage = 0.1
    cmd_notify(f"ยอดเงินในบัญชี USDT ปัจจุบัน: {latest_balance['free']} USDT")

    with threading.Lock():
        try:
            # ตรวจสอบสถานะว่ามีการซื้ออยู่แล้วหรือไม่
            if trade_status.get(symbol, {}).get('status') in ['buying', 'bought']:
                cmd_notify(f"ไม่สามารถซื้อ {symbol} ได้ เพราะมีสถานะอยู่")
                return None, None

            # คำนวณยอดที่ต้องการซื้อรวมค่าธรรมเนียม
            buy_amount_with_fee = buy_usdt_amount + calculate_fee(buy_usdt_amount, fee_percentage)
            if latest_balance['free'] < buy_amount_with_fee:
                cmd_notify(f"ยอดเงินไม่พอซื้อ {symbol}, มี {latest_balance['free']} USDT แต่ต้องการ {buy_amount_with_fee}")
                return None, None

            # เป้าหมายราคาซื้อ
            target_buy_price = lowest_price * (1 + TARGET_BUY_PERCENT / 100)
            current_price = float(client.get_symbol_ticker(symbol=symbol)['price'])

            # ตรวจสอบราคาปัจจุบันกับ target_buy_price
            if current_price > target_buy_price:
                cmd_notify(f"ไม่ซื้อ {symbol}: ราคาปัจจุบัน {current_price} สูงกว่าเป้าหมาย {target_buy_price}")
                return None, None

            symbol_info = client.get_symbol_info(symbol)
            step_size = float(next(filter(lambda f: f['filterType'] == 'LOT_SIZE', symbol_info['filters']))['stepSize'])
            fee = calculate_fee(buy_usdt_amount, fee_percentage)
            usdt_amount_after_fee = buy_usdt_amount - fee
            quantity = round_step_size(usdt_amount_after_fee / current_price, step_size)

            # วางคำสั่งซื้อ
            order = client.create_order(symbol=symbol, side=SIDE_BUY, type=ORDER_TYPE_MARKET, quantity=quantity)
            buy_price = float(order['fills'][0]['price'])
            trade_status[symbol] = {'status': 'bought', 'buy_price': buy_price, 'quantity': quantity}
            save_status(trade_status)
            cmd_notify(f"ซื้อ {symbol} ที่ราคา {buy_price} จำนวน {quantity}")
            line_notify(f"ซื้อ {symbol} ที่ราคา {buy_price} จำนวน {quantity}")

            log_trade("buy", symbol, quantity, buy_price, "MARKET", "success")
            return buy_price, order

        except Exception as e:
            cmd_notify(f"ข้อผิดพลาดในการสั่งซื้อ {symbol}: {str(e)}")
            line_notify(f"ข้อผิดพลาดในการสั่งซื้อ {symbol}: {str(e)}")
            trade_status[symbol] = {'status': None}
            save_status(trade_status)
            return None, None



def place_sell_order(symbol, trade_status, highest_prices, lowest_prices, high_low_data):
    try:
        # ตรวจสอบว่ามีสถานะซื้ออยู่ก่อนที่จะขาย
        if trade_status.get(symbol, {}).get('status') != 'bought':
            cmd_notify(f"ไม่สามารถขาย {symbol} ได้ เนื่องจากยังไม่มีสถานะการซื้อ")
            return None

        current_price = float(client.get_symbol_ticker(symbol=symbol)['price'])
        buy_price = trade_status[symbol]['buy_price']
        highest_price = highest_prices.get(symbol)

        # ตรวจสอบว่ามีค่า highest_price ก่อนคำนวณ target_sell_price
        if highest_price is None:
            cmd_notify(f"{symbol}: ยังไม่มีจุดสูงสุดเพื่อคำนวณเป้าหมายการขาย")
            return None

        target_sell_price = highest_price * (1 - TARGET_SELL_PERCENT / 100)

        # กำหนดราคา Stop Loss
        soft_stop_loss_price = buy_price * (1 - SOFT_STOP_LOSS_PERCENT / 100)
        hard_stop_loss_price = buy_price * (1 - HARD_STOP_LOSS_PERCENT / 100)

        # ตรวจสอบเงื่อนไขการขาย
        if current_price <= hard_stop_loss_price:
            cmd_notify(f"{symbol}: ถึงจุด Hard Stop Loss ที่ {current_price} ขายขาดทุนทันที")
        elif soft_stop_loss_price <= target_sell_price <= buy_price and current_price == target_sell_price:
            # ขายเมื่อราคาปัจจุบันถึงเป้าหมายการขายและอยู่ในช่วง Soft Stop Loss
            cmd_notify(f"{symbol}: ขายตามเป้าหมายการขายที่ {target_sell_price} ซึ่งอยู่ระหว่าง Soft Stop Loss และราคาซื้อ")
        elif target_sell_price < soft_stop_loss_price:
            cmd_notify(f"{symbol}: ราคาเป้าหมายการขายต่ำกว่า Soft Stop Loss รอและไม่ขาย")
            return None

        # วางคำสั่งขายเมื่อเงื่อนไขเป็นจริง
        balance = client.get_asset_balance(asset=symbol.replace('USDT', ''))
        quantity = float(balance['free'])

        symbol_info = client.get_symbol_info(symbol)
        step_size = float(next(filter(lambda f: f['filterType'] == 'LOT_SIZE', symbol_info['filters']))['stepSize'])
        quantity = round_step_size(quantity, step_size)

        if quantity <= 0:
            cmd_notify(f"ไม่สามารถขาย {symbol} เนื่องจากจำนวนที่มีไม่เพียงพอสำหรับ LOT_SIZE ขั้นต่ำ")
            return None

        # สั่งขาย
        order = client.create_order(symbol=symbol, side=SIDE_SELL, type=ORDER_TYPE_MARKET, quantity=quantity)
        sell_price = float(order['fills'][0]['price'])
        profit = (sell_price - buy_price) * quantity - calculate_fee(sell_price * quantity)
        trade_status[symbol] = {'status': None, 'sell_price': sell_price, 'profit': profit}
        save_status(trade_status)
        cmd_notify(f"ขาย {symbol} ที่ราคา {sell_price} กำไรสุทธิ: {profit} USDT")
        line_notify(f"ขาย {symbol} ที่ราคา {sell_price} กำไรสุทธิ: {profit} USDT")

        log_trade("sell", symbol, quantity, sell_price, "MARKET", "success", profit)

        # รีเซ็ตจุดต่ำสุดเป็นราคาขายล่าสุด และจุดสูงสุดเป็น None เพื่อเริ่มติดตามใหม่
        reset_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        highest_prices[symbol] = None  # รอการอัปเดตใหม่สำหรับจุดสูงสุด
        lowest_prices[symbol] = sell_price  # ตั้งจุดขายล่าสุดเป็นจุดต่ำสุดใหม่
        high_low_data[symbol] = {
            'high': None,  # None สำหรับจุดสูงสุด
            'low': lowest_prices[symbol],
            'reset_time': reset_time
        }
        save_high_low(high_low_data)
        cmd_notify(f"รีเซ็ตจุดต่ำสุดของ {symbol} เป็นราคา {sell_price} และรออัปเดตจุดสูงสุดใหม่ เมื่อ {reset_time}")

        return order

    except Exception as e:
        cmd_notify(f"ข้อผิดพลาดในการสั่งขาย {symbol}: {str(e)}")
        line_notify(f"ข้อผิดพลาดในการสั่งขาย {symbol}: {str(e)}")
        return None



def handle_socket_message(msg, trade_status, buy_usdt_amount, target_prices, highest_prices, lowest_prices, websocket_prices, high_low_data, last_notified_prices):
    try:
        symbol = msg['s']
        current_price = float(msg['c'])
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        websocket_prices[symbol] = current_price

        # ตรวจสอบการเปลี่ยนแปลงราคาที่สำคัญ
        if symbol in last_notified_prices and abs(last_notified_prices[symbol] - current_price) < (last_notified_prices[symbol] * 0.00000001):
            return

        last_notified_prices[symbol] = current_price
        cmd_notify(f"{now} - {symbol}: ราคาปัจจุบันคือ {current_price}")

        # ตรวจสอบสถานะของคู่เงินนี้
        symbol_status = trade_status.get(symbol, {}).get('status')

        # ตั้งเป้าหมายการซื้อใหม่เมื่อสถานะเป็น null
        if symbol_status is None:
            # ตั้งเป้าหมายการซื้อใหม่โดยใช้ราคาต่ำสุดที่อัปเดต
            if symbol not in lowest_prices or current_price < lowest_prices[symbol]:
                lowest_prices[symbol] = current_price
            target_buy_price = lowest_prices[symbol] * (1 + TARGET_BUY_PERCENT / 100)
            target_prices[symbol]['buy'] = target_buy_price
            cmd_notify(f"ตั้งเป้าหมายการซื้อใหม่สำหรับ {symbol} ที่ราคา {target_buy_price}")

            # ตรวจสอบเป้าหมายการซื้อ
            if current_price >= target_prices[symbol]['buy']:
                cmd_notify(f"{symbol}: ราคาถึงเป้าหมายการซื้อแล้วที่ {current_price}")
                buy_price, buy_order = place_buy_order(symbol, buy_usdt_amount, lowest_prices[symbol], trade_status)
                if buy_order:
                    target_sell_price = buy_price * (1 + TARGET_SELL_PERCENT / 100)
                    target_prices[symbol]['sell'] = target_sell_price
                    del target_prices[symbol]['buy']  # ลบเป้าหมายการซื้อหลังจากซื้อสำเร็จ
                    cmd_notify(f"{symbol}: ตั้งเป้าหมายการขายที่ {target_sell_price}")


        # ถ้าคู่เงินนี้มีการซื้อแล้ว ทำงานในโหมดขาย
        elif symbol_status == 'bought':
            # อัปเดตจุดสูงสุด (High) และบันทึกในไฟล์
            if highest_prices[symbol] is None or current_price > highest_prices[symbol]:
                highest_prices[symbol] = current_price
                target_sell_price = highest_prices[symbol] * (1 - TARGET_SELL_PERCENT / 100)
                target_prices[symbol]['sell'] = target_sell_price
                high_low_data[symbol] = high_low_data.get(symbol, {})
                high_low_data[symbol]['high'] = highest_prices[symbol]
                save_high_low(high_low_data)
                cmd_notify(f"ราคาสูงสุดใหม่ของ {symbol}: {highest_prices[symbol]}, ตั้งเป้าขายที่ {target_sell_price}")

            # ตรวจสอบการขายตามเป้าหมายหรือ Stop-loss
            buy_price = trade_status[symbol]['buy_price']
            # ตรวจสอบว่ามีค่า highest_price ก่อนทำการคำนวณ target_sell_price
            if highest_prices[symbol] is not None:
                target_sell_price = highest_prices[symbol] * (1 - TARGET_SELL_PERCENT / 100)
                soft_stop_loss_price = buy_price * (1 - SOFT_STOP_LOSS_PERCENT / 100)
                hard_stop_loss_price = buy_price * (1 - HARD_STOP_LOSS_PERCENT / 100)

                # เงื่อนไข Hard Stop Loss: ขายทันทีเมื่อราคาต่ำกว่า Hard Stop Loss
                if current_price <= hard_stop_loss_price:
                    cmd_notify(f"{symbol}: ราคาลดลงถึง Hard Stop Loss ที่ {current_price}, ขายขาดทุนทันที")
                    line_notify(f"{symbol}: ราคาลดลงถึง Hard Stop Loss ที่ {current_price}, ขายขาดทุนทันที")
                    place_sell_order(symbol, trade_status, highest_prices, lowest_prices, high_low_data)

                # ตรวจสอบเงื่อนไข Soft Stop Loss
                elif soft_stop_loss_price <= target_sell_price <= buy_price:
                    # ราคาเป้าหมายอยู่ระหว่าง Soft Stop Loss และราคาซื้อ
                    if current_price <= target_sell_price:
                        cmd_notify(f"{symbol}: ราคาเป้าหมายการขาย ({target_sell_price}) อยู่ระหว่าง Soft Stop Loss และราคาซื้อ และราคาปัจจุบันถึงเป้าหมาย ขายเพื่อทำกำไร")
                        line_notify(f"{symbol}: ราคาเป้าหมายการขาย ({target_sell_price}) อยู่ระหว่าง Soft Stop Loss และราคาซื้อ และราคาปัจจุบันถึงเป้าหมาย ขายเพื่อทำกำไร")
                        place_sell_order(symbol, trade_status, highest_prices, lowest_prices, high_low_data)
                    else:
                        # ราคาปัจจุบันยังไม่ถึงเป้าหมายการขาย
                        cmd_notify(f"{symbol}: ราคาเป้าหมายการขาย ({target_sell_price}) อยู่ในช่วง Soft Stop Loss รอให้ราคาปัจจุบันถึงเป้าหมายก่อนขาย")
                elif target_sell_price < soft_stop_loss_price:
                    # ราคาเป้าหมายการขายต่ำกว่า Soft Stop Loss รอไม่ขาย
                    cmd_notify(f"{symbol}: ราคาเป้าหมายการขาย ({target_sell_price}) ต่ำกว่า Soft Stop Loss รอและไม่ขาย")

                elif target_sell_price > buy_price:
                    # ราคาเป้าหมายการขายสูงกว่าราคาซื้อ ขายได้ทันทีเมื่อถึงเป้าหมาย
                    if current_price <= target_sell_price:
                        cmd_notify(f"{symbol}: ราคาเป้าหมายการขาย ({target_sell_price}) สูงกว่าราคาซื้อ ขายเพื่อทำกำไรทันที")
                        line_notify(f"{symbol}: ราคาเป้าหมายการขาย ({target_sell_price}) สูงกว่าราคาซื้อ ขายเพื่อทำกำไรทันที")
                        place_sell_order(symbol, trade_status, highest_prices, lowest_prices, high_low_data)

    except Exception as e:
        cmd_notify(f"ข้อผิดพลาด: {str(e)}")
        line_notify(f"ข้อผิดพลาด: {str(e)}")



# ฟังก์ชันสำหรับเริ่มการติดตามและเทรด
def monitor_and_trade_multiple_pairs(pairs, buy_usdt_amount):
    line_notify("เริ่มต้นการรันโปรแกรม Monitor และเทรดหลายคู่สกุลเงิน")
    trade_status = load_status()
    high_low_data = load_high_low()  # โหลดข้อมูล High และ Low จากไฟล์
    target_prices = {}
    highest_prices = {symbol: high_low_data.get(symbol, {}).get('high', 0) for symbol in pairs}
    lowest_prices = {symbol: high_low_data.get(symbol, {}).get('low', float('inf')) for symbol in pairs}
    websocket_prices = {}
    last_notified_prices = {}

    # เริ่ม WebSocket manager
    twm = ThreadedWebsocketManager(api_key=api_key, api_secret=api_secret)
    twm.start()

    for symbol in pairs:
        twm.start_symbol_ticker_socket(
            callback=lambda msg: handle_socket_message(
                msg, trade_status, buy_usdt_amount, target_prices, highest_prices, lowest_prices, websocket_prices, high_low_data,last_notified_prices
            ),
            symbol=symbol.lower()
        )
        target_prices[symbol] = {}

    try:
        twm.join()
    except Exception as e:
        twm.stop()

# เริ่มต้นโปรแกรม
symbols = [ "XRPUSDT", "DOTUSDT","ADAUSDT", "DOGEUSDT","SHIBUSDT", "LINKUSDT", "AVAXUSDT", "SOLUSDT"]  # กำหนดสัญลักษณ์ที่ต้องการเทรด
buy_usdt_amount = 30  # จำนวน USDT ที่ต้องการใช้ซื้อ

balance_thread = threading.Thread(target=update_balance)
balance_thread.daemon = True
balance_thread.start()

monitor_and_trade_multiple_pairs(symbols, buy_usdt_amount)
