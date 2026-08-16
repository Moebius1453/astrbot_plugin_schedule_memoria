import io
import re
import pandas as pd

# 周次解析：把 "2-16" / "2-6,9-17" / "2,6,8" / "17" 统一成区间列表 [[2,16]]
def parse_weeks(s: str) -> list[list[int]]:
    out = []
    for part in s.split(','):
        part = part.strip().replace('周', '')
        if '-' in part:
            a, b = part.split('-', 1)
            out.append([int(a), int(b)])
        else:
            out.append([int(part), int(part)])
    return out

# 解析单个课表格子（多行文本：课程名行 + 教师;周次;地点 行，可多组）
def parse_cell(cell: str) -> list[dict]:
    lines = [l.strip() for l in cell.split('\n') if l.strip()]
    courses = []
    name = None
    for line in lines:
        if ';' in line:
            parts = [p.strip() for p in line.split(';')]
            if name and len(parts) >= 3:
                courses.append({
                    '课程': name,
                    '教师': parts[0],
                    '周次': parse_weeks(parts[1]),
                    '地点': ';'.join(parts[2:]),
                })
            name = None
        else:
            name = line
    return courses

# 主解析：xls → 结构化 dict
def parse_timetable(path: str) -> dict:
    df = pd.read_excel(path, header=None)
    meta = str(df.iat[1, 0])
    m = re.search(r'学年学期：(\S+)', meta)
    semester = m.group(1) if m else ''
    m2 = re.search(r'武夷学院\s*(\S+)', str(df.iat[0, 0]))
    name = m2.group(1) if m2 else ''

    period_map = {'第一二节': 1, '第三四节': 2, '第五六节': 3, '第七八节': 4, '第九十节': 5}
    courses = []
    for r in range(3, 8):
        period_info = str(df.iat[r, 0])
        period = next((v for k, v in period_map.items() if k in period_info), 0)
        for c in range(1, 8):
            v = df.iat[r, c]
            if pd.isna(v):
                continue
            for course in parse_cell(str(v)):
                course['星期'] = c
                course['节次段'] = period
                courses.append(course)
    return {'学期': semester, '姓名': name, '课程': courses}


def parse_timetable_from_bytes(data: bytes) -> dict:
    return parse_timetable(io.BytesIO(data))

if __name__ == '__main__':
    import json, sys
    data = parse_timetable(sys.argv[1] if len(sys.argv) > 1 else '_fetched.xls')
    print(json.dumps(data, ensure_ascii=False, indent=1)[:2000])
    print(f'\n--- 共 {len(data["课程"])} 门课程记录 ---')
