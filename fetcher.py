import requests

BASE_URL = "https://jwxt.wuyiu.edu.cn"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome"

# 课表导出 URL 模板（学期参数 xnxq01id 可切换）
XSKB_URL = (
    BASE_URL + "/jsxsd/xskb/xskb_print.do"
    "?viweType=0&showallprint=0&showkchprint=0&showkink=0&showfzmprint=0"
    "&baseUrl=%2Fjsxsd&xsflMapListJsonStr=%E8%AE%B2%E8%AF%BE%E5%AD%A6%E6%97%B6%2C%E5%AE%9E%E9%AA%8C%E5%AD%A6%E6%97%B6%2C%E4%B8%8A%E6%9C%BA%E5%AD%A6%E6%97%B6%2C%E5%AE%9E%E8%B7%B5%E5%AD%A6%E6%97%B6%2C"
    "&xnxq01id={semester}&zc=&kbjcmsid=99"
)

# Excel 魔数（OLE2）：d0 cf 11 e0
_XLS_MAGIC = b"\xd0\xcf\x11\xe0"


def fetch_timetable(cookie_str: str, semester: str) -> bytes:
    """用浏览器 cookie 抓课表 xls。cookie 过期时抛 ValueError"""
    headers = {"Cookie": cookie_str, "User-Agent": UA}
    r = requests.get(XSKB_URL.format(semester=semester), headers=headers, timeout=30)
    if r.status_code != 200:
        raise ValueError(f"课表请求失败: HTTP {r.status_code}")
    if not r.content.startswith(_XLS_MAGIC):
        # 返回了 HTML（登录页）→ cookie 过期
        raise ValueError("获取课表失败：返回的不是课表文件，cookie 可能已过期，请重新粘贴")
    return r.content


def is_cookie_expired(cookie_str: str) -> bool:
    """轻量检查 cookie 是否有效（请求最新学期课表）"""
    try:
        fetch_timetable(cookie_str, "2025-2026-2")
        return False
    except ValueError:
        return True
