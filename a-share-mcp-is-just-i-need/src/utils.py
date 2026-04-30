"""工具函数模块。"""
from contextlib import contextmanager
import logging

import baostock as bs

logger = logging.getLogger(__name__)


@contextmanager
def baostock_login_context():
    """Baostock登录上下文管理器，自动处理登录和登出。"""
    try:
        lg = bs.login()
        if lg.error_code != "0":
            logger.warning("Baostock登录失败: %s", lg.error_msg)
        yield
    finally:
        try:
            bs.logout()
        except Exception:
            logger.debug("Baostock退出时忽略异常", exc_info=True)
