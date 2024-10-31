import json
import os
import requests
import asyncio
import threading
import time
import datetime
from binance import ThreadedWebsocketManager
from binance.client import Client
from binance.enums import SIDE_BUY, SIDE_SELL, ORDER_TYPE_MARKET
from binance.helpers import round_step_size
#  14/10   20:38
# เริ่มต้นการเชื่อมต่อกับ Binance API   
api_key = 'uMGWWDUKpYQQG3UhgnK2gdpfvlNWBIk8PYGjAYbJf0qrAovfXpu8sWL8ITHhxC9O'
api_secret = 'Hc1MFkxFHvwmu3FJepBv3KmZEgoEvq1KuLtNng9t37FAKl0oUWHK8lZg6nM6Hwzk'
client = Client(api_key, api_secret)

# ตัวแปรสำหรับเก็บยอดเงินล่าสุด
latest_balance = {'free': 0.0}

def line_notify(message, usdt_used=None, usdt_received=None):
    token = 'Th3wu3khl7GoYWMHiy9TZ3ARazsQ1hbViIe7WkQIFdL'
    url = 'https://notify-api.line.me/api/notify'
    headers = {
        'Authorization': f'Bearer {token}'
    }
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if usdt_used is not None:
        message += f"\nUSDT ที่ใช้ในการซื้อ: {usdt_used:.3f}"
    if usdt_received is not None:
        message += f"\nUSDT ที่ได้รับจากการขาย: {usdt_received:.3f}"
    
    # ตรวจสอบว่าข้อความที่จะแจ้งเตือนเหมือนเดิมหรือไม่เพื่อป้องกันการแจ้งซ้ำซ้อน
    previous_message = getattr(line_notify, 'previous_message', None)
    if previous_message == message:
        cmd_notify(f"แจ้งเตือนถูกระงับเพราะซ้ำซ้อน: {message}")
        return
    
    message = f"{now}: {message}"
    data = {'message': message}
    
    # ส่งการแจ้งเตือนผ่าน Line
    response = requests.post(url, headers=headers, data=data)
    
    if response.status_code != 200:
        print(f"การแจ้งเตือน Line ไม่สำเร็จ: {response.status_code}")
    
    # บันทึกข้อความล่าสุดที่ส่งไปแจ้งเตือน
    line_notify.previous_message = message

    return response


# ฟังก์ชันสำหรับอัปเดตยอดเงินในบัญชีทุกๆ 30 วินาที
def update_balance():
    global latest_balance
    while True:
        try:
            balance = client.get_asset_balance(asset='USDT')
            latest_balance['free'] = float(balance['free'])
            cmd_notify(f"ยอดเงินในบัญชี (อัปเดตล่าสุด): {latest_balance['free']} USDT")
        except Exception as e:
            cmd_notify(f"ข้อผิดพลาดในการอัปเดตยอดเงินในบัญชี: {str(e)}")
        time.sleep(30)

def check_saved_data(file_name):
    try:
        with open(file_name, 'r') as file:
            data = json.load(file)
            cmd_notify(f"ข้อมูลที่ถูกบันทึกใน {file_name}: {json.dumps(data, indent=4)}")
            return data
    except Exception as e:
        cmd_notify(f"ข้อผิดพลาดในการอ่านไฟล์ {file_name}: {str(e)}")
        return None

# ฟังก์ชันสำหรับการแจ้งเตือนใน CMD
def cmd_notify(message):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{now} - {message}")

# ฟังก์ชันสำหรับตรวจสอบข้อมูลของแต่ละคู่เงิน
def validate_trade_data(trade_data):
    valid_data = {}
    invalid_pairs = []

    for symbol, data in trade_data.items():
        # ตรวจสอบว่า trade data มีข้อมูลที่สำคัญครบถ้วนหรือไม่
        if 'status' in data and 'buy_price' in data and 'buy_time' in data and 'quantity' in data and 'buy_number' in data:
            valid_data[symbol] = data  # ข้อมูลสมบูรณ์ เก็บไว้
        else:
            invalid_pairs.append(symbol)  # ข้อมูลไม่สมบูรณ์ บันทึกชื่อคู่เงินที่มีปัญหา

    return valid_data, invalid_pairs

# ฟังก์ชันสำหรับบันทึกสถานะลงไฟล์ JSON พร้อมการลบข้อมูลที่ไม่สมบูรณ์
def save_status(trade_data, file_name):
    try:
        # ตรวจสอบความสมบูรณ์ของข้อมูลก่อนบันทึก
        valid_data, invalid_pairs = validate_trade_data(trade_data)

        # หากมีข้อมูลที่ไม่สมบูรณ์จะแจ้งเตือนและลบทิ้ง
        if invalid_pairs:
            cmd_notify(f"ข้อมูลของคู่เงินต่อไปนี้ไม่สมบูรณ์และถูกลบออก: {', '.join(invalid_pairs)}")

        # บันทึกข้อมูลที่สมบูรณ์กลับไปยังไฟล์
        with open(file_name, 'w') as file:
            json.dump(valid_data, file, indent=4)

        cmd_notify(f"บันทึกสถานะไปยังไฟล์ {file_name} เรียบร้อยแล้ว")

    except Exception as e:
        cmd_notify(f"ข้อผิดพลาดในการบันทึกสถานะ: {str(e)}")

