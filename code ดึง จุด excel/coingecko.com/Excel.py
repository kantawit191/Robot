import requests
import pandas as pd
from datetime import datetime, timedelta

# กำหนดสกุลเงินดิจิทัลที่ต้องการ เช่น 'bitcoin'
crypto_id = 'bitcoin'

# กำหนดวันที่เริ่มต้นและสิ้นสุด (ย้อนหลัง 1 เดือน)
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

# แปลงวันที่เป็น timestamp
start_timestamp = int(start_date.timestamp())
end_timestamp = int(end_date.timestamp())

# ดึงข้อมูลราคาย้อนหลังจาก CoinGecko API
url = f'https://api.coingecko.com/api/v3/coins/{crypto_id}/market_chart/range'
params = {
    'vs_currency': 'usd',
    'from': start_timestamp,
    'to': end_timestamp
}
response = requests.get(url, params=params)
data = response.json()

# แปลงข้อมูลเป็น DataFrame
prices = data['prices']
df = pd.DataFrame(prices, columns=['timestamp', 'price'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df.set_index('timestamp', inplace=True)

# คำนวณ High และ Low ในแต่ละวัน
daily_data = df.resample('D').agg({'price': ['max', 'min']})
daily_data.columns = ['High', 'Low']

# บันทึกข้อมูลเป็นไฟล์ Excel
file_path = 'Crypto_High_Low_Last_Month.xlsx'
daily_data.to_excel(file_path, sheet_name='Crypto_High_Low')

print(f"ข้อมูลถูกบันทึกลงในไฟล์ {file_path} เรียบร้อยแล้ว")
