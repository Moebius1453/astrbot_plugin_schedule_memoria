import json
from datetime import datetime
from pathlib import Path

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.core import AstrBotConfig

import fetcher
import parse_timetable
import query_engine


@register("astrbot_plugin_schedule_memoria", "Moebius1453",
         "课表记忆：抓取教务课表，回答下节课/今日课表", "v0.1.0")
class ScheduleMemoria(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.data_dir = Path(__file__).parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.timetable_path = self.data_dir / "timetable.json"

    def _load_timetable(self) -> dict | None:
        if self.timetable_path.exists():
            return json.loads(self.timetable_path.read_text(encoding="utf-8"))
        return None

    def _save_timetable(self, tb: dict) -> None:
        self.timetable_path.write_text(
            json.dumps(tb, ensure_ascii=False, indent=1), encoding="utf-8"
        )

    def _semester_start(self) -> datetime | None:
        s = str(self.config.get("semester_start", "")).strip()
        return datetime.strptime(s, "%Y-%m-%d") if s else None

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("设置cookie")
    async def set_cookie(self, event: AstrMessageEvent, cookie: str = ""):
        """设置cookie <cookie字符串>：粘贴教务系统浏览器的 cookie"""
        if not cookie:
            yield event.plain_result(
                "用法：设置cookie <cookie字符串>\n"
                "获取：浏览器登录教务 → F12 → Application → Cookies → "
                "jwxt.wuyiu.edu.cn → 复制全部 cookie（名字=值; 名字=值; ...）"
            )
            return
        self.config["cookie"] = cookie
        try:
            data = fetcher.fetch_timetable(
                cookie, self.config.get("semester", "2026-2027-1")
            )
            tb = parse_timetable.parse_timetable_from_bytes(data)
            self._save_timetable(tb)
            yield event.plain_result(
                f"cookie 已保存，课表抓取成功：{tb['学期']}，{len(tb['课程'])} 条课程记录"
            )
        except ValueError as e:
            yield event.plain_result(f"cookie 验证失败：{e}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("刷新课表")
    async def refresh(self, event: AstrMessageEvent):
        """刷新课表：重新抓取当前学期课表（课表变动后使用）"""
        cookie = str(self.config.get("cookie", ""))
        if not cookie:
            yield event.plain_result("尚未设置 cookie，请先：设置cookie <浏览器cookie>")
            return
        try:
            data = fetcher.fetch_timetable(
                cookie, self.config.get("semester", "2026-2027-1")
            )
            tb = parse_timetable.parse_timetable_from_bytes(data)
            self._save_timetable(tb)
            yield event.plain_result(
                f"课表已刷新：{tb['学期']}，{len(tb['课程'])} 条课程记录"
            )
        except ValueError as e:
            yield event.plain_result(str(e))

    @filter.command("下节课")
    async def next_class(self, event: AstrMessageEvent, week: int = -1):
        """下节课 [周次]：下一节课是什么（可指定假设周次）"""
        tb = self._load_timetable()
        if not tb:
            yield event.plain_result("课表未加载，请先让管理员执行：刷新课表")
            return
        start = self._semester_start()
        if not start:
            yield event.plain_result("未配置学期开学日（semester_start），请在插件配置中填写")
            return
        nxt = query_engine.find_next_class(
            tb, datetime.now(), start, week if week > 0 else None
        )
        if not nxt:
            yield event.plain_result("未来 7 天都没有课，享受假期！")
            return
        s, e = query_engine.PERIODS[nxt["节次段"]]
        yield event.plain_result(
            f"下节课：{nxt['课程']}\n"
            f"教师：{nxt['教师']}\n"
            f"地点：{nxt['地点']}\n"
            f"时间：{nxt['日期']} {s}~{e}（第{nxt['周']}周）"
        )

    @filter.command("今日课表")
    async def today(self, event: AstrMessageEvent):
        """今日课表：今天有什么课"""
        tb = self._load_timetable()
        if not tb:
            yield event.plain_result("课表未加载，请先让管理员执行：刷新课表")
            return
        start = self._semester_start()
        if not start:
            yield event.plain_result("未配置学期开学日（semester_start），请在插件配置中填写")
            return
        classes = query_engine.classes_on(tb, datetime.now(), start)
        if not classes:
            yield event.plain_result("今天没有课！")
            return
        lines = []
        for c in classes:
            s, e = query_engine.PERIODS[c["节次段"]]
            lines.append(f"{s}~{e} {c['课程']} | {c['教师']} | {c['地点']}")
        yield event.plain_result("今日课表：\n" + "\n".join(lines))