# ฟังก์ชันสำหรับโหลดสถานะจากไฟล์ JSON พร้อมการตรวจสอบข้อมูลเสียหาย
def load_status(file_name):
    try:
        # หากไม่มีไฟล์ ให้สร้างไฟล์ใหม่และคืนค่าเป็นข้อมูลว่าง
        if not os.path.exists(file_name):
            cmd_notify(f"ไม่มีไฟล์ {file_name} กำลังสร้างไฟล์ใหม่...")
            with open(file_name, 'w') as file:
                json.dump({}, file)
            return {}

        # โหลดข้อมูลจากไฟล์ที่มีอยู่
        with open(file_name, 'r') as file:
            trade_data = json.load(file)

            # ตรวจสอบความสมบูรณ์ของข้อมูลที่โหลดมา
            valid_data, invalid_pairs = validate_trade_data(trade_data)

            # หากพบข้อมูลที่เสียหายจะทำการลบออกและบันทึกเฉพาะข้อมูลที่สมบูรณ์
            if invalid_pairs:
                cmd_notify(f"ข้อมูลของคู่เงินต่อไปนี้เสียหายและถูกลบออก: {', '.join(invalid_pairs)}")
                save_status(valid_data, file_name)  # บันทึกข้อมูลที่สมบูรณ์กลับไปยังไฟล์

            return valid_data

    except json.JSONDecodeError:
        cmd_notify(f"ไฟล์ {file_name} เสียหายบางส่วน กำลังพยายามกู้คืนข้อมูล...")
        return {}  # กรณีที่ไฟล์ไม่สามารถอ่านได้

    except Exception as e:
        cmd_notify(f"ข้อผิดพลาดในการโหลดสถานะ: {str(e)}")
        return {}
    
# ฟังก์ชันสำหรับบันทึกข้อมูลการซื้อขาย
def log_trade(action, symbol, quantity, price, trade_type, status, profit=None, buy_number=1, usdt_used=None, usdt_received=None):
    log_file = 'trade_log.json'
    trade_record = {
        "date_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "action": action,
        "symbol": symbol,
        "quantity": quantity,
        "price": price,
        "trade_type": trade_type,
        "status": status,
        "profit": profit,
        "buy_number": buy_number,
        "usdt_used": usdt_used,
        "usdt_received": usdt_received
    }
    try:
        if not os.path.exists(log_file):
            with open(log_file, 'w') as file:
                json.dump([trade_record], file, indent=4)
        else:
            with open(log_file, 'r') as file:
                trade_data = json.load(file)
            trade_data.append(trade_record)
            with open(log_file, 'w') as file:
                json.dump(trade_data, file, indent=4)
        cmd_notify(f"บันทึกข้อมูลการซื้อขาย {action} สำหรับ {symbol} ไม้ {buy_number} เรียบร้อยแล้ว")
    except Exception as e:
        cmd_notify(f"ไม่สามารถบันทึกข้อมูลลงในไฟล์ {log_file} ได้: {str(e)}")

def place_buy_order(symbol, usdt_amount, price, trade_status, trade_status2, file_name, buy_number=1):
    global latest_balance
    fee_percentage = 0.1
    with threading.Lock():
        try:
            # ตรวจสอบยอดเงินในบัญชีก่อนการซื้อ
            if latest_balance['free'] < usdt_amount:
                cmd_notify(f"ยอดเงินในบัญชี USDT ไม่เพียงพอสำหรับซื้อ {symbol}, มี {latest_balance['free']} USDT")
                return None, None

            # ตรวจสอบสถานะของไม้ 2 หากยังไม่ขาย ห้ามซื้อไม้ 1 เพิ่ม
            if buy_number == 1 and trade_status2.get(symbol, {}).get('status') == 'bought':
                cmd_notify(f"ไม่สามารถซื้อ {symbol} ไม้ 1 ได้เนื่องจากไม้ 2 ยังไม่ได้ขาย")
                return None, None

            if trade_status.get(symbol, {}).get('status') in ['buying', 'bought']:
                cmd_notify(f"ไม่สามารถซื้อ {symbol} ได้ เพราะยังมีคำสั่งซื้อหรือคำสั่งขายก่อนหน้าอยู่")
                return None, None
            
            # แสดงยอดเงินและค่าธรรมเนียม
            fee = usdt_amount * (fee_percentage / 100)
            usdt_amount_after_fee = usdt_amount - fee
            cmd_notify(f"ยอดเงินที่ใช้สำหรับซื้อ: {usdt_amount}, ค่าธรรมเนียม: {fee}")

            trade_status[symbol] = {'status': 'buying', 'buy_number': buy_number}
            save_status(trade_status, file_name)
            check_saved_data(file_name)

            symbol_info = client.get_symbol_info(symbol)
            step_size = float(next(filter(lambda f: f['filterType'] == 'LOT_SIZE', symbol_info['filters']))['stepSize'])
            quantity = round_step_size(usdt_amount_after_fee / price, step_size)

            order = client.create_order(symbol=symbol, side=SIDE_BUY, type=ORDER_TYPE_MARKET, quantity=quantity)

            total_usdt_spent = quantity * price

            cmd_notify(f"ซื้อ {symbol} ไม้ {buy_number} ใช้ USDT ทั้งหมด {total_usdt_spent} จำนวน {quantity} สำเร็จ")

            trade_status[symbol] = {
                'status': 'bought',
                'buy_price': price,
                'buy_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'quantity': quantity,
                'buy_number': buy_number
            }
            save_status(trade_status, file_name)
            check_saved_data(file_name)
            log_trade("buy", symbol, quantity, price, "MARKET", "success", buy_number=buy_number)
            return price, order
        
        except Exception as e:
            cmd_notify(f"ข้อผิดพลาดในการสั่งซื้อ {symbol}: {str(e)}")
            cmd_notify(f"สถานะการซื้อขายสำหรับ {symbol} ไม่ได้รับการอัปเดตเนื่องจากเกิดข้อผิดพลาด")
            return None, None

