import requests
import pandas as pd
from datetime import datetime, timedelta

# กำหนดคู่สกุลเงินดิจิทัล เช่น 'BTCUSDT' สำหรับ Bitcoin กับ USD
symbol = 'BTCUSDT'
interval = '1d'  # ใช้ความถี่ข้อมูลรายวัน

# กำหนดวันที่เริ่มต้นและสิ้นสุด (ย้อนหลัง 1 เดือน)
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

# แปลงวันที่เริ่มต้นเป็น timestamp ในรูปแบบ milliseconds
start_timestamp = int(start_date.timestamp() * 1000)
end_timestamp = int(end_date.timestamp() * 1000)

# ดึงข้อมูลจาก Binance API
url = 'https://api.binance.com/api/v3/klines'
params = {
    'symbol': symbol,
    'interval': interval,
    'startTime': start_timestamp,
    'endTime': end_timestamp
}
response = requests.get(url, params=params)
data = response.json()

# แปลงข้อมูลเป็น DataFrame
df = pd.DataFrame(data, columns=['Open time', 'Open', 'High', 'Low', 'Close', 'Volume', 
                                 'Close time', 'Quote asset volume', 'Number of trades', 
                                 'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'])
df['Date'] = pd.to_datetime(df['Open time'], unit='ms')
df = df[['Date', 'High', 'Low']].astype({'High': 'float', 'Low': 'float'})

# บันทึกข้อมูลเป็นไฟล์ Excel
file_path = 'Crypto_High_Low_Last_Month_Binance.xlsx'
df.to_excel(file_path, index=False, sheet_name='Crypto_High_Low')

print(f"ข้อมูลถูกบันทึกลงในไฟล์ {file_path} เรียบร้อยแล้ว")
