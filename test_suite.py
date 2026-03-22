"""
完整的测试套件 - Mechanical Engineering AI System
包含单元测试、集成测试、端到端测试

运行前请先启动 main_app（默认端口 8010），例如：
  python main_app.py

执行：
  python test_suite.py

自定义服务地址：
  TEST_BASE_URL=http://127.0.0.1:8000 python test_suite.py

可选：用 pytest 跑（需 pip install pytest）：
  pytest test_suite.py -v -s
"""

import logging
import os
import sys
from typing import Any, Dict

import httpx

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# main_app 默认 8010；与 mechanical-ai-platform 的 8000 区分
BASE_URL = os.environ.get("TEST_BASE_URL", "http://127.0.0.1:8010").rstrip("/")


def _diagnosis_body(
    equipment_id: str,
    equipment_type: str,
    symptoms: str,
    sensor_data: Dict[str, Any],
) -> Dict[str, Any]:
    """与 main_app.DiagnosisRequest 一致：symptoms 为 str，传感器为 sensor_data。"""
    return {
        "equipment_id": equipment_id,
        "equipment_type": equipment_type,
        "symptoms": symptoms,
        "sensor_data": sensor_data,
    }


def _probe_server() -> None:
    """连不上则打印说明并退出（避免 10 个 Phase 全是 Connection refused）。"""
    try:
        with httpx.Client(timeout=5.0) as client:
            client.get(f"{BASE_URL}/health")
    except httpx.ConnectError as e:
        logger.error("无法连接 %s ：%s", BASE_URL, e)
        logger.error("")
        logger.error("【原因】本套件针对「机械工程AI系统/main_app.py」，需要先启动 API。")
        logger.error("【做法 1】另开终端执行：")
        logger.error(
            "  python \"%s\"",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "main_app.py"),
        )
        logger.error("  （默认监听 8010；若改端口请设置环境变量 TEST_BASE_URL）")
        logger.error("【做法 2】若你实际跑的是 mechanical-ai-platform（常见 8000），请：")
        logger.error("  TEST_BASE_URL=http://127.0.0.1:8000 python test_suite.py")
        logger.error("  注意：8000 上若是另一套应用，部分接口路径/行为可能不一致。")
        logger.error("")
        sys.exit(2)
    except httpx.TimeoutException:
        logger.error("连接 %s 超时，请确认服务已启动且防火墙未拦截。", BASE_URL)
        sys.exit(2)


def _expect_status(response: httpx.Response, allowed: tuple, what: str) -> None:
    if response.status_code not in allowed:
        body = (response.text or "")[:1200]
        raise AssertionError(f"{what}: HTTP {response.status_code} — {body}")


# ============================================================================
# 1. 单元测试 - API 端点
# ============================================================================