# ฟังก์ชันสำหรับคำนวณราคาขายเป้าหมาย
def calculate_target_sell_price(buy_price, rise_percentage, fee_percentage=0.1):
    return buy_price * (1 + (rise_percentage / 100)) * (1 + (fee_percentage / 100))

def place_sell_order(symbol, trade_status, rise_percentage,trade_status1, trade_status2,websocket_prices, file_name, buy_number=1):
    try:
        fee_percentage = 0.1  # ค่าธรรมเนียม 0.1%
        # ตรวจสอบสถานะการซื้อก่อน
        if buy_number == 1:
            trade_status = trade_status1
        elif buy_number == 2:
            trade_status = trade_status2

        # ตรวจสอบสถานะการซื้อก่อน
        if trade_status.get(symbol, {}).get('status') != 'bought':
            cmd_notify(f"ไม่สามารถขาย {symbol} ได้ เนื่องจากยังไม่มีสถานะการซื้อ")
            return None

        # ดึงราคาปัจจุบันและตรวจสอบยอดเงินคงเหลือ
        current_price = websocket_prices.get(symbol)

        if current_price is None:
            cmd_notify(f"ไม่พบราคาจาก WebSocket สำหรับ {symbol}")
            return

        # ตรวจสอบว่ากำลังขายไม้ไหน
        if buy_number == 1:
            buy_price = trade_status[symbol]['buy_price']
            quantity = trade_status[symbol].get('quantity', 0)  # ตรวจสอบยอดไม้ 1
        elif buy_number == 2:
            buy_price = trade_status[symbol]['buy_price']
            quantity = trade_status[symbol].get('quantity', 0)  # ตรวจสอบยอดไม้ 2

        target_sell_price = calculate_target_sell_price(buy_price, rise_percentage)
        cmd_notify(f"ราคาเป้าหมายสำหรับขาย buy {buy_number} {symbol}: {target_sell_price}")

        # ตรวจสอบว่าราคาปัจจุบันถึงราคาขายเป้าหมายหรือยัง
        if current_price < target_sell_price:
            cmd_notify(f"ราคาปัจจุบันของ {symbol} ยังไม่ถึงเป้าหมายการขาย ({target_sell_price})")
            return None

        if quantity <= 0:
            cmd_notify(f"ยอดเหรียญ {symbol} ที่บันทึกไว้ไม่เพียงพอที่จะทำการขาย")
            return None

        # ตรวจสอบยอดเหรียญคงเหลือในบัญชีก่อนที่จะขาย
        account_balance = client.get_asset_balance(asset=symbol[:-4])  # ลบ 'USDT' เพื่อดึงชื่อเหรียญ
        free_balance = float(account_balance['free'])

        if free_balance < quantity:
            quantity = free_balance  # ปรับจำนวนที่จะขายตามยอดเงินในบัญชีจริง
            cmd_notify(f"ปรับจำนวนที่จะขายให้ตรงกับยอดที่มีในบัญชี: {quantity}")

        # คำนวณจำนวนที่สามารถขายได้จริง และส่งคำสั่งขาย
        symbol_info = client.get_symbol_info(symbol)
        step_size = float(next(filter(lambda f: f['filterType'] == 'LOT_SIZE', symbol_info['filters']))['stepSize'])
        quantity = round_step_size(quantity, step_size)

        order = client.create_order(symbol=symbol, side=SIDE_SELL, type=ORDER_TYPE_MARKET, quantity=quantity)

        # ตรวจสอบสถานะการขาย
        if order['status'] == 'FILLED':
            sell_price = float(order['fills'][0]['price'])
            total_usdt_received = quantity * sell_price
            fee = total_usdt_received * (fee_percentage / 100)
            net_usdt_received = total_usdt_received - fee
                
            cmd_notify(f"ขาย {symbol} ไม้ {buy_number} ได้รับ USDT {net_usdt_received} จำนวน {quantity} สำเร็จ")

            # คำนวณกำไร
            profit = (sell_price - buy_price) * quantity - fee

            # อัปเดตสถานะการขาย
            trade_status[symbol] = {
                'status': 'sold',
                'sell_price': sell_price,
                'sell_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'profit': profit
            }

            # บันทึกสถานะและการขาย
            save_status(trade_status, file_name)
            check_saved_data(file_name)  # ตรวจสอบข้อมูลที่บันทึก
            log_trade("sell", symbol, quantity, sell_price, "MARKET", "success", profit, buy_number=buy_number)
            line_notify(f"ขาย {symbol} ไม้ {buy_number} จำนวน {quantity:.3f} ที่ราคา {sell_price:.3f} สำเร็จ", usdt_received=net_usdt_received)

            return order
        else:
            cmd_notify(f"การขาย {symbol} ล้มเหลว: สถานะ {order['status']}")
            return None

    except Exception as e:
        cmd_notify(f"ข้อผิดพลาดในการสั่งขาย {symbol}: {str(e)}")
        return None    

