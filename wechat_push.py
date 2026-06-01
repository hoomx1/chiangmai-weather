#!/usr/bin/env python3
"""
Server酱微信推送脚本
定时获取天气并推送到微信
"""

import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone
import sys

# ============================================================
# 配置
# ============================================================
SENDKEY = "SCT357700TDobjNXIDpTAfyAbM9DL2T4C1"
SERVERCHAN_URL = "https://sctapi.ftqq.com/{SENDKEY}.send"

# 城市配置
CITIES = {
    "Chiang+Mai": "清迈",
    "Bangkok": "曼谷",
    "Pattaya": "芭堤雅",
    "Phuket": "普吉岛",
}

# 默认城市
DEFAULT_CITY = "Chiang+Mai"

# 天气图标映射
WEATHER_ICONS = {
    113: "☀️", 116: "⛅", 119: "☁️", 122: "☁️",
    143: "🌫️", 176: "🌦️", 179: "🌨️", 182: "🌨️",
    185: "🌧️", 200: "⛈️", 227: "🌬️", 230: "🌨️",
    248: "🌫️", 260: "🌫️", 263: "🌧️", 266: "🌧️",
    281: "🌧️", 284: "🌧️", 293: "🌦️", 296: "🌦️",
    299: "🌧️", 302: "🌧️", 305: "🌧️", 308: "🌧️",
    311: "🌧️", 314: "🌧️", 317: "🌨️", 320: "🌨️",
    323: "🌨️", 326: "🌨️", 329: "❄️", 332: "❄️",
    335: "❄️", 338: "❄️", 350: "🌨️", 353: "🌦️",
    356: "🌧️", 359: "🌧️", 362: "🌨️", 365: "🌨️",
    368: "🌨️", 371: "❄️", 374: "🌨️", 377: "🌨️",
    386: "⛈️", 389: "⛈️", 392: "⛈️", 395: "❄️",
}

def get_weather_icon(code):
    """获取天气图标"""
    return WEATHER_ICONS.get(code, "🌤️")

def fetch_weather(city):
    """获取天气数据"""
    url = f"https://wttr.in/{city}?format=j1"
    req = urllib.request.Request(url, headers={
        "User-Agent": "WeatherPush/1.0",
        "Accept": "application/json"
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode('utf-8'))

def parse_timeline(day_data):
    """解析早/中/晚天气"""
    hours = day_data.get("hourly", [])
    if not hours:
        return {}
    
    # 找到最接近的时间点
    def find_hour(target):
        exact = next((h for h in hours if int(h.get("time", 0)) == target), None)
        if exact:
            return exact
        # 找最接近的
        best = min(hours, key=lambda h: abs(int(h.get("time", 0)) - target))
        return best
    
    return {
        "morning": find_hour(600),   # 6:00
        "noon": find_hour(1200),     # 12:00
        "evening": find_hour(1800),  # 18:00
    }

def format_time_period():
    """根据当前时间返回时段"""
    now = datetime.now(timezone(timedelta(hours=7)))  # UTC+7
    hour = now.hour
    if 5 <= hour < 10:
        return "🌅 早晨", "morning"
    elif 10 <= hour < 14:
        return "☀️ 中午", "noon"
    elif 14 <= hour < 20:
        return "🌆 傍晚", "evening"
    else:
        return "🌙 夜晚", "evening"

def send_to_wechat(title, content):
    """推送到微信"""
    url = SERVERCHAN_URL.format(SENDKEY=SENDKEY)
    data = urllib.parse.urlencode({
        "title": title,
        "desp": content
    }).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            if result.get("code") == 0:
                print("✅ 推送成功")
                return True
            else:
                print(f"❌ 推送失败: {result.get('message', 'Unknown error')}")
                return False
    except Exception as e:
        print(f"❌ 网络错误: {e}")
        return False

def generate_message(city_name, weather_data):
    """生成推送消息"""
    cc = weather_data["current_condition"][0]
    days = weather_data["weather"]
    today = days[0]
    timeline = parse_timeline(today)
    
    # 当前天气
    temp = cc["temp_C"]
    desc = cc["weatherDesc"][0]["value"].strip()
    feels = cc["FeelsLikeC"]
    humidity = cc["humidity"]
    wind = f"{cc['winddir16Point']} {cc['windspeedKmph']}km/h"
    uv = cc["uvIndex"]
    
    # 时段
    period_label, period_key = format_time_period()
    period_data = timeline.get(period_key, {})
    
    # 今日预报
    max_temp = today["maxtempC"]
    min_temp = today["mintempC"]
    
    # 明天预报
    tomorrow = days[1] if len(days) > 1 else today
    tomorrow_max = tomorrow["maxtempC"]
    tomorrow_min = tomorrow["mintempC"]
    tomorrow_desc = tomorrow["hourly"][4]["weatherDesc"][0]["value"].strip() if len(tomorrow["hourly"]) > 4 else "未知"
    
    # 构建消息
    now = datetime.now(timezone(timedelta(hours=7))).strftime("%m/%d %H:%M")
    
    message = f"""## {city_name}天气 · {period_label}

**当前天气**
🌡️ {temp}°C ({desc}) | 体感 {feels}°C
💧 湿度 {humidity}% | 💨 {wind}
☀️ 紫外线 {uv}级

**今日预报**
🌡️ {min_temp}°C ~ {max_temp}°C
📅 明天: {tomorrow_min}°C ~ {tomorrow_max}°C ({tomorrow_desc})

"""
    
    # 添加时段详情
    if period_data:
        period_temp = period_data.get("tempC", "N/A")
        period_desc = period_data.get("weatherDesc", [{"value": "未知"}])[0]["value"].strip()
        message += f"**{period_label}预报**\n"
        message += f"🌡️ {period_temp}°C ({period_desc})\n"
    
    message += f"""
---
📊 数据来源: wttr.in
🕐 更新时间: {now}
"""
    
    return message

def main():
    try:
        print(f"开始获取天气数据...")
        
        # 获取天气
        weather_data = fetch_weather(DEFAULT_CITY)
        city_name = CITIES.get(DEFAULT_CITY, "清迈")
        
        # 生成消息
        message = generate_message(city_name, weather_data)
        
        # 推送标题
        period_label, _ = format_time_period()
        title = f"{city_name}天气 {period_label}"
        
        # 发送
        print(f"标题: {title}")
        print(f"消息长度: {len(message)} 字符")
        
        success = send_to_wechat(title, message)
        if success:
            # 保存日志
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "city": DEFAULT_CITY,
                "title": title,
                "success": True
            }
            with open("push_log.json", "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            return 0
        else:
            return 1
            
    except Exception as e:
        print(f"❌ 程序错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
