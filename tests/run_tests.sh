#!/bin/bash
# 运行所有测试的脚本

echo "======================================"
echo "林麝健康监测系统 - 测试套件"
echo "======================================"

# 设置环境变量
export PYTHONPATH="${PYTHONPATH}:$(pwd)/hikvision-backend"

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

cd "$(dirname "$0")/.."

# 检查pytest是否安装
if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}安装 pytest...${NC}"
    pip install pytest pytest-asyncio
fi

echo ""
echo "======================================"
echo "1. 数据库测试"
echo "======================================"
pytest tests/database/test_tables.py -v --tb=short
DB_RESULT=$?

echo ""
echo "======================================"
echo "2. API 接口测试"
echo "======================================"
pytest tests/api/test_endpoints.py -v --tb=short
API_RESULT=$?

echo ""
echo "======================================"
echo "3. 算法 Pipeline 测试"
echo "======================================"
pytest tests/pipeline/test_algorithm.py -v --tb=short
PIPELINE_RESULT=$?

echo ""
echo "======================================"
echo "4. 集成测试"
echo "======================================"
pytest tests/integration/test_end_to_end.py -v --tb=short
INTEGRATION_RESULT=$?

echo ""
echo "======================================"
echo "测试完成 - 汇总"
echo "======================================"

# 显示结果
if [ $DB_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ 数据库测试: 通过${NC}"
else
    echo -e "${RED}❌ 数据库测试: 失败${NC}"
fi

if [ $API_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ API 接口测试: 通过${NC}"
else
    echo -e "${RED}❌ API 接口测试: 失败${NC}"
fi

if [ $PIPELINE_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ 算法 Pipeline 测试: 通过${NC}"
else
    echo -e "${RED}❌ 算法 Pipeline 测试: 失败${NC}"
fi

if [ $INTEGRATION_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ 集成测试: 通过${NC}"
else
    echo -e "${RED}❌ 集成测试: 失败${NC}"
fi

# 计算总体结果
TOTAL_RESULT=$((DB_RESULT + API_RESULT + PIPELINE_RESULT + INTEGRATION_RESULT))

echo ""
if [ $TOTAL_RESULT -eq 0 ]; then
    echo -e "${GREEN}======================================"
    echo "所有测试通过!"
    echo "======================================${NC}"
    exit 0
else
    echo -e "${RED}======================================"
    echo "部分测试失败，请查看详细报告"
    echo "======================================${NC}"
    exit 1
fi