def handle_socket_message(msg, trade_status1, trade_status2, buy_usdt_amount, target_prices1, target_prices2, highest_prices, last_notified_prices, websocket_prices):
    try:
        symbol = msg.get('s')
        current_price = msg.get('c')

        # ตรวจสอบว่าข้อมูลราคาถูกต้องหรือไม่
        if symbol is None or current_price is None:
            cmd_notify(f"ไม่พบข้อมูลที่ถูกต้องใน WebSocket message")
            return
        
        # ตรวจสอบว่ามีราคาปัจจุบันหรือไม่ก่อนที่จะดำเนินการ
        current_price = msg.get('c')
        if current_price is None:
            cmd_notify(f"ไม่สามารถดึงราคาปัจจุบันสำหรับ {symbol} ได้")
            return
        
        # แปลงค่าเป็น float และประมวลผลข้อมูลต่อไป
        try:
            current_price = float(current_price)
        except ValueError:
            cmd_notify(f"ไม่สามารถแปลงราคาปัจจุบันสำหรับ {symbol} เป็นตัวเลขได้: {current_price}")
            return

        websocket_prices[symbol] = current_price

        # เพิ่มการตรวจสอบสำหรับ buy 1
        if trade_status1.get(symbol, {}).get('status') == 'bought' and trade_status2.get(symbol, {}).get('status') == 'bought':
            cmd_notify(f"รอให้ขาย buy 2 ก่อนการซื้อขาย buy 1 สำหรับ {symbol}")
            return

        # ตรวจสอบการเปลี่ยนแปลงราคาว่ามีมากพอที่จะสนใจหรือไม่
        if symbol in last_notified_prices and abs(last_notified_prices[symbol] - current_price) < (last_notified_prices[symbol] * 0.00000000005):
            return

        last_notified_prices[symbol] = current_price
        cmd_notify(f"{datetime.datetime.now()} - {symbol}: ราคาปัจจุบันคือ {current_price}")

        # ตรวจสอบราคาสูงสุดและตั้งราคาเป้าหมายการซื้อ
        if symbol not in highest_prices or current_price > highest_prices[symbol]:
            highest_prices[symbol] = current_price
            target_buy_price1 = highest_prices[symbol] * (1 - drop_percentage / 100)
            target_prices1[symbol] = {'buy': target_buy_price1}  # ใช้การตั้งค่าให้แน่ใจว่ามีข้อมูล

            cmd_notify(f"ราคาสูงสุดใหม่ของ {symbol} คือ {highest_prices[symbol]} USDT, ตั้งราคาซื้อ buy 1 ที่ {target_buy_price1} USDT")

        # Logic สำหรับ buy 1
        if trade_status1.get(symbol, {}).get('status') == 'bought':
            buy_price1 = trade_status1[symbol].get('buy_price')
            if buy_price1 is None:
                cmd_notify(f"ไม่พบราคาซื้อสำหรับ {symbol}")
                return
            
            target_sell_price1 = calculate_target_sell_price(buy_price1, rise_percentage)
            target_prices1[symbol]['sell'] = target_sell_price1
            cmd_notify(f"ตั้งราคาขาย buy 1 {symbol} ที่ {target_sell_price1} USDT")

        if 'buy' in target_prices1.get(symbol, {}):  # ตรวจสอบการเข้าถึงให้ดีขึ้น
            if current_price <= target_prices1[symbol]['buy']:

                if latest_balance['free'] < buy_usdt_amount:
                    new_drop_percentage = drop_percentage
                    new_target_buy_price = current_price * (1 - new_drop_percentage / 100)
                    target_prices1[symbol]['buy'] = new_target_buy_price
                    cmd_notify(f"ไม่มีเงินเพียงพอ ปรับเป้าหมายราคาซื้อใหม่สำหรับ {symbol} จากราคาปัจจุบัน {current_price:.8f} USDT เป็น {new_target_buy_price:.8f} USDT")
                    return
                else:

                    buy_price1, buy_order1 = place_buy_order(symbol, buy_usdt_amount, current_price, trade_status1, trade_status2, 'trade_status1.json', buy_number=1)
                    if buy_order1:
                        target_sell_price1 = calculate_target_sell_price(buy_price1, rise_percentage)
                        target_prices1[symbol]['sell'] = target_sell_price1
                        del target_prices1[symbol]['buy']
                        line_notify(f"ซื้อ {symbol} ไม้ 1 จำนวน {float(buy_order1['origQty']):.3f} ที่ราคา {buy_price1:.3f} สำเร็จ", usdt_used=float(buy_order1['cummulativeQuoteQty']))
                        cmd_notify(f"ตั้งราคาขาย buy 1 {symbol} ที่ {target_sell_price1} USDT")

        # Logic สำหรับขาย buy 1
        if 'sell' in target_prices1.get(symbol, {}) and current_price >= target_prices1[symbol]['sell']:
            sell_order1 = place_sell_order(symbol, trade_status1, rise_percentage, trade_status1,websocket_prices, trade_status2, 'trade_status1.json', buy_number=1)
            if sell_order1:
                del target_prices1[symbol]['sell']
                line_notify(f"ขาย {symbol} ไม้ 1 จำนวน {sell_order1['origQty']} ที่ราคา {sell_order1['fills'][0]['price']} สำเร็จ", usdt_received=sell_order1['cummulativeQuoteQty'])                
                cmd_notify(f"ขาย buy 1 {symbol} สำเร็จที่ {current_price} USDT")

        # Trigger buy 2 if buy 1 exists
        if trade_status1.get(symbol, {}).get('status') == 'bought' and symbol in highest_prices:
            target_buy_price2 = trade_status1[symbol]['buy_price'] * (1 - 9 / 100)
            target_prices2[symbol] = {'buy': target_buy_price2}  # ตั้งค่าให้แน่ใจว่ามีข้อมูล

            cmd_notify(f"ตั้งราคาซื้อ buy 2 สำหรับ {symbol} ที่ {target_buy_price2} USDT")

        # ตรวจสอบสถานะของ buy 2
        if trade_status2.get(symbol, {}).get('status') == 'sold':
            # ถ้า `ไม้ 2` ถูกขายแล้ว จะสามารถกลับมาซื้อได้
            if current_price <= target_prices2[symbol]['buy']:
                buy_price2, buy_order2 = place_buy_order(symbol, buy_usdt_amount, current_price, trade_status2, trade_status1, 'trade_status2.json', buy_number=2)
                if buy_order2:
                    target_sell_price2 = calculate_target_sell_price(buy_price2, rise_percentage)
                    target_prices2[symbol]['sell'] = target_sell_price2
                    del target_prices2[symbol]['buy']
                    cmd_notify(f"ตั้งราคาขาย buy 2 {symbol} ที่ {target_sell_price2} USDT")

        # ตรวจสอบราคาไม้ 1 ว่าลดลงต่ำกว่า 9% หรือไม่
        if trade_status1.get(symbol, {}).get('status') == 'bought':
            buy_price1 = trade_status1[symbol]['buy_price']
            if current_price <= buy_price1 * (1 - 0.09):  # หากราคาลดลงต่ำกว่า 9%
                cmd_notify(f"ราคาของ {symbol} ลดลงมากกว่า 9% ทำการซื้อ buy 2 ทันที")
                try:
                    buy_price2, buy_order2 = place_buy_order(symbol, buy_usdt_amount, current_price, trade_status2, trade_status1, 'trade_status2.json', buy_number=2)
                except TypeError as e:
                    cmd_notify(f"เกิดข้อผิดพลาดใน WebSocket สำหรับ {symbol}: {str(e)}")
                
                if buy_order2:
                    target_sell_price2 = calculate_target_sell_price(buy_price2, rise_percentage)
                    target_prices2[symbol]['sell'] = target_sell_price2
                    line_notify(f"ซื้อ {symbol} ไม้ 2 จำนวน {float(buy_order2['origQty']):.3f} ที่ราคา {buy_price2:.3f} สำเร็จ", usdt_used=float(buy_order2['cummulativeQuoteQty']))
                    cmd_notify(f"ตั้งราคาขาย buy 2 {symbol} ที่ {target_sell_price2} USDT")

        # Logic สำหรับ buy 2
        if 'sell' in target_prices2.get(symbol, {}) and current_price >= target_prices2[symbol]['sell']:
            sell_order2 = place_sell_order(symbol, trade_status2, rise_percentage, trade_status1,websocket_prices, trade_status2, 'trade_status2.json', buy_number=2)
            if sell_order2:
                del target_prices2[symbol]['sell']
                line_notify(f"ขาย {symbol} ไม้ 2 จำนวน {sell_order2['origQty']} สำเร็จที่ราคา {sell_order2['fills'][0]['price']} USDT", usdt_received=sell_order2['cummulativeQuoteQty'])
                cmd_notify(f"ขาย buy 2 {symbol} สำเร็จที่ {current_price} USDT")

    except KeyError as e:
        cmd_notify(f"KeyError: ข้อมูลขาดหายสำหรับ {symbol}: {str(e)}")
    except Exception as e:
        cmd_notify(f"ข้อผิดพลาดใน WebSocket สำหรับ {symbol}: {str(e)}")

