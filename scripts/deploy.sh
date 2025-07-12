#!/bin/bash

# TradeFan 部署脚本
# 支持开发、测试、生产环境部署

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 默认参数
ENVIRONMENT="development"
ACTION="deploy"
SKIP_TESTS=false
FORCE_REBUILD=false

# 帮助信息
show_help() {
    cat << EOF
TradeFan 部署脚本

用法: $0 [选项]

选项:
    -e, --environment ENV    部署环境 (development|testing|staging|production)
    -a, --action ACTION      执行动作 (deploy|start|stop|restart|status|logs)
    -s, --skip-tests         跳过测试
    -f, --force-rebuild      强制重新构建镜像
    -h, --help              显示帮助信息

示例:
    $0 -e production -a deploy
    $0 -e development -a start
    $0 -a logs
    $0 -a status

EOF
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -a|--action)
            ACTION="$2"
            shift 2
            ;;
        -s|--skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        -f|--force-rebuild)
            FORCE_REBUILD=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 验证环境参数
if [[ ! "$ENVIRONMENT" =~ ^(development|testing|staging|production)$ ]]; then
    log_error "无效的环境: $ENVIRONMENT"
    exit 1
fi

# 验证动作参数
if [[ ! "$ACTION" =~ ^(deploy|start|stop|restart|status|logs|cleanup)$ ]]; then
    log_error "无效的动作: $ACTION"
    exit 1
fi

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

log_info "TradeFan 部署脚本启动"
log_info "环境: $ENVIRONMENT"
log_info "动作: $ACTION"
log_info "项目目录: $PROJECT_ROOT"

# 检查依赖
check_dependencies() {
    log_info "检查系统依赖..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        exit 1
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装"
        exit 1
    fi
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi
    
    log_success "系统依赖检查通过"
}

# 运行测试
run_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        log_warning "跳过测试"
        return 0
    fi
    
    log_info "运行测试..."
    
    # 基础功能测试
    if [[ -f "tests/test_basic_functionality.py" ]]; then
        python3 tests/test_basic_functionality.py
        if [[ $? -ne 0 ]]; then
            log_error "基础功能测试失败"
            exit 1
        fi
    fi
    
    # 指标库测试
    if [[ -f "indicators_lib/test_indicators.py" ]]; then
        python3 indicators_lib/test_indicators.py
        if [[ $? -ne 0 ]]; then
            log_error "指标库测试失败"
            exit 1
        fi
    fi
    
    # 运行pytest (如果存在)
    if command -v pytest &> /dev/null && [[ -d "tests" ]]; then
        pytest tests/ -v
        if [[ $? -ne 0 ]]; then
            log_error "Pytest 测试失败"
            exit 1
        fi
    fi
    
    log_success "所有测试通过"
}

# 准备配置文件
prepare_configs() {
    log_info "准备配置文件..."
    
    # 创建必要的目录
    mkdir -p config/environments
    mkdir -p logs
    mkdir -p data
    mkdir -p results
    
    # 生成环境配置
    python3 -c "
from modules.config_manager import get_config_manager
manager = get_config_manager()
manager.create_environment_configs()
print('配置文件生成完成')
"
    
    # 设置环境变量文件
    ENV_FILE=".env.${ENVIRONMENT}"
    cat > "$ENV_FILE" << EOF
# TradeFan ${ENVIRONMENT} 环境配置
ENVIRONMENT=${ENVIRONMENT}
COMPOSE_PROJECT_NAME=tradefan-${ENVIRONMENT}

# 数据库配置
INFLUX_URL=http://influxdb:8086
INFLUX_TOKEN=tradefan-super-secret-auth-token
INFLUX_ORG=tradefan
INFLUX_BUCKET=market_data

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=tradefan123

# 监控配置
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000

# 应用配置
LOG_LEVEL=INFO
DEBUG=false
EOF
    
    log_success "配置文件准备完成"
}

# 构建镜像
build_images() {
    log_info "构建Docker镜像..."
    
    BUILD_ARGS=""
    if [[ "$FORCE_REBUILD" == "true" ]]; then
        BUILD_ARGS="--no-cache"
    fi
    
    docker-compose --env-file ".env.${ENVIRONMENT}" build $BUILD_ARGS
    
    if [[ $? -eq 0 ]]; then
        log_success "镜像构建完成"
    else
        log_error "镜像构建失败"
        exit 1
    fi
}

