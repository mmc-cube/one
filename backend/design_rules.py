"""Reusable component-selection and function-design rules derived from prd-gen.

This module deliberately contains no HTTP or UI code so the rules can later be
reused by an AI prompt pipeline, PRD exporter, or MCU project generator.
"""

from __future__ import annotations

import re
from typing import Any


NETWORK_TERMS = ("物联网", "联网", "WiFi", "wifi", "MQTT", "mqtt", "APP", "app", "远程", "云端")
ESP32_TERMS = ("ESP32", "esp32")
ALARM_TERMS = ("蜂鸣器", "报警", "告警")


def is_pid_dc_motor_topic(topic: str) -> bool:
    lowered = topic.lower()
    return "pid" in lowered and any(word in topic for word in ("直流电机", "电机调速", "电机控制"))


def domain_profile(topic: str) -> dict[str, list[str]] | None:
    """Return the allowed component pool for common MCU project categories."""
    if is_pid_dc_motor_topic(topic):
        return {
            "sensors": ["增量式编码器", "ACS712 电流传感器", "光电测速模块", "按键模块"],
            "displays": ["0.96 英寸 SSD1306 OLED 显示屏", "LCD1602 液晶显示屏"],
            "actuators": ["直流电机 + TB6612FNG 电机驱动模块", "LED 运行指示灯（GPIO 直接驱动）"],
        }
    if any(word in topic for word in ("密码锁", "门禁", "智能锁", "电子锁", "门锁")):
        return {
            "sensors": ["AS608 指纹识别模块", "4×4矩阵键盘", "门磁传感器", "RC522 射频识别模块"],
            "displays": ["0.96 英寸 SSD1306 OLED 显示屏", "LCD1602 液晶显示屏"],
            "actuators": ["电磁锁 + 继电器驱动模块", "有源蜂鸣器", "LED 状态指示灯（GPIO 直接驱动）"],
        }
    if any(word in topic for word in ("水产", "养殖", "水质", "鱼缸")):
        return {
            "sensors": ["DS18B20 水温传感器", "pH 传感器", "溶解氧传感器", "浊度传感器", "TDS 传感器"],
            "displays": ["0.96 英寸 SSD1306 OLED 显示屏", "LCD1602 液晶显示屏"],
            "actuators": ["增氧泵 + 继电器驱动模块", "换水泵 + 继电器驱动模块", "有源蜂鸣器"],
        }
    if any(word in topic for word in ("温室", "大棚", "灌溉", "农业", "种植")):
        return {
            "sensors": ["DHT22 温湿度传感器", "土壤湿度传感器", "BH1750 光照传感器", "按键模块", "CO2 传感器"],
            "displays": ["0.96 英寸 SSD1306 OLED 显示屏", "LCD1602 液晶显示屏"],
            "actuators": ["水泵 + 继电器驱动模块", "风扇 + 继电器驱动模块", "补光灯 + 继电器驱动模块"],
        }
    if "窗帘" in topic:
        return {
            "sensors": ["BH1750 光照传感器", "雨滴传感器", "限位开关"],
            "displays": ["0.96 英寸 SSD1306 OLED 显示屏", "LCD1602 液晶显示屏"],
            "actuators": ["28BYJ-48 步进电机 + ULN2003 驱动板", "有源蜂鸣器"],
        }
    if any(word in topic for word in ("火灾", "消防", "烟雾")):
        return {
            "sensors": ["MQ-2 烟雾传感器", "DS18B20 温度传感器", "火焰传感器", "按键模块"],
            "displays": ["0.96 英寸 SSD1306 OLED 显示屏", "LCD1602 液晶显示屏"],
            "actuators": ["有源蜂鸣器", "红色 LED 指示灯（GPIO 直接驱动）", "消防水泵 + 继电器驱动模块"],
        }
    if any(term.lower() in topic.lower() for term in NETWORK_TERMS):
        return {
            "sensors": ["DHT22 温湿度传感器", "BH1750 光照传感器", "MQ-135 空气质量传感器", "按键模块"],
            "displays": ["0.96 英寸 SSD1306 OLED 显示屏", "LCD1602 液晶显示屏"],
            "actuators": ["LED 状态指示灯（GPIO 直接驱动）", "有源蜂鸣器"],
        }
    return None