# ในฟังก์ชัน start_combined_socket และ start_socket
def start_combined_socket(pairs, twm, trade_status1, trade_status2, buy_usdt_amount, target_prices1, target_prices2, highest_prices, last_notified_prices, websocket_prices):
    try:
        streams = [f"{symbol.lower()}@ticker" for symbol in pairs]
        twm.start_multiplex_socket(
            callback=lambda msg: handle_socket_message(
                msg, trade_status1, trade_status2, buy_usdt_amount, target_prices1, target_prices2, highest_prices, last_notified_prices, websocket_prices
            ),
            streams=streams
        )
        cmd_notify("เปิด WebSocket รวมเรียบร้อยแล้ว")
    except Exception as e:
        cmd_notify(f"เกิดข้อผิดพลาดในการเริ่ม WebSocket รวม: {str(e)}")

def start_socket(symbol, twm, trade_status1, trade_status2, buy_usdt_amount, target_prices1, target_prices2, highest_prices, last_notified_prices, websocket_prices):
    try:
        twm.start_symbol_ticker_socket(
            callback=lambda msg: handle_socket_message(
                msg, trade_status1, trade_status2, buy_usdt_amount, target_prices1, target_prices2, highest_prices, last_notified_prices, websocket_prices
            ),
            symbol=symbol.lower()  # ใช้สัญลักษณ์คู่เงินเป็นพารามิเตอร์
        )
        cmd_notify(f"เปิด WebSocket สำหรับ {symbol} เรียบร้อยแล้ว")
    except Exception as e:
        cmd_notify(f"เกิดข้อผิดพลาดในการเริ่ม WebSocket สำหรับ {symbol}: {str(e)}")

