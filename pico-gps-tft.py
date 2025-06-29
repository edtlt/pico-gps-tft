from machine import Pin, SPI,UART
import time
import utime
import st7789 as st7789  # 导入驱动库

# === 硬件引脚配置 ===
# 根据您的实际接线修改这些引脚号
spi_sck = 2    # GP2 (SCK)
spi_mosi = 3   # GP3 (MOSI)
spi_cs = 5     # GP5 (CS)
dc_pin = 6     # GP4 (DC)
reset_pin = 7  # GP6 (RESET)
bl_pin = 8     # GP7 (背光控制，可选)

# === 颜色定义 (RGB565格式) ===
# 注意：驱动文件中的颜色定义有误，这里使用正确的值
BLACK   = 0x0000
WHITE   = 0xFFFF
RED     = 0xF800
GREEN   = 0x07E0
BLUE    = 0x001F
CYAN    = 0x07FF
MAGENTA = 0xF81F
YELLOW  = 0xFFE0

# 初始化LED用于状态指示
led = Pin("LED", Pin.OUT)
led.off()

# 初始化UART用于GPS (波特率9600)
uart = UART(0, baudrate=9600, tx=None, rx=Pin(17))

# 全局变量存储GPS数据
gps_data = {
    'date': "等待定位",
    'time': "等待定位",
    'latitude': 0.0,
    'longitude': 0.0,
    'satellites': 0
}

# === 初始化SPI和GPIO ===
spi = SPI(0, baudrate=20_000_000, sck=Pin(spi_sck), mosi=Pin(spi_mosi))
dc = Pin(dc_pin, Pin.OUT)
reset = Pin(reset_pin, Pin.OUT)
cs = Pin(spi_cs, Pin.OUT)
bl = Pin(bl_pin, Pin.OUT)

# === 创建显示屏对象 ===
# 注意：240x240分辨率的屏幕
tft = st7789.ST7789(
    spi=spi,
    width=240,
    height=320,
    dc=dc,
    cs=cs,
    reset=reset,
    rotation=0  # 旋转角度 (0, 90, 180, 270)
)

# === 初始化显示屏 ===
tft.init()
bl.on()  # 开启背光



# 全局变量存储日期信息
last_valid_date = "未知"

def parse_gps_data(data):
    """解析NMEA数据并更新GPS数据"""
    global last_valid_date, gps_data
    
    try:
        # 检查GNRMC/GPRMC语句（包含完整日期信息）
        if data.startswith('$GPRMC') or data.startswith('$GNRMC'):
            parts = data.split(',')
            if len(parts) < 10:
                return
                
            # 检查定位状态
            if parts[2] != 'A':
                return
                
            # 解析日期 (ddmmyy)
            date_str = parts[9]
            if len(date_str) == 6:
                # 更新全局日期
                last_valid_date = f"{date_str[0:2]}-{date_str[2:4]}-20{date_str[4:6]}"
            else:
                return
            
            # 解析时间 (hhmmss.ss)
            time_str = parts[1]
            if len(time_str) < 6:
                return
            utc_time = f"{time_str[0:2]}:{time_str[2:4]}:{time_str[4:6]} UTC"
            
            # 解析纬度 (ddmm.mmmm)
            if parts[3] and parts[4]:
                try:
                    lat = float(parts[3])
                    lat_deg = int(lat / 100)
                    lat_min = lat - (lat_deg * 100)
                    latitude = lat_deg + (lat_min / 60)
                    if parts[4] == 'S':
                        latitude = -latitude
                except:
                    return
            else:
                return
            
            # 解析经度 (dddmm.mmmm)
            if parts[5] and parts[6]:
                try:
                    lon = float(parts[5])
                    lon_deg = int(lon / 100)
                    lon_min = lon - (lon_deg * 100)
                    longitude = lon_deg + (lon_min / 60)
                    if parts[6] == 'W':
                        longitude = -longitude
                except:
                    return
            else:
                return
            
            # 更新GPS数据
            gps_data['date'] = last_valid_date
            gps_data['time'] = utc_time
            gps_data['latitude'] = latitude
            gps_data['longitude'] = longitude
        
        # 检查GNGLL/GPGLL语句（包含位置信息）
        elif data.startswith('$GNGLL') or data.startswith('$GPGLL'):
            parts = data.split(',')
            if len(parts) < 7:
                return
                
            # 检查定位状态
            if parts[6] != 'A':
                return
            
            # 解析时间 (hhmmss.ss)
            time_str = parts[5]
            if len(time_str) < 6:
                return
            utc_time = f"{time_str[0:2]}:{time_str[2:4]}:{time_str[4:6]} UTC"
            
            # 解析纬度 (ddmm.mmmm)
            if parts[1] and parts[2]:
                try:
                    lat = float(parts[1])
                    lat_deg = int(lat / 100)
                    lat_min = lat - (lat_deg * 100)
                    latitude = lat_deg + (lat_min / 60)
                    if parts[2] == 'S':
                        latitude = -latitude
                except:
                    return
            else:
                return
            
            # 解析经度 (dddmm.mmmm)
            if parts[3] and parts[4]:
                try:
                    lon = float(parts[3])
                    lon_deg = int(lon / 100)
                    lon_min = lon - (lon_deg * 100)
                    longitude = lon_deg + (lon_min / 60)
                    if parts[4] == 'W':
                        longitude = -longitude
                except:
                    return
            else:
                return
            
            # 更新GPS数据（使用最后有效日期）
            gps_data['time'] = utc_time
            gps_data['latitude'] = latitude
            gps_data['longitude'] = longitude
        
        # 检查GPGGA/GNGGA语句（包含卫星数量信息）
        elif data.startswith('$GPGGA') or data.startswith('$GNGGA'):
            parts = data.split(',')
            if len(parts) > 7:
                try:
                    satellites = int(parts[7])
                    gps_data['satellites'] = satellites
                except:
                    pass
            
    except Exception as e:
        pass

