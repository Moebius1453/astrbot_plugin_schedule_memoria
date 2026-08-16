from datetime import datetime, timedelta

# 节次段 → 时间段（来自课表 xls 行 0 列）
PERIODS = {
    1: ("08:00", "09:40"),
    2: ("10:00", "11:40"),
    3: ("14:30", "16:10"),
    4: ("16:20", "18:00"),
    5: ("19:00", "20:40"),
}

def _week_of(today: datetime, semester_start: datetime) -> int:
    return (today.date() - semester_start.date()).days // 7 + 1

def _in_weeks(week: int, weeks: list[list[int]]) -> bool:
    return any(a <= week <= b for a, b in weeks)

def _current_period(now: datetime) -> int:
    t = now.strftime("%H:%M")
    for p, (start, end) in PERIODS.items():
        if start <= t <= end:
            return p
    # 在一天开始上课前（早于第 1 节）算第 0 段，晚上之后算 5（今天不再有课）
    return 0 if t < "08:00" else 5

def find_next_class(timetable: dict, now: datetime, semester_start: datetime,
                    week_override: int | None = None) -> dict | None:
    """返回下一节课 {'课程','教师','地点','星期','节次段','日期','周'}；无课返回 None"""
    week = week_override if week_override is not None else _week_of(now, semester_start)
    cur = _current_period(now)
    day = now.date()
    for _ in range(8):  # 今天 + 往后最多 7 天
        wd = day.isoweekday()
        for period in range(cur + 1, 6):
            for c in timetable['课程']:
                if c['星期'] == wd and c['节次段'] == period and _in_weeks(week, c['周次']):
                    return {**c, '日期': str(day), '周': week}
        # 今天没了，从明天第 1 节开始
        day += timedelta(days=1)
        cur = 0
    return None

def classes_on(timetable: dict, date: datetime, week_override: int | None = None) -> list[dict]:
    """某天全部课程（按节次段排序）"""
    week = week_override if week_override is not None else _week_of(date, semester_start_of(timetable, date))
    wd = date.isoweekday()
    out = []
    for c in timetable['课程']:
        if c['星期'] == wd and _in_weeks(week, c['周次']):
            out.append(c)
    out.sort(key=lambda c: c['节次段'])
    return out

def semester_start_of(timetable: dict, date: datetime) -> datetime:
    """学期开学日：由插件配置提供，这里用默认映射（可被配置覆盖）"""
    from datetime import datetime as dt
    # 2025-2026-2 学期：2026-02-23（春季）；2026-2027-1 学期：2026-09-01（秋季）
    starts = {
        "2025-2026-2": "2026-02-23",
        "2026-2027-1": "2026-09-01",
    }
    s = starts.get(timetable.get('学期', ''))
    return dt.strptime(s, "%Y-%m-%d") if s else dt(date.year, 9, 1)

if __name__ == '__main__':
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    import parse_timetable
    tb = parse_timetable.parse_timetable('_fetched.xls')
    # 测试：2026-03-09（周一，第 3 周）15:00 问下节课
    test = datetime(2026, 3, 9, 15, 0)
    nxt = find_next_class(tb, test, semester_start_of(tb, test))
    if nxt:
        print(f"下节课: {nxt['课程']} | {nxt['教师']} | {nxt['地点']} | 节次段{nxt['节次段']} "
              f"{PERIODS[nxt['节次段']][0]}~{PERIODS[nxt['节次段']][1]}")
    else:
        print("无课")
    # 测试：周五 17:00 问下节课（应跨到下周）
    test2 = datetime(2026, 3, 13, 17, 0)
    nxt2 = find_next_class(tb, test2, semester_start_of(tb, test2))
    if nxt2:
        print(f"周五17点问下节课: {nxt2['课程']} | {nxt2['日期']} | 节次段{nxt2['节次段']}")