# ฟังก์ชันที่ใช้สำหรับหยุด WebSocket ทั้งหมด
async def stop_socket(twm):
    try:
        if twm is not None:
            await twm.stop()
            cmd_notify("ปิด WebSocket เรียบร้อยแล้ว")
        else:
            cmd_notify("ไม่มี WebSocket ที่กำลังทำงานอยู่")
    except Exception as e:
        cmd_notify(f"ข้อผิดพลาดในการปิด WebSocket: {str(e)}")

def calculate_stop_loss_price(buy_price, loss_percentage):
    return buy_price * (1 - (loss_percentage / 100))

def check_trade_status(trade_status1, trade_status2, rise_percentage, loss_percentage, websocket_prices):
    while True:
        try:
            cmd_notify("ตรวจสอบประวัติการซื้อขาย...")
            for symbol, status1 in trade_status1.items():
                if status1.get('status') == 'bought':
                    if 'buy_price' not in status1:
                        cmd_notify(f"ไม่พบ buy_price ใน trade_status สำหรับ {symbol}")
                        continue
                    current_price = websocket_prices.get(symbol)
                    if current_price is None:
                        cmd_notify(f"ไม่พบราคาจาก WebSocket สำหรับ {symbol}")
                        continue

                    target_sell_price1 = calculate_target_sell_price(status1['buy_price'], rise_percentage)
                    stop_loss_price1 = calculate_stop_loss_price(status1['buy_price'], loss_percentage)

                    cmd_notify(f"{symbol}: ราคาปัจจุบันคือ {current_price}, ราคาที่ต้องการขาย buy 1 คือ {target_sell_price1}, ราคาหยุดขาดทุนคือ {stop_loss_price1}")

                    # ตรวจสอบราคาหยุดขาดทุน
                    if current_price <= stop_loss_price1:
                        # ตรวจสอบว่า buy 2 ถูกขายก่อนที่ buy 1 จะถูกขายหรือไม่
                        if trade_status2.get(symbol, {}).get('status') == 'bought':
                            cmd_notify(f"รอให้ขาย buy 2 ก่อนการขาย buy 1 สำหรับ {symbol}")
                            continue  # รอจนกว่า buy 2 จะขาย
                        
                        # ขาย buy 1 ทันทีที่ราคาลดต่ำกว่า stop-loss
                        place_sell_order(symbol, trade_status1, rise_percentage, trade_status1, trade_status2,websocket_prices, 'trade_status1.json', buy_number=1)
                        cmd_notify(f"ขาย buy 1 {symbol} ที่ราคาหยุดขาดทุนที่ {current_price} USDT")

                    elif current_price >= target_sell_price1:
                        place_sell_order(symbol, trade_status1, rise_percentage, trade_status1, trade_status2,websocket_prices, 'trade_status1.json', buy_number=1)
                        cmd_notify(f"ขาย buy 1 {symbol} สำเร็จที่ {current_price} USDT")

            for symbol, status2 in trade_status2.items():
                if status2.get('status') == 'bought':
                    if 'buy_price' not in status2:
                        cmd_notify(f"ไม่พบ buy_price ใน trade_status สำหรับ {symbol}")
                        continue
                    current_price = websocket_prices.get(symbol)
                    if current_price is None:
                        cmd_notify(f"ไม่พบราคาจาก WebSocket สำหรับ {symbol}")
                        continue

                    target_sell_price2 = calculate_target_sell_price(status2['buy_price'], rise_percentage)
                    stop_loss_price2 = calculate_stop_loss_price(status2['buy_price'], loss_percentage)

                    cmd_notify(f"{symbol}: ราคาปัจจุบันคือ {current_price}, ราคาที่ต้องการขาย buy 2 คือ {target_sell_price2}, ราคาหยุดขาดทุนคือ {stop_loss_price2}")

                    # ตรวจสอบราคาหยุดขาดทุน
                    if current_price <= stop_loss_price2:
                        place_sell_order(symbol, trade_status2, rise_percentage, trade_status1, trade_status2,websocket_prices, 'trade_status2.json', buy_number=2)
                        cmd_notify(f"ขาย buy 2 {symbol} ที่ราคาหยุดขาดทุนที่ {current_price} USDT")
                        continue

                    elif current_price >= target_sell_price2:
                        place_sell_order(symbol, trade_status2, rise_percentage, trade_status1, trade_status2,websocket_prices, 'trade_status2.json', buy_number=2)
                        cmd_notify(f"ขาย buy 2 {symbol} สำเร็จที่ {current_price} USDT")


        except Exception as e:
            cmd_notify(f"ข้อผิดพลาดใน check_trade_status: {str(e)}")
        time.sleep(60)

