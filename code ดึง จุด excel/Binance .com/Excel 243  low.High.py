import requests
import pandas as pd
from datetime import datetime, timedelta

# สร้างรายชื่อคู่สกุลเงินที่ต้องการดึงข้อมูล
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
] #  อัปเดตล่าสุด   23/10/2024  # เพิ่มคู่เงินที่ต้องการ เช่น BTCUSDT, ETHUSDT, BNBUSDT
interval = '1d'  # กำหนดความถี่ข้อมูลรายวัน

# กำหนดวันที่เริ่มต้นและสิ้นสุด (ย้อนหลัง 1 เดือน)
end_date = datetime.now()
start_date = end_date - timedelta(days=30)
start_timestamp = int(start_date.timestamp() * 1000)
end_timestamp = int(end_date.timestamp() * 1000)

# สร้าง DataFrame ว่างเพื่อเก็บข้อมูลทั้งหมด
all_data = pd.DataFrame()

# วนลูปดึงข้อมูลสำหรับแต่ละคู่เงิน
for idx, symbol in enumerate(symbols, start=1):
    print(f"กำลังดึงข้อมูล คู่ที่ {idx}/{len(symbols)}: {symbol}")

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
    df['Symbol'] = symbol  # เพิ่มคอลัมน์คู่สกุลเงิน
    df = df[['Date', 'Symbol', 'High', 'Low']].astype({'High': 'float', 'Low': 'float'})
    
    # นำข้อมูลของคู่สกุลเงินแต่ละคู่มารวมกันใน DataFrame เดียว
    all_data = pd.concat([all_data, df], ignore_index=True)

# เพิ่มคอลัมน์ใหม่ที่คำนวณค่า Low*100/High-100 และ High*100/Low-100
all_data['L*100/H-100'] = (all_data['Low'] * 100 / all_data['High']) - 100
all_data['H*100/L-100'] = (all_data['High'] * 100 / all_data['Low']) - 100

# บันทึกข้อมูลทั้งหมดลงในไฟล์ Excel พร้อมจัดรูปแบบหัวตารางตามที่คุณต้องการ
file_path = 'Crypto_High_Low_Multiple_Symbols_Last_Month_Updated.xlsx'
with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
    all_data.to_excel(writer, index=False, sheet_name='Crypto_High_Low')
    worksheet = writer.sheets['Crypto_High_Low']

    # ปรับสไตล์หัวตารางให้ตรงกับภาพตัวอย่าง
    header_format = {
        'DATE': 'DATE',
        'Symbol': 'PAIRS',
        'Low': 'LOW',
        'High': 'HIGH',
        'L*100/H-100': 'L*100/H-100=?',
        'H*100/L-100': 'H*100/L-100=?'
    }
    for idx, header in enumerate(header_format.keys(), start=1):
        cell = worksheet.cell(row=1, column=idx)
        cell.value = header_format[header]
        cell.font = cell.font.copy(bold=True)
        cell.fill = cell.fill.copy(fgColor="FFFF00", fill_type="solid")  # สีพื้นหลังเหลือง

print(f"\nข้อมูลถูกบันทึกลงในไฟล์ {file_path} เรียบร้อยแล้ว")