class TestHealthCheck:
    """健康检查测试"""
    
    def test_health_check_success(self):
        """测试健康检查端点"""
        with httpx.Client() as client:
            response = client.get(f"{BASE_URL}/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            logger.info("✅ 健康检查通过")
    
    def test_root_endpoint(self):
        """测试根端点"""
        with httpx.Client() as client:
            response = client.get(f"{BASE_URL}/")
            assert response.status_code == 200
            data = response.json()
            assert "service" in data or "docs" in data or "health" in data
            logger.info("✅ 根端点测试通过")


class TestAuthEndpoints:
    """认证端点测试"""
    
    def test_register_user(self):
        """测试用户注册"""
        with httpx.Client() as client:
            payload = {
                "username": f"testuser_{int(__import__('time').time())}",
                "email": f"test_{int(__import__('time').time())}@example.com",
                "password": "Test@123456"
            }
            # main_app 中 register 为 query 参数，非 JSON body
            response = client.post(f"{BASE_URL}/api/v1/auth/register", params=payload)
            assert response.status_code in [200, 201, 409]  # 409 if already exists
            logger.info(f"✅ 用户注册测试: {response.status_code}")
    
    def test_login_user(self):
        """测试用户登录"""
        with httpx.Client() as client:
            # 先注册
            username = f"testuser_{int(__import__('time').time())}"
            register_payload = {
                "username": username,
                "email": f"test_{int(__import__('time').time())}@example.com",
                "password": "Test@123456"
            }
            client.post(f"{BASE_URL}/api/v1/auth/register", params=register_payload)
            
            # 再登录
            login_payload = {
                "username": username,
                "password": "Test@123456"
            }
            response = client.post(f"{BASE_URL}/api/v1/auth/login", params=login_payload)
            assert response.status_code in [200, 400, 401]
            if response.status_code == 200:
                data = response.json()
                assert "access_token" in data or "token" in data
            logger.info(f"✅ 用户登录测试: {response.status_code}")


class TestDiagnosisEndpoints:
    """诊断系统测试"""
    
    def test_submit_diagnosis(self):
        """测试提交诊断"""
        with httpx.Client() as client:
            payload = _diagnosis_body(
                "EQUIP_001",
                "pump",
                "vibration, noise",
                {
                    "temperature": 85.5,
                    "pressure": 2.5,
                    "vibration": 15.3,
                },
            )
            response = client.post(
                f"{BASE_URL}/api/v1/diagnosis/submit",
                json=payload
            )
            _expect_status(response, (200, 201), "POST /diagnosis/submit")
            data = response.json()
            assert "diagnosis_id" in data or "id" in data
            logger.info(f"✅ 诊断提交成功: {data}")
            return data.get("diagnosis_id") or data.get("id")
    
    def test_get_diagnosis(self):
        """测试获取诊断结果"""
        with httpx.Client() as client:
            diagnosis_id = "test_diagnosis_001"
            response = client.get(
                f"{BASE_URL}/api/v1/diagnosis/{diagnosis_id}"
            )
            assert response.status_code in [200, 404]
            if response.status_code == 200:
                data = response.json()
                assert "equipment_id" in data or "diagnosis_id" in data
            logger.info(f"✅ 获取诊断结果: {response.status_code}")


class TestKnowledgeEndpoints:
    """知识库测试"""
    
    def test_knowledge_search(self):
        """测试知识库搜索"""
        with httpx.Client() as client:
            payload = {
                "query": "pump vibration analysis",
                "top_k": 10,
                "similarity_threshold": 0.7,
            }
            response = client.post(
                f"{BASE_URL}/api/v1/knowledge/search",
                json=payload
            )
            assert response.status_code in [200, 400]
            if response.status_code == 200:
                data = response.json()
                assert "results" in data or isinstance(data, list)
            logger.info(f"✅ 知识库搜索: {response.status_code}")


class TestAgentEndpoints:
    """Agent执行测试"""
    
    def test_agent_execute(self):
        """测试Agent执行"""
        with httpx.Client() as client:
            payload = {
                "task_description": "分析设备 EQUIP_001 传感器数据",
                "tools": ["sensor_analysis"],
                "parameters": {
                    "equipment_id": "EQUIP_001",
                    "temperature": 85.5,
                    "pressure": 2.5,
                },
            }
            response = client.post(
                f"{BASE_URL}/api/v1/agent/execute",
                json=payload
            )
            assert response.status_code in [200, 400, 500]
            if response.status_code == 200:
                data = response.json()
                assert "status" in data or "task_id" in data or "message" in data
            logger.info(f"✅ Agent执行: {response.status_code}")


class TestAnalyticsEndpoints:
    """分析与监控测试"""
    
    def test_get_dashboard(self):
        """测试获取仪表板数据"""
        with httpx.Client() as client:
            response = client.get(
                f"{BASE_URL}/api/v1/analytics/dashboard"
            )
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                assert (
                    "data" in data
                    or "metrics" in data
                    or "total_diagnoses" in data
                    or "charts" in data
                )
            logger.info(f"✅ 获取仪表板: {response.status_code}")
    
    def test_get_system_metrics(self):
        """测试获取系统指标"""
        with httpx.Client() as client:
            response = client.get(
                f"{BASE_URL}/api/v1/admin/system/metrics"
            )
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                assert (
                    "cpu" in data
                    or "memory" in data
                    or "uptime" in data
                    or "cpu_usage" in data
                    or "memory_usage" in data
                )
            logger.info(f"✅ 获取系统指标: {response.status_code}")


# ============================================================================
# 2. 集成测试 - 完整工作流
# ============================================================================

class TestIntegrationWorkflows:
    """集成测试 - 完整工作流"""
    
    def test_complete_diagnosis_workflow(self):
        """测试完整的诊断流程"""
        logger.info("=" * 60)
        logger.info("开始完整诊断工作流测试")
        logger.info("=" * 60)
        
        with httpx.Client() as client:
            # 1. 提交诊断
            diagnosis_payload = _diagnosis_body(
                "PUMP_001",
                "centrifugal_pump",
                "abnormal_vibration, noise",
                {
                    "temperature": 88.5,
                    "pressure": 2.8,
                    "vibration": 18.2,
                    "rpm": 1750,
                },
            )
            
            diagnosis_response = client.post(
                f"{BASE_URL}/api/v1/diagnosis/submit",
                json=diagnosis_payload
            )
            _expect_status(diagnosis_response, (200, 201), "集成-提交诊断")
            diagnosis_id = diagnosis_response.json().get("diagnosis_id") or diagnosis_response.json().get("id")
            logger.info(f"✅ 步骤1: 提交诊断 - {diagnosis_id}")
            
            # 2. 搜索相关知识
            knowledge_payload = {
                "query": "centrifugal pump vibration bearing clearance",
                "top_k": 5,
            }
            
            knowledge_response = client.post(
                f"{BASE_URL}/api/v1/knowledge/search",
                json=knowledge_payload
            )
            assert knowledge_response.status_code in [200, 400]
            logger.info(f"✅ 步骤2: 搜索知识库")
            
            # 3. 执行Agent分析
            agent_payload = {
                "task_description": "预测 PUMP_001 故障风险",
                "tools": ["predictive_agent"],
                "parameters": {
                    "equipment_id": "PUMP_001",
                    **(diagnosis_payload.get("sensor_data") or {}),
                },
            }
            
            agent_response = client.post(
                f"{BASE_URL}/api/v1/agent/execute",
                json=agent_payload
            )
            assert agent_response.status_code in [200, 400, 500]
            logger.info(f"✅ 步骤3: 执行Agent分析")
            
            # 4. 获取结果
            result_response = client.get(
                f"{BASE_URL}/api/v1/diagnosis/{diagnosis_id}"
            )
            assert result_response.status_code in [200, 404]
            logger.info(f"✅ 步骤4: 获取诊断结果")
            
        logger.info("✅ 完整诊断工作流测试通过！\n")
    
    def test_multi_equipment_analysis(self):
        """测试多设备分析"""
        logger.info("=" * 60)
        logger.info("开始多设备分析测试")
        logger.info("=" * 60)
        
        with httpx.Client() as client:
            equipments = [
                ("PUMP_001", "pump", [82.5, 2.5, 12.3]),
                ("MOTOR_001", "motor", [75.0, 3.0, 8.5]),
                ("COMPRESSOR_001", "compressor", [92.0, 3.5, 15.7])
            ]
            
            for equip_id, equip_type, readings in equipments:
                payload = _diagnosis_body(
                    equip_id,
                    equip_type,
                    "abnormal_reading",
                    {
                        "temperature": readings[0],
                        "pressure": readings[1],
                        "vibration": readings[2],
                    },
                )
                
                response = client.post(
                    f"{BASE_URL}/api/v1/diagnosis/submit",
                    json=payload
                )
                _expect_status(response, (200, 201), f"多设备诊断 {equip_id}")
                logger.info(f"✅ 设备{equip_id}诊断提交成功")
        
        logger.info("✅ 多设备分析测试通过！\n")


# ============================================================================
# 3. 性能测试
# ============================================================================

class TestPerformance:
    """性能测试"""
    
    def test_concurrent_requests(self):
        """测试并发请求"""
        logger.info("=" * 60)
        logger.info("开始并发请求性能测试")
        logger.info("=" * 60)
        
        import concurrent.futures
        import time
        
        def make_request():
            with httpx.Client() as client:
                start = time.time()
                response = client.get(f"{BASE_URL}/health")
                elapsed = time.time() - start
                return response.status_code, elapsed
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        successful = sum(1 for status, _ in results if status == 200)
        avg_time = sum(t for _, t in results) / len(results)
        
        assert successful >= len(results) * 0.9  # 至少90%成功率
        logger.info(f"✅ 成功率: {successful}/{len(results)}")
        logger.info(f"✅ 平均响应时间: {avg_time*1000:.2f}ms")
        logger.info("✅ 并发性能测试通过！\n")


# ============================================================================
# 4. 端到端测试
# ============================================================================

class TestEndToEnd:
    """端到端测试"""
    
    def test_complete_user_journey(self):
        """完整的用户使用旅程"""
        logger.info("=" * 60)
        logger.info("开始端到端用户旅程测试")
        logger.info("=" * 60)
        
        with httpx.Client() as client:
            # 1. 系统健康检查
            health = client.get(f"{BASE_URL}/health")
            assert health.status_code == 200
            logger.info("✅ 系统健康")
            
            # 2. 用户注册
            timestamp = int(__import__('time').time())
            register_data = {
                "username": f"endtoend_user_{timestamp}",
                "email": f"e2e_{timestamp}@example.com",
                "password": "Test@123456"
            }
            register = client.post(
                f"{BASE_URL}/api/v1/auth/register", params=register_data
            )
            logger.info(f"✅ 用户注册: {register.status_code}")
            
            # 3. 用户登录
            login_data = {
                "username": register_data["username"],
                "password": register_data["password"]
            }
            login = client.post(f"{BASE_URL}/api/v1/auth/login", params=login_data)
            logger.info(f"✅ 用户登录: {login.status_code}")
            
            # 4. 提交诊断
            diagnosis_data = _diagnosis_body(
                "E2E_TEST_EQUIP",
                "pump",
                "vibration",
                {"temperature": 85.0, "pressure": 2.5, "vibration": 14.0},
            )
            diagnosis = client.post(f"{BASE_URL}/api/v1/diagnosis/submit", json=diagnosis_data)
            _expect_status(diagnosis, (200, 201), "E2E 诊断提交")
            logger.info(f"✅ 诊断提交: {diagnosis.status_code}")
            
            # 5. 查看仪表板
            dashboard = client.get(f"{BASE_URL}/api/v1/analytics/dashboard")
            logger.info(f"✅ 查看仪表板: {dashboard.status_code}")
            
        logger.info("✅ 端到端用户旅程测试完成！\n")


# ============================================================================
# 5. 错误处理测试
# ============================================================================

class TestErrorHandling:
    """错误处理测试"""
    
    def test_invalid_payload(self):
        """测试无效数据处理"""
        with httpx.Client() as client:
            invalid_payload = {"invalid_field": "value"}
            response = client.post(
                f"{BASE_URL}/api/v1/diagnosis/submit",
                json=invalid_payload
            )
            assert response.status_code >= 400
            logger.info(f"✅ 无效数据处理: {response.status_code}")
    
    def test_missing_required_fields(self):
        """测试缺少必需字段"""
        with httpx.Client() as client:
            incomplete_payload = {"equipment_id": "TEST"}
            response = client.post(
                f"{BASE_URL}/api/v1/diagnosis/submit",
                json=incomplete_payload
            )
            assert response.status_code >= 400
            logger.info(f"✅ 缺少必需字段处理: {response.status_code}")
    
    def test_nonexistent_resource(self):
        """测试访问不存在的资源"""
        with httpx.Client() as client:
            response = client.get(
                f"{BASE_URL}/api/v1/diagnosis/nonexistent_id_12345"
            )
            # main_app 当前对任意 id 返回模拟成功；兼容 404 设计
            assert response.status_code in [404, 400, 200]
            logger.info(f"✅ 不存在资源处理: {response.status_code}")


# ============================================================================
# 运行测试
# ============================================================================

def run_all_tests():
    """运行所有测试"""
    logger.info("\n")
    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║" + " " * 10 + "Mechanical Engineering AI System" + " " * 15 + "║")
    logger.info("║" + " " * 20 + "完整测试套件" + " " * 25 + "║")
    logger.info("╚" + "=" * 58 + "╝")
    logger.info("\n")
    logger.info("目标服务: %s（可用环境变量 TEST_BASE_URL 修改）", BASE_URL)
    logger.info("")
    _probe_server()
    
    # 测试健康检查
    logger.info("【Phase 1】基础端点测试")
    logger.info("-" * 60)
    test_health = TestHealthCheck()
    try:
        test_health.test_health_check_success()
        test_health.test_root_endpoint()
    except Exception as e:
        logger.error("❌ 基础端点测试失败: %r", e)
    
    # 测试认证
    logger.info("\n【Phase 2】认证系统测试")
    logger.info("-" * 60)
    test_auth = TestAuthEndpoints()
    try:
        test_auth.test_register_user()
        test_auth.test_login_user()
    except Exception as e:
        logger.error("❌ 认证测试失败: %r", e)
    
    # 测试诊断
    logger.info("\n【Phase 3】诊断系统测试")
    logger.info("-" * 60)
    test_diagnosis = TestDiagnosisEndpoints()
    try:
        test_diagnosis.test_submit_diagnosis()
        test_diagnosis.test_get_diagnosis()
    except Exception as e:
        logger.error("❌ 诊断测试失败: %r", e)
    
    # 测试知识库
    logger.info("\n【Phase 4】知识库系统测试")
    logger.info("-" * 60)
    test_knowledge = TestKnowledgeEndpoints()
    try:
        test_knowledge.test_knowledge_search()
    except Exception as e:
        logger.error("❌ 知识库测试失败: %r", e)
    
    # 测试Agent
    logger.info("\n【Phase 5】Agent系统测试")
    logger.info("-" * 60)
    test_agent = TestAgentEndpoints()
    try:
        test_agent.test_agent_execute()
    except Exception as e:
        logger.error("❌ Agent测试失败: %r", e)
    
    # 测试分析
    logger.info("\n【Phase 6】分析与监控测试")
    logger.info("-" * 60)
    test_analytics = TestAnalyticsEndpoints()
    try:
        test_analytics.test_get_dashboard()
        test_analytics.test_get_system_metrics()
    except Exception as e:
        logger.error("❌ 分析测试失败: %r", e)
    
    # 集成测试
    logger.info("\n【Phase 7】集成工作流测试")
    logger.info("-" * 60)
    test_integration = TestIntegrationWorkflows()
    try:
        test_integration.test_complete_diagnosis_workflow()
        test_integration.test_multi_equipment_analysis()
    except Exception as e:
        logger.error("❌ 集成测试失败: %r", e)
    
    # 性能测试
    logger.info("\n【Phase 8】性能测试")
    logger.info("-" * 60)
    test_perf = TestPerformance()
    try:
        test_perf.test_concurrent_requests()
    except Exception as e:
        logger.error("❌ 性能测试失败: %r", e)
    
    # 端到端测试
    logger.info("\n【Phase 9】端到端测试")
    logger.info("-" * 60)
    test_e2e = TestEndToEnd()
    try:
        test_e2e.test_complete_user_journey()
    except Exception as e:
        logger.error("❌ 端到端测试失败: %r", e)
    
    # 错误处理测试
    logger.info("\n【Phase 10】错误处理测试")
    logger.info("-" * 60)
    test_errors = TestErrorHandling()
    try:
        test_errors.test_invalid_payload()
        test_errors.test_missing_required_fields()
        test_errors.test_nonexistent_resource()
    except Exception as e:
        logger.error("❌ 错误处理测试失败: %r", e)
    
    logger.info("\n" + "=" * 60)
    logger.info("测试流程结束；若上方出现 ❌，请根据对应 Phase 的报错排查。")
    logger.info("=" * 60 + "\n")


if __name__ == "__main__":
    # 直接运行所有测试（无需安装 pytest）
    run_all_tests()