# 部署服务
deploy_services() {
    log_info "部署服务..."
    
    # 停止现有服务
    docker-compose --env-file ".env.${ENVIRONMENT}" down
    
    # 启动服务
    docker-compose --env-file ".env.${ENVIRONMENT}" up -d
    
    if [[ $? -eq 0 ]]; then
        log_success "服务部署完成"
    else
        log_error "服务部署失败"
        exit 1
    fi
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 30
    
    # 健康检查
    check_health
}

# 健康检查
check_health() {
    log_info "执行健康检查..."
    
    # 检查容器状态
    CONTAINERS=$(docker-compose --env-file ".env.${ENVIRONMENT}" ps -q)
    
    for container in $CONTAINERS; do
        status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no-health-check")
        name=$(docker inspect --format='{{.Name}}' "$container" | sed 's/\///')
        
        if [[ "$status" == "healthy" ]] || [[ "$status" == "no-health-check" ]]; then
            log_success "容器 $name 状态正常"
        else
            log_warning "容器 $name 状态: $status"
        fi
    done
    
    # 检查端口连通性
    check_port "localhost" "8086" "InfluxDB"
    check_port "localhost" "6379" "Redis"
    check_port "localhost" "9090" "Prometheus"
    check_port "localhost" "3000" "Grafana"
    check_port "localhost" "8000" "TradeFan App"
}

# 检查端口
check_port() {
    local host=$1
    local port=$2
    local service=$3
    
    if timeout 5 bash -c "</dev/tcp/$host/$port" 2>/dev/null; then
        log_success "$service ($host:$port) 连接正常"
    else
        log_warning "$service ($host:$port) 连接失败"
    fi
}

# 启动服务
start_services() {
    log_info "启动服务..."
    docker-compose --env-file ".env.${ENVIRONMENT}" start
    log_success "服务启动完成"
}

# 停止服务
stop_services() {
    log_info "停止服务..."
    docker-compose --env-file ".env.${ENVIRONMENT}" stop
    log_success "服务停止完成"
}

# 重启服务
restart_services() {
    log_info "重启服务..."
    docker-compose --env-file ".env.${ENVIRONMENT}" restart
    log_success "服务重启完成"
}

# 查看状态
show_status() {
    log_info "服务状态:"
    docker-compose --env-file ".env.${ENVIRONMENT}" ps
    
    echo ""
    log_info "系统资源使用:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
}

# 查看日志
show_logs() {
    log_info "查看服务日志..."
    docker-compose --env-file ".env.${ENVIRONMENT}" logs -f --tail=100
}

# 清理资源
cleanup() {
    log_info "清理资源..."
    
    # 停止并删除容器
    docker-compose --env-file ".env.${ENVIRONMENT}" down -v
    
    # 清理未使用的镜像
    docker image prune -f
    
    # 清理未使用的卷
    docker volume prune -f
    
    log_success "资源清理完成"
}

# 主执行逻辑
main() {
    case $ACTION in
        deploy)
            check_dependencies
            run_tests
            prepare_configs
            build_images
            deploy_services
            ;;
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        cleanup)
            cleanup
            ;;
    esac
}

# 执行主函数
main

log_success "操作完成!"

# 显示访问信息
if [[ "$ACTION" == "deploy" ]] || [[ "$ACTION" == "start" ]]; then
    echo ""
    log_info "服务访问地址:"
    echo "  - Grafana 监控面板: http://localhost:3000 (admin/tradefan123)"
    echo "  - Prometheus 监控: http://localhost:9090"
    echo "  - InfluxDB 管理: http://localhost:8086"
    echo "  - TradeFan 指标: http://localhost:8000/metrics"
    echo ""
    log_info "常用命令:"
    echo "  - 查看状态: $0 -e $ENVIRONMENT -a status"
    echo "  - 查看日志: $0 -e $ENVIRONMENT -a logs"
    echo "  - 重启服务: $0 -e $ENVIRONMENT -a restart"
fi