# def tft.text(text, x, y, color, bg_color=BLACK):
#     """使用嵌入式字体绘制文本"""
#     # 绘制背景
#     tft.fill_rect(x, y, len(text) * font8x16.width, font8x16.height, bg_color)
#     
#     # 绘制每个字符
#     for i, char in enumerate(text):
#         char_data = font8x16.get_char(char)
#         if char_data:
#             # 创建字符缓冲区
#             char_buf = bytearray(char_data)
#             char_fb = framebuf.FrameBuffer(char_buf, font8x16.width, font8x16.height, framebuf.MONO_HLSB)
#             
#             # 绘制字符
#             for py in range(font8x16.height):
#                 for px in range(font8x16.width):
#                     if char_fb.pixel(px, py):
#                         tft.pixel(x + i * font8x16.width + px, y + py, color)

def display_gps_info():
    """在显示屏上显示GPS信息"""
    # 清屏
    tft.fill(BLACK)
    
    # 显示标题
    tft.text("GPS info", 60, 10, YELLOW)
    
    # 显示日期和时间
    tft.text(f"date: {gps_data['date']}", 10, 40, WHITE)
    tft.text(f"time: {gps_data['time']}", 10, 70, WHITE)
    
    # 显示经纬度
    tft.text(f"latitude: {gps_data['latitude']:.6f}°", 10, 100, CYAN)
    tft.text(f"longtitude: {gps_data['longitude']:.6f}°", 10, 130, CYAN)
    
    # 显示卫星数量
    tft.text(f"satellites: {gps_data['satellites']}颗", 10, 160, GREEN)
    
    # 显示状态信息
    status = "locatied" if gps_data['satellites'] >= 3 else "定位中"
    status_color = GREEN if status == "已定位" else RED
    tft.text(f"status: {status}", 10, 190, status_color)
    
    # 更新显示
    tft.show()


def display_waiting_screen():
    """显示等待定位的界面"""
    tft.fill(BLACK)
    tft.text("GPS system", 60, 20, WHITE)
    tft.text("waitting singnal...", 40, 60, YELLOW)
    tft.text("satellites:", 70, 100, CYAN)
    tft.text(f"{gps_data['satellites']}", 100, 130, GREEN)
    tft.text("Put device", 70, 160, YELLOW)
    tft.text("to open field", 80, 190, YELLOW)
    tft.show()

# 显示初始化界面
#tft.fill(BLACK)
tft.text("GPS system", 60, 20, WHITE)
tft.text("Initialing...", 70, 50, WHITE)
tft.text("Put device", 70, 80, YELLOW)
tft.text("to open field", 80, 100, YELLOW)
tft.show()

# 主循环
last_display_update = utime.ticks_ms()
last_fix_time = utime.ticks_ms()

# print("GPS定位系统启动...")
# print("等待GPS数据...")

while True:
    # 处理GPS数据
    if uart.any():
        data = uart.readline()
        try:
            decoded = data.decode('utf-8').strip()
            parse_gps_data(decoded)
            last_fix_time = utime.ticks_ms()
        except:
            pass
    
    # 更新显示屏
    current_time = utime.ticks_ms()
    if utime.ticks_diff(current_time, last_display_update) > 1000:  # 每秒更新一次
        if gps_data['satellites'] >= 3:  # 至少有3颗卫星时显示定位信息
            display_gps_info()
            # 定位成功时快速闪烁LED
            led.on()
            utime.sleep_ms(50)
            led.off()
        else:
            display_waiting_screen()
        
        last_display_update = current_time
    
    # 检查定位状态
    if utime.ticks_diff(utime.ticks_ms(), last_fix_time) > 10000:  # 10秒无更新
        gps_data['satellites'] = max(0, gps_data['satellites'] - 1)  # 减少卫星数
    
    # 系统运行时LED慢速闪烁
    if utime.ticks_ms() % 2000 < 100:
        led.on()
    else:
        led.off()
    
    # 降低CPU使用率
    utime.sleep_ms(100)