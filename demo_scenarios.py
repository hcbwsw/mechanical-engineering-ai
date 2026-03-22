#!/usr/bin/env python3
"""
演示场景与测试数据生成器
包含5个真实工业场景，可直接导入到系统中测试
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
import random

# 对接「机械工程AI系统/main_app.py」时用此地址（默认 8010，与 main_app 一致）
DEMO_API_BASE = os.environ.get("DEMO_API_BASE", "http://127.0.0.1:8010").rstrip("/")


def demo_to_main_app_diagnosis(
    demo: Dict[str, Any],
    symptoms_text: str = "监测数据异常，详见 sensor_data",
) -> Dict[str, Any]:
    """
    把本文件里的演示 dict（含 device_id、measurement_data 等）
    转成 main_app 接口 POST /api/v1/diagnosis/submit 需要的字段。
    """
    eid = demo.get("equipment_id") or demo.get("device_id") or "demo-device"
    etype = demo.get("equipment_type") or demo.get("device_type") or "unknown"
    sensor: Dict[str, Any] = {}
    md = demo.get("measurement_data")
    if isinstance(md, dict):
        sensor.update(md)
    for k in ("device_name", "location", "facility_name", "rated_power_kw"):
        if k in demo and demo[k] is not None:
            sensor[k] = demo[k]
    return {
        "equipment_id": str(eid),
        "equipment_type": str(etype),
        "symptoms": symptoms_text,
        "sensor_data": sensor,
    }


# =====================================================================
# 场景1: 轴承故障诊断 - 真实案例（工厂常见）
# =====================================================================

class BearingFailureDemo:
    """轴承故障诊断演示"""
    
    @staticmethod
    def get_demo_data() -> Dict[str, Any]:
        """获取轴承故障的典型测量数据"""
        return {
            "device_id": "BEARING-001",
            "device_name": "生产线主轴承",
            "device_type": "rolling_bearing",
            "location": "Assembly Line A",
            "measurement_data": {
                "vibration_amplitude_mm": 0.85,  # 正常 < 0.3mm，中等 0.3-0.7mm，严重 > 0.7mm
                "vibration_frequency_hz": 1250,
                "temperature_celsius": 68,        # 正常 < 50°C，警告 50-70°C，严重 > 70°C
                "noise_level_db": 82,             # 正常 < 75dB，警告 75-85dB，严重 > 85dB
                "rotational_speed_rpm": 1500,
                "lubrication_pressure_bar": 1.2   # 正常 1.5-2.0，低压警告
            },
            "historical_data": [
                {"timestamp": (datetime.now() - timedelta(hours=i)).isoformat(),
                 "vibration_mm": 0.2 + i*0.08,
                 "temperature": 45 + i*2}
                for i in range(1, 11)
            ],
            "expected_diagnosis": {
                "status": "WARNING",
                "primary_cause": "Bearing outer race defect",
                "confidence": 0.89,
                "risk_level": "HIGH",
                "recommended_action": "Replace bearing within 48 hours",
                "estimated_remaining_life": "36-48 hours"
            }
        }

    @staticmethod
    def curl_example() -> str:
        """返回可直接调用 main_app 诊断接口的 curl（已转换字段名）。"""
        body = demo_to_main_app_diagnosis(
            BearingFailureDemo.get_demo_data(),
            symptoms_text="轴承振动与温度偏高，噪声偏大",
        )
        compact = json.dumps(body, ensure_ascii=False)
        return f"""curl -X POST {DEMO_API_BASE}/api/v1/diagnosis/submit \\
  -H "Content-Type: application/json" \\
  -d '{compact}'"""


# =====================================================================
# 场景2: 泵机械密封泄漏 - 预防性维护
# =====================================================================

class PumpSealLeakageDemo:
    """泵机械密封泄漏诊断"""
    
    @staticmethod
    def get_demo_data() -> Dict[str, Any]:
        return {
            "device_id": "PUMP-002",
            "device_name": "化工泵P-101",
            "device_type": "centrifugal_pump",
            "location": "Plant B - Chemical Department",
            "measurement_data": {
                "outlet_pressure_bar": 8.5,
                "inlet_pressure_bar": -0.2,       # 真空度过高
                "flow_rate_m3_h": 45,
                "vibration_amplitude_mm": 0.45,
                "temperature_celsius": 72,
                "seal_leakage_rate_ml_h": 2.5,    # 正常 < 1ml/h，警告 1-5ml/h
                "bearing_temperature": 65
            },
            "maintenance_history": [
                {"date": "2026-02-15", "type": "Seal replacement", "cost": 1200},
                {"date": "2026-01-10", "type": "Bearing lubrication", "cost": 150},
                {"date": "2025-12-01", "type": "Impeller cleaning", "cost": 300}
            ],
            "expected_diagnosis": {
                "status": "PREDICTIVE_MAINTENANCE",
                "primary_cause": "Mechanical seal wear",
                "confidence": 0.92,
                "risk_level": "MEDIUM",
                "recommended_action": "Schedule seal replacement in next maintenance window",
                "estimated_remaining_life": "7-14 days",
                "cost_benefit": "Prevention cost: $1200 vs Emergency repair: $8000+"
            }
        }


# =====================================================================
# 场景3: 电机故障诊断 - 多种故障叠加
# =====================================================================

class MotorFailureDemo:
    """电机绕组短路和轴承问题诊断"""
    
    @staticmethod
    def get_demo_data() -> Dict[str, Any]:
        return {
            "device_id": "MOTOR-003",
            "device_name": "主驱动电机M-401",
            "device_type": "induction_motor",
            "rated_power_kw": 45,
            "location": "Assembly Hall",
            "measurement_data": {
                "phase_current_a": [28.5, 29.2, 27.1],  # 不平衡电流
                "phase_voltage_v": [380, 382, 378],
                "power_factor": 0.78,                     # 正常 0.95+
                "vibration_amplitude_mm": 0.72,
                # 工频 50Hz 的 1×/2×/3× 分量 (Hz)
                "vibration_frequency_hz": [50, 100, 150],
                "winding_temperature": 85,                # 过高
                "bearing_temperature": 72,
                "harmonic_content": {
                    "5th_harmonic_percent": 8.2,
                    "7th_harmonic_percent": 6.5,
                    "thd_total": 12.1                     # THD > 5% 为异常
                }
            },
            "electrical_signatures": {
                "startup_current_inrush_a": 245,
                "locked_rotor_current_a": 250,
                "running_current_a": 28.6,
                "current_imbalance_percent": 6.8         # > 5% 为异常
            },
            "expected_diagnosis": {
                "status": "CRITICAL",
                "detected_faults": [
                    "Phase current imbalance (6.8%)",
                    "High THD (12.1%)",
                    "Elevated winding temperature (85°C)",
                    "Bearing wear signs"
                ],
                "confidence": 0.87,
                "risk_level": "CRITICAL",
                "recommended_action": "STOP OPERATION - Immediate maintenance required",
                "probable_causes": [
                    "Winding inter-turn short circuit (High confidence)",
                    "Bearing degradation (Medium confidence)",
                    "Stator slot contamination (Low confidence)"
                ],
                "emergency_action": "Shutdown within 2 hours to prevent fire risk"
            }
        }


# =====================================================================
# 场景4: 齿轮箱故障 - 齿面磨损和错位
# =====================================================================

class GearboxFailureDemo:
    """齿轮箱齿面磨损和齿轮错位诊断"""
    
    @staticmethod
    def get_demo_data() -> Dict[str, Any]:
        return {
            "device_id": "GEARBOX-004",
            "device_name": "减速齿轮箱GB-501",
            "device_type": "gearbox",
            "ratio": 10,
            "location": "Production Line C",
            "measurement_data": {
                "input_speed_rpm": 1500,
                "output_speed_rpm": 150,
                "input_torque_nm": 250,
                "vibration_amplitude_mm": 1.2,           # 严重 > 0.7mm
                "vibration_frequencies_hz": [75, 150, 300],  # 齿啮频率 = 输入转速×齿数
                "oil_temperature": 78,
                "oil_viscosity_index": 92,
                "oil_particle_count_iso": "18/16/13"    # 正常 < 16/14/11
            },
            "oil_analysis": {
                "iron_particles_ppm": 185,               # 正常 < 50ppm
                "copper_particles_ppm": 15,              # 正常 < 5ppm
                "water_content_percent": 0.8,            # 正常 < 0.3%
                "acid_number_mg_koh_g": 2.1              # 正常 < 1.0
            },
            "expected_diagnosis": {
                "status": "URGENT_MAINTENANCE",
                "primary_cause": "Tooth surface pitting and wear",
                "confidence": 0.94,
                "risk_level": "HIGH",
                "detected_issues": [
                    "High vibration at tooth mesh frequency",
                    "Elevated iron particle count (185ppm)",
                    "Elevated oil acidity (2.1 mg/KOH/g)",
                    "Oil moisture content high (0.8%)"
                ],
                "recommended_action": "Schedule gearbox overhaul within 1 week",
                "repair_scope": [
                    "Replace damaged gears",
                    "Perform oil change",
                    "Inspect shaft alignment",
                    "Replace bearings if necessary"
                ],
                "downtime_estimate": "4-6 hours",
                "cost_estimate": "$3500-5000"
            }
        }


# =====================================================================
# 场景5: 通用设备状态评估 - 综合诊断
# =====================================================================

class ComprehensiveAssessmentDemo:
    """综合设备状态评估 - 多机械系统"""
    
    @staticmethod
    def get_demo_data() -> Dict[str, Any]:
        return {
            "facility_id": "PLANT-A",
            "facility_name": "Manufacturing Plant A",
            "assessment_date": datetime.now().isoformat(),
            "devices": [
                {
                    "device_id": "MOTOR-A1",
                    "status": "GOOD",
                    "health_score": 0.92,
                    "key_metrics": {
                        "vibration_level": "Normal",
                        "temperature": "Normal",
                        "current_balance": "Good"
                    }
                },
                {
                    "device_id": "PUMP-A2",
                    "status": "WARNING",
                    "health_score": 0.68,
                    "key_metrics": {
                        "flow_rate": "Declining",
                        "temperature": "Elevated",
                        "seal_leakage": "Increasing"
                    }
                },
                {
                    "device_id": "COMPRESSOR-A3",
                    "status": "CRITICAL",
                    "health_score": 0.35,
                    "key_metrics": {
                        "discharge_pressure": "Low",
                        "current_draw": "High",
                        "valve_leakage": "Severe"
                    }
                }
            ],
            "summary": {
                "total_devices": 3,
                "healthy": 1,
                "warning": 1,
                "critical": 1,
                "overall_health_score": 0.65,
                "facility_risk_level": "MEDIUM",
                "immediate_actions": [
                    "Repair/Replace compressor valve",
                    "Schedule pump seal maintenance"
                ],
                "preventive_actions": [
                    "Increase motor vibration monitoring",
                    "Plan quarterly system inspection"
                ]
            }
        }


# =====================================================================
# 知识库搜索测试数据
# =====================================================================

class KnowledgeBaseDemo:
    """知识库搜索演示数据"""
    
    @staticmethod
    def get_search_examples() -> List[Dict[str, str]]:
        return [
            {
                "query": "轴承振动诊断标准",
                "expected_results": [
                    "ISO 20816 - Mechanical vibration - Measurement and evaluation",
                    "GB/T 5414 - Vibration severity grades",
                    "Bearing condition monitoring best practices"
                ]
            },
            {
                "query": "泵机械密封更换步骤",
                "expected_results": [
                    "Mechanical seal replacement procedure",
                    "Seal selection guide by fluid type",
                    "Installation torque specifications"
                ]
            },
            {
                "query": "电机故障排查",
                "expected_results": [
                    "Motor troubleshooting flowchart",
                    "Winding resistance testing methods",
                    "Three-phase current analysis guide"
                ]
            }
        ]


# =====================================================================
# Agent执行演示
# =====================================================================

class AgentExecutionDemo:
    """Multi-Agent执行演示"""
    
    @staticmethod
    def get_demo_request() -> Dict[str, Any]:
        return {
            "task": "comprehensive_diagnosis",
            "parameters": {
                "device_id": "BEARING-001",
                "analysis_depth": "full",
                "include_predictive": True,
                "generate_report": True
            },
            "agent_chain": [
                {
                    "agent_id": "data_validator",
                    "task": "Validate measurement data quality"
                },
                {
                    "agent_id": "pattern_analyzer",
                    "task": "Analyze fault patterns against knowledge base"
                },
                {
                    "agent_id": "risk_assessor",
                    "task": "Assess risk level and urgency"
                },
                {
                    "agent_id": "action_recommender",
                    "task": "Recommend maintenance actions"
                },
                {
                    "agent_id": "report_generator",
                    "task": "Generate comprehensive report"
                }
            ]
        }


# =====================================================================
# 完整演示脚本
# =====================================================================

def print_demo_section(title: str):
    """打印演示标题"""
    print("\n" + "="*70)
    print(f"📊 {title}")
    print("="*70)

def generate_all_demos():
    """生成所有演示数据"""
    
    print("\n🎯 机械工程AI诊断系统 - 完整演示数据包\n")
    
    # 场景1
    print_demo_section("场景1: 轴承故障诊断")
    bearing_data = BearingFailureDemo.get_demo_data()
    print(f"设备: {bearing_data['device_name']}")
    print(f"诊断结果: {bearing_data['expected_diagnosis']['status']}")
    print(f"置信度: {bearing_data['expected_diagnosis']['confidence']*100:.1f}%")
    print(f"建议: {bearing_data['expected_diagnosis']['recommended_action']}")
    print("\n📝 curl命令:")
    print(BearingFailureDemo.curl_example())
    
    # 场景2
    print_demo_section("场景2: 泵机械密封泄漏")
    pump_data = PumpSealLeakageDemo.get_demo_data()
    print(f"设备: {pump_data['device_name']}")
    print(f"诊断状态: {pump_data['expected_diagnosis']['status']}")
    print(f"剩余寿命: {pump_data['expected_diagnosis']['estimated_remaining_life']}")
    print(f"成本效益: {pump_data['expected_diagnosis']['cost_benefit']}")
    
    # 场景3
    print_demo_section("场景3: 电机故障诊断")
    motor_data = MotorFailureDemo.get_demo_data()
    print(f"设备: {motor_data['device_name']}")
    print(f"⚠️  紧急等级: {motor_data['expected_diagnosis']['risk_level']}")
    print(f"检测到的故障:")
    for fault in motor_data['expected_diagnosis']['detected_faults']:
        print(f"  • {fault}")
    print(f"紧急行动: {motor_data['expected_diagnosis']['emergency_action']}")
    
    # 场景4
    print_demo_section("场景4: 齿轮箱故障诊断")
    gear_data = GearboxFailureDemo.get_demo_data()
    print(f"设备: {gear_data['device_name']}")
    print(f"油液分析:")
    print(f"  • 铁粒子含量: {gear_data['oil_analysis']['iron_particles_ppm']}ppm (正常 < 50ppm)")
    print(f"  • 铜粒子含量: {gear_data['oil_analysis']['copper_particles_ppm']}ppm (正常 < 5ppm)")
    print(f"  • 水分含量: {gear_data['oil_analysis']['water_content_percent']}% (正常 < 0.3%)")
    print(f"维修范围:")
    for action in gear_data['expected_diagnosis']['repair_scope']:
        print(f"  • {action}")
    
    # 场景5
    print_demo_section("场景5: 综合设备状态评估")
    comprehensive = ComprehensiveAssessmentDemo.get_demo_data()
    print(f"设施: {comprehensive['facility_name']}")
    print(f"设备总数: {comprehensive['summary']['total_devices']}")
    print(f"  ✅ 健康: {comprehensive['summary']['healthy']}")
    print(f"  ⚠️  警告: {comprehensive['summary']['warning']}")
    print(f"  🔴 严重: {comprehensive['summary']['critical']}")
    print(f"设施整体风险: {comprehensive['summary']['facility_risk_level']}")
    print(f"立即行动:")
    for action in comprehensive['summary']['immediate_actions']:
        print(f"  • {action}")
    
    # 知识库
    print_demo_section("知识库搜索示例")
    knowledge = KnowledgeBaseDemo.get_search_examples()
    for i, example in enumerate(knowledge, 1):
        print(f"\n{i}. 查询: {example['query']}")
        print(f"   预期结果:")
        for result in example['expected_results']:
            print(f"   • {result}")
    
    # Agent执行
    print_demo_section("Multi-Agent执行演示")
    agent_demo = AgentExecutionDemo.get_demo_request()
    print(f"任务: {agent_demo['task']}")
    print(f"Agent执行链:")
    for i, agent in enumerate(agent_demo['agent_chain'], 1):
        print(f"  {i}. [{agent['agent_id']}] {agent['task']}")
    
    # 生成JSON文件供导入
    print_demo_section("生成可导入的JSON数据")
    all_data = {
        "bearing_failure": bearing_data,
        "pump_seal_leakage": pump_data,
        "motor_failure": motor_data,
        "gearbox_failure": gear_data,
        "comprehensive_assessment": comprehensive,
        "knowledge_search_examples": knowledge,
        "agent_execution": agent_demo
    }
    
    with open("demo_data.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    
    print("✅ demo_data.json 已生成（原始演示结构，字段名与 main_app 不完全相同）")
    print("\n" + "=" * 70)
    print("📌 不明白？按这三步就够（针对 机械工程AI系统/main_app.py）")
    print("=" * 70)
    print("① 另开终端先启动 API：  python main_app.py")
    print(f"② 浏览器打开文档：      {DEMO_API_BASE}/docs")
    print("③ 找到 POST /api/v1/diagnosis/submit → Try it out")
    print("   把下面整段 JSON 复制到请求体里，点 Execute。")
    print("\n─── 场景1 已转好的请求体（可直接粘贴）───")
    sample = demo_to_main_app_diagnosis(
        bearing_data,
        symptoms_text="轴承振动与温度偏高，噪声偏大",
    )
    print(json.dumps(sample, indent=2, ensure_ascii=False))
    print("\n─── 或在终端执行（同上内容）───")
    print(BearingFailureDemo.curl_example())
    print("\n💡 换端口时：先 set DEMO_API_BASE=http://127.0.0.1:8020 再运行本脚本。")
    print("💡 Python 里取数据：from demo_scenarios import BearingFailureDemo; BearingFailureDemo.get_demo_data()")


if __name__ == "__main__":
    generate_all_demos()
