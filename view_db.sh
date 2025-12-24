#!/bin/bash

# Script để xem dữ liệu trong database nhanh chóng
# Usage: ./view_db.sh [option]
# Options:
#   -a, --all      Xem tất cả
#   -c, --customers   Xem khách hàng
#   -o, --orders      Xem đơn hàng
#   -b, --branches    Xem chi nhánh
#   -l, --logs        Xem logs nhận diện
#   -s, --stats       Xem thống kê

# Màu sắc
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function để chạy query
run_query() {
    docker compose exec -T postgres psql -U faceid -d faceid -c "$1"
}

# Function xem branches
view_branches() {
    echo -e "${BLUE}=== DANH SÁCH CHI NHÁNH ===${NC}"
    run_query "SELECT id, name, location, description, created_at FROM branches ORDER BY id;"
    echo ""
}

# Function xem customers
view_customers() {
    echo -e "${BLUE}=== DANH SÁCH KHÁCH HÀNG ===${NC}"
    run_query "SELECT id, name, phone, email, created_at FROM customers ORDER BY created_at DESC LIMIT 20;"
    echo ""
}

# Function xem orders
view_orders() {
    echo -e "${BLUE}=== ĐƠN HÀNG GẦN NHẤT ===${NC}"
    run_query "
    SELECT 
        o.id,
        o.created_at,
        c.name as customer_name,
        b.name as branch_name,
        o.total_amount,
        o.status
    FROM orders o
    JOIN customers c ON o.customer_id = c.id
    JOIN branches b ON o.branch_id = b.id
    ORDER BY o.created_at DESC
    LIMIT 20;
    "
    echo ""
}

# Function xem logs
view_logs() {
    echo -e "${BLUE}=== LOGS NHẬN DIỆN GẦN NHẤT ===${NC}"
    run_query "
    SELECT 
        rl.id,
        rl.created_at,
        c.name as customer_name,
        b.name as branch_name,
        rl.recognized,
        rl.confidence
    FROM recognition_logs rl
    LEFT JOIN customers c ON rl.customer_id = c.id
    LEFT JOIN branches b ON rl.branch_id = b.id
    ORDER BY rl.created_at DESC
    LIMIT 20;
    "
    echo ""
}

# Function xem stats
view_stats() {
    echo -e "${GREEN}=== THỐNG KÊ TỔNG QUAN ===${NC}"
    
    echo -e "${YELLOW}Tổng số chi nhánh:${NC}"
    run_query "SELECT COUNT(*) as total FROM branches;"
    
    echo -e "${YELLOW}Tổng số khách hàng:${NC}"
    run_query "SELECT COUNT(*) as total FROM customers;"
    
    echo -e "${YELLOW}Tổng số đơn hàng:${NC}"
    run_query "SELECT COUNT(*) as total FROM orders;"
    
    echo -e "${YELLOW}Tổng số logs nhận diện:${NC}"
    run_query "SELECT COUNT(*) as total FROM recognition_logs;"
    
    echo -e "${YELLOW}Tổng doanh thu:${NC}"
    run_query "SELECT COALESCE(SUM(total_amount), 0) as total_revenue FROM orders;"
    
    echo -e "${YELLOW}Tỷ lệ nhận diện thành công:${NC}"
    run_query "
    SELECT 
        COUNT(*) as total_attempts,
        SUM(CASE WHEN recognized = true THEN 1 ELSE 0 END) as successful,
        ROUND(100.0 * SUM(CASE WHEN recognized = true THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate_percent
    FROM recognition_logs;
    "
    
    echo ""
}

# Function xem tất cả
view_all() {
    view_stats
    view_branches
    view_customers
    view_orders
    view_logs
}

# Main
case "${1:-}" in
    -a|--all)
        view_all
        ;;
    -c|--customers)
        view_customers
        ;;
    -o|--orders)
        view_orders
        ;;
    -b|--branches)
        view_branches
        ;;
    -l|--logs)
        view_logs
        ;;
    -s|--stats)
        view_stats
        ;;
    "")
        view_all
        ;;
    *)
        echo "Usage: $0 [option]"
        echo "Options:"
        echo "  -a, --all       Xem tất cả"
        echo "  -c, --customers Xem khách hàng"
        echo "  -o, --orders    Xem đơn hàng"
        echo "  -b, --branches  Xem chi nhánh"
        echo "  -l, --logs      Xem logs nhận diện"
        echo "  -s, --stats     Xem thống kê"
        exit 1
        ;;
esac