# เริ่มการตรวจสอบและซื้อขายตามคู่เงินที่ระบุ
def monitor_and_trade_multiple_pairs(pairs, drop_percentage, rise_percentage, buy_usdt_amount):
    loss_percentage = 18  # กำหนดเปอร์เซ็นต์การหยุดขาดทุนที่นี่

    line_notify("ระบบเทรดเริ่มทำงาน เตรียมลุยตลาด!")

    trade_status1 = load_status('trade_status1.json')
    trade_status2 = load_status('trade_status2.json')
    target_prices1 = {}
    target_prices2 = {}
    highest_prices = {}
    last_notified_prices = {}
    websocket_prices = {}
    
    check_trade_thread = threading.Thread(target=check_trade_status, args=(trade_status1, trade_status2, rise_percentage, loss_percentage, websocket_prices))
    check_trade_thread.daemon = True
    check_trade_thread.start()

    active_sockets = set()
    

    for symbol in pairs:
        if symbol in trade_status1 and trade_status1[symbol]['status'] == 'bought':
            target_sell_price1 = trade_status1[symbol]['buy_price'] * (1 + rise_percentage / 100)
            target_prices1[symbol] = {'sell': target_sell_price1}
        else:
            target_prices1[symbol] = {}

    twm = ThreadedWebsocketManager(api_key=api_key, api_secret=api_secret)
    twm.start()

    try:
        for symbol in pairs:
            if symbol not in active_sockets:
                start_socket(symbol, twm, trade_status1, trade_status2, buy_usdt_amount, target_prices1, target_prices2, highest_prices, last_notified_prices, websocket_prices)
                active_sockets.add(symbol)  # เพิ่ม symbol ที่ใช้งานอยู่เข้า set
    except KeyboardInterrupt:
        asyncio.run(stop_socket(twm))
    except Exception as e:
        cmd_notify(f"เกิดข้อผิดพลาดในการรัน WebSocket: {str(e)}")
        asyncio.run(stop_socket(twm))


    try:
        twm.join()
    except Exception as e:
        cmd_notify(f"ข้อผิดพลาดใน twm.join(): {str(e)}")
        asyncio.run(stop_socket(twm))


# เริ่มต้นการอัปเดตยอดเงินในบัญชีทุกๆ 60 วินาที
balance_thread = threading.Thread(target=update_balance)
balance_thread.daemon = True
balance_thread.start()

