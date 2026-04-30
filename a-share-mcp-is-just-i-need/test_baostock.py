"""测试baostock数据源是否正常工作。"""
import sys

import baostock as bs


def row_to_dict(result_set):
    """将 Baostock 当前行转换为字典。"""
    return dict(zip(result_set.fields, result_set.get_row_data()))


def test_baostock():
    """测试baostock连接和数据获取。"""
    print("测试baostock数据源...")

    lg = bs.login()
    if lg.error_code != "0":
        print(f"登录失败: {lg.error_msg}")
        return False
    print("✓ 登录成功")

    rs = bs.query_stock_basic(code="sh.600519")
    if rs.error_code == "0" and rs.next():
        row = row_to_dict(rs)
        print(f"✓ 获取股票信息成功: {row.get('code_name', '')}")
    else:
        print("✗ 获取股票信息失败")
        bs.logout()
        return False

    rs = bs.query_history_k_data_plus(
        code="sh.600519",
        fields="date,open,high,low,close,volume",
        start_date="2024-01-01",
        end_date="2024-01-31",
        frequency="d",
    )

    count = 0
    while rs.error_code == "0" and rs.next():
        count += 1
    print(f"✓ 获取K线数据成功: {count}条记录")

    bs.logout()
    print("✓ 所有测试通过!")
    return True


if __name__ == "__main__":
    success = test_baostock()
    sys.exit(0 if success else 1)