def unique_items(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        key = re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", item.lower())
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result


def component_matches(candidate: str, allowed: str) -> bool:
    candidate_key = re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", candidate.lower())
    allowed_key = re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", allowed.lower())
    return bool(candidate_key and allowed_key and (candidate_key in allowed_key or allowed_key in candidate_key))


def filter_domain_items(topic: str, kind: str, candidates: list[str], count: int) -> list[str]:
    """Match AI candidates in domain-priority order, then fill missing slots from the pool."""
    profile = domain_profile(topic)
    if not profile:
        return unique_items(candidates)[:count]
    pool_key = {"sensor": "sensors", "display": "displays", "actuator": "actuators"}[kind]
    allowed = profile[pool_key]
    result: list[str] = []
    for fallback in allowed:
        matched = next(
            (candidate for candidate in candidates if component_matches(candidate, fallback)),
            fallback,
        )
        if not any(component_matches(existing, matched) for existing in result):
            result.append(matched)
    return result[:count]


def domain_first_items(topic: str, kind: str, candidates: list[str]) -> list[str]:
    """Compatibility wrapper for callers that need the full domain-sized result."""
    return filter_domain_items(topic, kind, candidates, len(candidates))


def choose_controller(topic: str) -> dict[str, str]:
    if any(term in topic for term in ESP32_TERMS):
        return {
            "name": "ESP32-S3-N8R2",
            "reason": "题目明确指定 ESP32，按指定平台选型；需要更多图形或缓存资源时再升级 N8R8。",
        }
    return {
        "name": "STM32F103C8T6",
        "reason": "题目未指定主控，按 prd-gen 规则优先选择资料成熟、适合课设和毕设的 STM32F103C8T6。",
    }


def topic_load(topic: str) -> str:
    if is_pid_dc_motor_topic(topic):
        return "直流电机"
    if any(word in topic for word in ("密码锁", "门禁", "智能锁", "电子锁", "门锁")):
        return "电磁锁"
    if any(word in topic for word in ("水产", "养殖", "水质", "鱼缸")):
        return "增氧泵"
    if any(word in topic for word in ("火灾", "消防", "烟雾")):
        return "消防水泵"
    if any(word in topic for word in ("大棚", "灌溉", "土壤", "鱼缸", "水质", "补水")):
        return "水泵"
    if any(word in topic for word in ("温度", "温湿度", "环境", "通风", "降温")):
        return "风扇"
    if any(word in topic for word in ("窗帘", "门", "开合")):
        return "28BYJ-48 步进电机 + ULN2003 驱动板"
    return "外部负载"


def clean_item(item: str) -> str:
    return re.sub(r"\s+", " ", item).strip()


def normalize_actuator(topic: str, item: str) -> tuple[str, str | None]:
    value = clean_item(item)
    lowered = value.lower()
    if "步进电机" in value:
        if "uln2003" not in lowered or "继电器" in value:
            return "28BYJ-48 步进电机 + ULN2003 驱动板", "步进电机使用 ULN2003 驱动板，不额外串接继电器。"
        return value, None
    if "led" in lowered and "继电器" in value:
        return value.replace("继电器", "GPIO"), "LED 改为 GPIO 直接驱动，不使用继电器。"
    if "继电器" in value and not any(load in value for load in ("水泵", "风扇", "加热", "电磁阀", "电磁锁", "增氧泵", "补光灯", "负载")):
        load = topic_load(topic)
        return f"{load} + 继电器驱动模块", f"将只有驱动器的“{value}”补全为具体执行器与驱动器组合。"
    if "直流电机" in value and "驱动" not in value:
        return f"{value} + 直流电机驱动模块", "执行器与驱动器分离列明。"
    return value, None


def normalize_display(topic: str, item: str) -> str:
    value = clean_item(item)
    if any(word in topic for word in ("彩屏", "触摸", "TFT")):
        return value
    if any(marker in value.upper() for marker in ("OLED", "SSD1306")):
        return "0.96 英寸 SSD1306 OLED 显示屏"
    return value


def apply_component_rules(
    topic: str,
    sensors: list[str],
    displays: list[str],
    actuators: list[str],
) -> dict[str, Any]:
    selection_notes: list[str] = []
    profile = domain_profile(topic)
    if profile:
        sensors = filter_domain_items(topic, "sensor", sensors, len(sensors))
        displays = filter_domain_items(topic, "display", displays, len(displays))
        actuators = filter_domain_items(topic, "actuator", actuators, len(actuators))
        selection_notes.append("已命中题目领域器件白名单：保留相关 AI 候选，过滤无关器件，并从标准器件池补足数量。")
    normalized_actuators: list[str] = []
    for item in actuators:
        normalized, note = normalize_actuator(topic, item)
        normalized_actuators.append(normalized)
        if note and note not in selection_notes:
            selection_notes.append(note)

    normalized_displays = [normalize_display(topic, item) for item in displays]
    if normalized_displays and not any(word in topic for word in ("彩屏", "触摸", "TFT")):
        normalized_displays[0] = "0.96 英寸 SSD1306 OLED 显示屏"
        selection_notes.append("显示器默认优先使用 SSD1306 OLED，便于实现实时页与阈值页。")

    selection_notes.extend(
        [
            "模拟传感器存在 AO 输出时优先使用 AO，保留连续量用于阈值判断。",
            "UART 模块必须使用硬件串口，不使用软件串口。",
            "LED 由 GPIO 直接驱动；继电器只用于水泵、风扇、加热等较大负载。",
        ]
    )
    return {
        "sensors": [clean_item(item) for item in sensors],
        "displays": normalized_displays,
        "actuators": normalized_actuators,
        "selection_notes": selection_notes,
    }


def build_function_lines(topic: str, sensors: list[str], displays: list[str], actuators: list[str]) -> list[str]:
    if is_pid_dc_motor_topic(topic):
        return [
            "编码器定时采集电机脉冲，换算当前转速并作为 PID 闭环反馈值。",
            "按设定周期计算速度误差，执行比例、积分、微分运算并输出 PWM 占空比。",
            "TB6612FNG 电机驱动模块根据 PWM 和方向信号控制直流电机正反转及调速。",
            "支持按键设置目标转速、Kp、Ki、Kd 与正反转方向，参数修改后立即参与下一次控制计算。",
            "电流异常或编码器无反馈时停止 PWM 输出并提示故障，避免电机堵转持续驱动。",
            "OLED 实时显示目标转速、实际转速、PWM 占空比、PID 参数和运行状态。",
        ]
    if any(word in topic for word in ("密码锁", "门禁", "智能锁", "电子锁", "门锁")):
        return [
            "指纹识别模块采集并比对用户指纹，验证通过后发送开锁指令。",
            "矩阵键盘输入密码，支持确认、清除和修改密码等操作。",
            "门磁传感器检测门体开合状态，并在 OLED 上显示“开门 / 关门”状态。",
            "身份验证成功后驱动电磁锁开锁，到时自动重新上锁。",
            "连续输错密码或非法开门时触发蜂鸣器报警，并记录失败次数。",
            "OLED 显示验证结果、门锁状态、剩余尝试次数和操作提示。",
        ]
    if any(word in topic for word in ("温室", "大棚", "灌溉", "温湿度", "种植")):
        return [
            "定时采集空气温湿度、土壤湿度和光照强度，并在 OLED 实时显示。",
            "土壤湿度低于设定下限时启动水泵灌溉，恢复到目标范围后自动停止。",
            "温度或湿度超过设定上限时启动风扇通风，数据恢复正常后关闭。",
            "支持按键修改温湿度、土壤湿度等控制阈值，并立即参与自动控制。",
            "OLED 显示当前传感器数据、水泵与风扇状态以及自动/手动工作模式。",
        ]
    if any(word in topic for word in ("水产", "养殖", "水质", "鱼缸")):
        return [
            "定时采集水温、pH、溶解氧等水质数据，并在 OLED 显示当前值。",
            "溶解氧低于设定值时启动增氧泵，恢复正常后自动停止。",
            "水质指标持续异常时启动换水泵，并给出声光告警提示。",
            "支持按键设置溶解氧、pH 等报警与控制阈值。",
            "OLED 显示水质状态、增氧泵/换水泵状态和异常告警信息。",
        ]
    if "窗帘" in topic:
        return [
            "实时读取光照强度与雨滴状态，作为窗帘自动开合依据。",
            "光照低于设定值时关闭窗帘，光照恢复后按设定策略打开。",
            "检测到雨滴时优先关闭窗帘，避免雨水进入室内。",
            "步进电机通过 ULN2003 驱动窗帘开合，并结合限位信号停止。",
            "OLED 显示光照、天气状态、窗帘位置和自动/手动模式。",
        ]
    if any(word in topic for word in ("火灾", "消防", "烟雾")):
        return [
            "持续采集烟雾浓度、环境温度和火焰检测状态。",
            "任一火灾指标超过阈值时立即触发蜂鸣器和红色 LED 声光报警。",
            "OLED 显示烟雾值、温度、火焰状态和当前报警等级。",
            "按键可执行消警操作；报警条件未解除时保持告警状态。",
            "传感器数据恢复正常后自动解除报警并记录系统恢复状态。",
        ]
    if any(term.lower() in topic.lower() for term in NETWORK_TERMS):
        return [
            f"读取 {'、'.join(sensors)}，形成系统实时输入数据。",
            f"使用 {'、'.join(displays)} 显示数据和设备运行状态。",
            "通过硬件串口将传感器数据、设备状态和阈值上报至 MQTT 平台。",
            "接收上位机下发的阈值或控制指令，并反馈执行结果。",
            "网络异常时保持本地采集与自动控制，恢复连接后继续上报。",
        ]
    sensor_names = "、".join(sensors)
    display_names = "、".join(displays)
    actuator_names = "、".join(actuators)
    result = [f"读取 {sensor_names}，形成系统实时输入数据。"]
    result.append(f"使用 {display_names} 展示传感器读数、设备状态与工作模式。")
    result.append("KEY1 切换 OLED 页面；KEY2 切换当前阈值项；KEY3 阈值加；KEY4 阈值减/长按消警。")
    if actuators:
        result.append(f"依据传感器阈值控制 {actuator_names}，并同步更新显示状态。")
        result.append("需要手动控制时，各执行器独立维护 AUTO/MANUAL 模式，模式切换不改变当前开关状态。")
    return result


# OLED 传感器能力映射：器件名关键词 → (行标签, 默认值, 阈值标签)
SENSOR_OLED_MAP: list[tuple[str, str, str, str]] = [
    # (匹配词, 显示名, 默认值, 阈值名)
    ("温湿度", "Temp", "25.6C", "T.Hi"),
    ("DHT", "Temp", "25.6C", "T.Hi"),
    ("SHT", "Temp", "25.6C", "T.Hi"),
    ("BME", "Temp", "25.6C", "T.Hi"),
    ("DS18B20", "Temp", "25.6C", "T.Hi"),
    ("温度", "Temp", "25.6C", "T.Hi"),
    ("湿度", "Humi", "60%", "H.Lo"),
    ("光照", "Light", "1200lx", "L.Lo"),
    ("BH1750", "Light", "1200lx", "L.Lo"),
    ("光敏", "Light", "1200lx", "L.Lo"),
    ("土壤湿度", "Soil", "45%", "S.Lo"),
    ("土壤", "Soil", "45%", "S.Lo"),
    ("烟雾", "Smoke", "120ppm", "Sm.Hi"),
    ("MQ-2", "Smoke", "120ppm", "Sm.Hi"),
    ("MQ2", "Smoke", "120ppm", "Sm.Hi"),
    ("空气质量", "Air", "GOOD", "A.Lo"),
    ("MQ-135", "Air", "GOOD", "A.Lo"),
    ("MQ135", "Air", "GOOD", "A.Lo"),
    ("ENS160", "Air", "GOOD", "A.Lo"),
    ("CO2", "CO2", "420ppm", "C.Hi"),
    ("MH-Z19", "CO2", "420ppm", "C.Hi"),
    ("火焰", "Flame", "NO", "F.ON"),
    ("pH", "pH", "7.20", "pH.Lo"),
    ("溶解氧", "DO", "6.5mg/L", "DO.Lo"),
    ("浊度", "Turb", "20NTU", "Tb.Hi"),
    ("TDS", "TDS", "180ppm", "TD.Hi"),
    ("心率", "HR", "72bpm", "HR.Hi"),
    ("MAX30102", "HR", "72bpm", "HR.Hi"),
    ("血氧", "SpO2", "98%", "Sp.Lo"),
    ("超声波", "Dist", "120cm", "Ds.Lo"),
    ("HC-SR04", "Dist", "120cm", "Ds.Lo"),
    ("测距", "Dist", "120cm", "Ds.Lo"),
    ("编码器", "Speed", "1500rpm", "Sp.Lo"),
    ("测速", "Speed", "1500rpm", "Sp.Lo"),
    ("ACS712", "Curr", "0.6A", "Cu.Hi"),
    ("INA226", "Curr", "0.6A", "Cu.Hi"),
    ("电流", "Curr", "0.6A", "Cu.Hi"),
    ("电压", "Volt", "5.0V", "Vo.Hi"),
    ("GPS", "GPS", "FIX:5", ""),
    ("定位", "GPS", "FIX:5", ""),
    ("指纹", "Finger", "READY", ""),
    ("AS608", "Finger", "READY", ""),
    ("RFID", "RFID", "IDLE", ""),
    ("RC522", "RFID", "IDLE", ""),
    ("门磁", "Door", "CLOSED", ""),
    ("雨滴", "Rain", "NO", "Rn.ON"),
    ("限位", "Limit", "OK", ""),
    ("气压", "Press", "1013hPa", "Pr.Hi"),
    ("BMP280", "Press", "1013hPa", "Pr.Hi"),
    ("姿态", "IMU", "OK", ""),
    ("MPU6050", "IMU", "OK", ""),
    ("粉尘", "PM2.5", "35ug", "PM.Hi"),
    ("PM2.5", "PM2.5", "35ug", "PM.Hi"),
    ("PMS5003", "PM2.5", "35ug", "PM.Hi"),
]

# OLED 执行器状态映射：器件名关键词 → (行标签, 默认状态)
ACTUATOR_OLED_MAP: list[tuple[str, str, str]] = [
    ("风扇", "FAN", "OFF"),
    ("水泵", "PUMP", "OFF"),
    ("蜂鸣器", "BUZZ", "OFF"),
    ("LED", "LED", "OFF"),
    ("继电器", "RELAY", "OFF"),
    ("舵机", "SERVO", "STOP"),
    ("步进电机", "STEP", "STOP"),
    ("直流电机", "MOTOR", "STOP"),
    ("电机", "MOTOR", "STOP"),
    ("电磁锁", "LOCK", "LOCKED"),
    ("加热", "HEAT", "OFF"),
    ("制冷", "COOL", "OFF"),
    ("增氧泵", "AER", "OFF"),
    ("雾化", "MIST", "OFF"),
    ("补光灯", "LAMP", "OFF"),
    ("遮阳帘", "SHADE", "OPEN"),
    ("TB6612", "MOTOR", "STOP"),
    ("L298N", "MOTOR", "STOP"),
    ("L9110", "MOTOR", "STOP"),
    ("DRV8871", "MOTOR", "STOP"),
    ("BTS7960", "MOTOR", "STOP"),
    ("MOSFET", "MOS", "OFF"),
]


def _match_component(items: list[str], terms: tuple[str, ...]) -> bool:
    """Check if any item contains any of the given terms."""
    lowered_items = " ".join(items).lower()
    return any(term.lower() in lowered_items for term in terms)


def _detect_oled_sensors(sensors: list[str]) -> list[dict[str, str]]:
    """Scan sensor names and return their OLED line definitions."""
    found: list[dict[str, str]] = []
    seen_labels: set[str] = set()
    sensor_text = " ".join(sensors).lower()
    for keyword, label, default, threshold in SENSOR_OLED_MAP:
        if keyword.lower() in sensor_text and label not in seen_labels:
            seen_labels.add(label)
            found.append({"label": label, "value": default, "threshold": threshold})
    return found


def _detect_oled_actuators(actuators: list[str]) -> list[dict[str, str]]:
    """Scan actuator names and return their OLED status lines."""
    found: list[dict[str, str]] = []
    seen_labels: set[str] = set()
    actuator_text = " ".join(actuators).lower()
    for keyword, label, default in ACTUATOR_OLED_MAP:
        if keyword.lower() in actuator_text and label not in seen_labels:
            seen_labels.add(label)
            found.append({"label": label, "value": default})
    return found


def build_oled_pages(topic: str, sensors: list[str] | None = None,
                     actuators: list[str] | None = None) -> list[dict[str, object]]:
    """Return OLED-ready pages driven by actual component selection."""
    _sensors = sensors or []
    _actuators = actuators or []

    # PID 直流电机——保留专用页面
    if is_pid_dc_motor_topic(topic):
        return [
            {"title": "转速监测", "lines": ["Set : 1500rpm", "Real: 1486rpm", "PWM : 62%", "DIR : FWD"]},
            {"title": "PID 参数", "lines": ["Kp  : 1.20", "Ki  : 0.08", "Kd  : 0.03", "KEY2: Edit"]},
            {"title": "运行状态", "lines": ["MOTOR: RUN", "Current: 0.6A", "Encoder: OK", "Fault: NONE"]},
        ]

    # 密码锁——保留专用页面
    if any(word in topic for word in ("密码锁", "门禁", "智能锁", "电子锁", "门锁")):
        return [
            {"title": "门锁状态", "lines": ["LOCK: LOCKED", "DOOR: CLOSED", "Time: 12:30", "Last: PASS"]},
            {"title": "身份验证", "lines": ["PIN: ****", "Finger: READY", "Try: 3", "KEY1: Enter"]},
            {"title": "管理设置", "lines": ["1.Password", "2.Fingerprint", "3.Alarm limit", "KEY1: Select"]},
        ]

    # 通用：根据实际元器件动态生成
    sensor_items = _detect_oled_sensors(_sensors)
    actuator_items = _detect_oled_actuators(_actuators)

    pages: list[dict[str, object]] = []

    # 页面 1：实时数据（从传感器映射的前 4 项）
    if sensor_items:
        lines = [f"{s['label']:5s}: {s['value']}" for s in sensor_items[:4]]
        fillers = ["State: NORM", "Err  : 0", "---", "---"]
        while len(lines) < 4:
            lines.append(fillers[len(lines) - len(sensor_items[:4])])
        pages.append({"title": "实时数据", "lines": lines[:4]})
    else:
        pages.append({"title": "实时数据", "lines": ["Temp: 25.6C", "Humi: 60%", "State: NORM", "MODE : AUTO"]})

    # 页面 2：设备状态（从执行器映射的前 4 项）
    if actuator_items:
        lines = [f"{a['label']:5s}: {a['value']}" for a in actuator_items[:4]]
        # 不足4行时智能填充：先补MODE，其余补占位
        if len(lines) < 4:
            lines.append("MODE : AUTO")
        while len(lines) < 4:
            lines.append("---")
        pages.append({"title": "设备状态", "lines": lines[:4]})
    else:
        has_network = _match_component(_sensors + _actuators, NETWORK_TERMS) or any(
            term.lower() in topic.lower() for term in NETWORK_TERMS
        )
        if has_network:
            pages.append({"title": "网络状态", "lines": ["WiFi: OK", "MQTT: OK", "IP:192.168.1.x", "Uptime:12h"]})
        else:
            pages.append({"title": "设备状态", "lines": ["Device: OK", "MODE : AUTO", "Uptime: 0h", "Err  : 0"]})

    # 页面 3：阈值设置（从传感器的阈值标签中取前 3 项）
    threshold_lines = [f"{s['threshold']:5s}: --" for s in sensor_items if s.get("threshold")][:3]
    if threshold_lines:
        threshold_lines.append("KEY2: Edit")
    else:
        threshold_lines = ["T.Hi: 30.0C", "H.Lo: 40%", "SW1 : ON", "KEY2: Edit"]
    pages.append({"title": "阈值设置", "lines": threshold_lines[:4]})

    return pages


def build_display_design(topic: str, sensors: list[str] | None = None,
                         actuators: list[str] | None = None) -> list[str]:
    """Human-readable page descriptions retained for documents and compatibility."""
    pages = build_oled_pages(topic, sensors, actuators)
    return [f"页面 {index}｜{page['title']}：{'；'.join(page['lines'])}" for index, page in enumerate(pages, start=1)]


def build_design_logic(topic: str, sensors: list[str], displays: list[str], actuators: list[str]) -> dict[str, Any]:
    controller = choose_controller(topic)
    has_alarm = any(any(term in item for term in ALARM_TERMS) for item in actuators)
    networked = any(term.lower() in topic.lower() for term in NETWORK_TERMS)

    control_rules = []
    if is_pid_dc_motor_topic(topic):
        control_rules.extend(
            [
                {
                    "title": "速度闭环 PID 控制",
                    "detail": "目标转速与编码器反馈转速计算误差；PID 输出映射为 PWM 占空比，并设置积分限幅与输出限幅。",
                },
                {
                    "title": "参数在线调整",
                    "detail": "目标转速、Kp、Ki、Kd 由按键逐项调整，下一控制周期立即生效；这不是传感器阈值控制。",
                },
            ]
        )
    elif actuators:
        control_rules.append(
            {
                "title": "AUTO / MANUAL 模式隔离",
                "detail": "AUTO 模式由传感器阈值控制；MANUAL 模式由按键或上位机控制。每个执行器独立维护模式，切换模式时保持当前状态。",
            }
        )
    if has_alarm:
        control_rules.append(
            {
                "title": "报警静默状态机",
                "detail": "超阈值触发报警；KEY4 或上位机消警后 silenced=1；数据恢复正常时自动清零，下次超阈值可重新报警。",
            }
        )
    if not is_pid_dc_motor_topic(topic):
        control_rules.append(
            {
                "title": "阈值立即生效",
                "detail": "阈值修改后立即参与判断；显示端只回显当前阈值，设置操作与数据展示职责分离。",
            }
        )

    return {
        "controller": controller,
        "function_lines": build_function_lines(topic, sensors, displays, actuators),
        "display_design": build_display_design(topic, sensors, actuators),
        "oled_pages": build_oled_pages(topic, sensors, actuators),
        "button_design": [
            "KEY1：切换显示页面",
            "KEY2：切换当前阈值项目",
            "KEY3：当前阈值加",
            "KEY4：当前阈值减；存在报警器时长按执行消警",
        ],
        "control_rules": control_rules,
        "state_definitions": ["设备状态 = { OFF, ON }", "控制模式 = { AUTO, MANUAL }"],
        "networking": {
            "enabled": networked,
            "protocol": "MQTT" if networked else None,
            "question": "上位机是 APP 还是 Windows 客户端？" if networked else None,
            "note": "联网需求明确时才加入通信模块；STM32 优先使用硬件 UART2 或 UART3。" if networked else "题目未明确联网，本方案不增加通信模块。",
        },
    }