# ตัวอย่างการใช้งาน
symbols = [
    '1000SATSUSDT', '1INCHUSDT', 'AAVEUSDT', 'ACAUSDT', 'ACEUSDT', 'ACHUSDT', 'ADAUSDT', 'AGLDUSDT', 'ALGOUSDT',
    'ALICEUSDT', 'ALPACAUSDT', 'ALPHAUSDT', 'ALPINEUSDT', 'ANKRUSDT', 'APEUSDT', 'API3USDT', 'APTUSDT', 'ARUSDT',
    'ARBUSDT', 'ARKMUSDT', 'ASTRUSDT', 'ATOMUSDT', 'AUCTIONUSDT', 'AUDIOUSDT', 'AVAUSDT', 'AVAXUSDT', 'AXSUSDT',
    'BADGERUSDT', 'BAKEUSDT', 'BANANAUSDT', 'BANDUSDT', 'BARUSDT', 'BATUSDT', 'BBUSDT', 'BCHUSDT', 'BEAMXUSDT',
    'BICOUSDT', 'BLURUSDT', 'BNXUSDT', 'BOMEUSDT', 'BONKUSDT', 'BSWUSDT', 'BTCUSDT', 'BURGERUSDT', 'C98USDT',
    'CAKEUSDT', 'CATIUSDT', 'CELOUSDT', 'CELRUSDT', 'CFXUSDT', 'CHESSUSDT', 'CHRUSDT', 'CHZUSDT', 'CKBUSDT',
    'COMPUSDT', 'COTIUSDT', 'CRVUSDT', 'CVCUSDT', 'DASHUSDT', 'DCRUSDT', 'DEGOUSDT', 'DGBUSDT', 'DIAUSDT',
    'DODOUSDT', 'DOGEUSDT', 'DOGSUSDT', 'DOTUSDT', 'DYDXUSDT', 'DYMUSDT', 'EDUUSDT', 'EGLDUSDT', 'EIGENUSDT',
    'ENAUSDT', 'ENJUSDT', 'ENSUSDT', 'EOSUSDT', 'ETCUSDT', 'ETHUSDT', 'ETHFIUSDT', 'FARMUSDT', 'FETUSDT', 'FIDAUSDT',
    'FILUSDT', 'FLMUSDT', 'FLOKIUSDT', 'FLOWUSDT', 'FTMUSDT', 'FXSUSDT', 'GUSDT', 'GALAUSDT', 'GASUSDT', 'GLMUSDT',
    'GMTUSDT', 'GMXUSDT', 'GNOUSDT', 'GNSUSDT', 'GRTUSDT', 'GTCUSDT', 'HBARUSDT', 'HFTUSDT', 'HIGHUSDT', 'HMSTRUSDT',
    'HOTUSDT', 'ICPUSDT', 'ICXUSDT', 'IDUSDT', 'IDEXUSDT', 'IMXUSDT', 'INJUSDT', 'IOUSDT', 'IOSTUSDT', 'IOTXUSDT',
    'JSTUSDT', 'JTOUSDT', 'JUPUSDT', 'KAVAUSDT', 'KDAUSDT', 'KNCUSDT', 'KSMUSDT', 'LDOUSDT', 'LEVERUSDT', 'LINKUSDT',
    'LISTAUSDT', 'LITUSDT', 'LOKAUSDT', 'LPTUSDT', 'LQTYUSDT', 'LRCUSDT', 'LTCUSDT', 'LUNAUSDT', 'LUNCUSDT',
    'MAGICUSDT', 'MANAUSDT', 'MANTAUSDT', 'MASKUSDT', 'MEMEUSDT', 'METISUSDT', 'MINAUSDT', 'MKRUSDT', 'MLNUSDT',
    'NEARUSDT', 'NEIROUSDT', 'NEOUSDT', 'NEXOUSDT', 'NKNUSDT', 'NMRUSDT', 'NOTUSDT', 'NULSUSDT', 'OGNUSDT', 'OMUSDT',
    'ONEUSDT', 'ONGUSDT', 'ONTUSDT', 'OPUSDT', 'ORDIUSDT', 'OXTUSDT', 'PAXGUSDT', 'PENDLEUSDT', 'PEOPLEUSDT',
    'PEPEUSDT', 'PHAUSDT', 'POLUSDT', 'POLYXUSDT', 'PORTALUSDT', 'PORTOUSDT', 'PYTHUSDT', 'QIUSDT', 'QNTUSDT',
    'QTUMUSDT', 'QUICKUSDT', 'RADUSDT', 'RAREUSDT', 'RAYUSDT', 'RDNTUSDT', 'RENDERUSDT', 'REQUSDT', 'RLCUSDT',
    'RONINUSDT', 'ROSEUSDT', 'RPLUSDT', 'RSRUSDT', 'RUNEUSDT', 'RVNUSDT', 'SANDUSDT', 'SEIUSDT', 'SHIBUSDT',
    'SKLUSDT', 'SLPUSDT', 'SNXUSDT', 'SOLUSDT', 'SSVUSDT', 'STEEMUSDT', 'STGUSDT', 'STMXUSDT', 'STORJUSDT',
    'STPTUSDT', 'STRKUSDT', 'STXUSDT', 'SUIUSDT', 'SUPERUSDT', 'SUSHIUSDT', 'SXPUSDT', 'SYSUSDT', 'TUSDT', 'TAOUSDT',
    'THETAUSDT', 'TIAUSDT', 'TKOUSDT', 'TLMUSDT', 'TNSRUSDT', 'TONUSDT', 'TRBUSDT', 'TRUUSDT', 'TRXUSDT', 'TURBOUSDT',
    'TWTUSDT', 'UMAUSDT', 'UNIUSDT', 'VANRYUSDT', 'VETUSDT', 'VIDTUSDT', 'VOXELUSDT', 'WUSDT', 'WAXPUSDT',
    'WBTCUSDT', 'WIFUSDT', 'WINUSDT', 'WLDUSDT', 'WOOUSDT', 'XAIUSDT', 'XECUSDT', 'XLMUSDT', 'XNOUSDT', 'XRPUSDT',
    'XTZUSDT', 'XVSUSDT', 'YFIUSDT', 'YGGUSDT', 'ZENUSDT', 'ZILUSDT', 'ZKUSDT', 'ZROUSDT', 'ZRXUSDT'
] #  อัปเดตล่าสุด   23/10/2024
drop_percentage = 0.8
rise_percentage = 2.79
buy_usdt_amount = 180
monitor_and_trade_multiple_pairs(symbols, drop_percentage, rise_percentage, buy_usdt_amount)
