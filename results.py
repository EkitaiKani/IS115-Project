# export_results.py  -- run from the project root: python3 export_results.py
# needs openpyxl:  pip install openpyxl
import json
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

POLICIES = ["baseline", "nearest_neighbour", "two_opt", "greedy_nn_2opt"]     # add more policy folder names here
DAYS = [f"day_{i:03d}" for i in range(1, 21)]
COMPARE = ["avg_time_taken", "delivery_rate", "delivery_cost_per_parcel", "number_of_trips", "km_per_delivered_parcel"]
FONT = "Arial"

# ---- load all metrics.json files ----
rows, keys = [], []
for pol in POLICIES:
    for day in DAYS:
        path = Path("results") / pol / day / "metrics.json"
        if not path.exists():
            print(f"missing: {path}")
            continue
        m = json.loads(path.read_text(encoding="utf-8"))
        for k in m:
            if k not in keys:
                keys.append(k)
        rows.append((pol, day, m))

wb = Workbook()
head_font = Font(name=FONT, bold=True, color="FFFFFF")
head_fill = PatternFill("solid", fgColor="1F4E78")
body_font = Font(name=FONT)

def style_header(ws, row, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.font, cell.fill = head_font, head_fill
        cell.alignment = Alignment(horizontal="center", wrap_text=True)

# ---- Sheet 1: Raw (one row per policy per day) ----
raw = wb.active
raw.title = "Raw"
raw.append(["policy", "day"] + keys)
for pol, day, m in rows:
    raw.append([pol, day] + [m.get(k) for k in keys])
style_header(raw, 1, len(keys) + 2)
raw.freeze_panes = "C2"
n_raw = raw.max_row
col_of = {k: get_column_letter(i + 3) for i, k in enumerate(keys)}   # metric -> column letter

# ---- Sheet 2: Compare (days as rows; formulas pull from Raw) ----
cmp_ws = wb.create_sheet("Compare")
base, others = POLICIES[0], POLICIES[1:]
header = ["day"]
for k in COMPARE:
    header += [f"{p} {k}" for p in POLICIES] + [f"{k}: {p} - {base}" for p in others]
cmp_ws.append(header)
style_header(cmp_ws, 1, len(header))

for r, day in enumerate(DAYS, start=2):
    cmp_ws.cell(row=r, column=1, value=day)
    c = 2
    for k in COMPARE:
        L = col_of[k]
        first_pol_col = c
        for pol in POLICIES:
            cmp_ws.cell(row=r, column=c, value=(
                f'=SUMIFS(Raw!${L}$2:${L}${n_raw},Raw!$A$2:$A${n_raw},"{pol}",'
                f'Raw!$B$2:$B${n_raw},$A{r})'))
            c += 1
        for i in range(len(others)):
            a = get_column_letter(first_pol_col + 1 + i)
            b = get_column_letter(first_pol_col)
            cmp_ws.cell(row=r, column=c, value=f"={a}{r}-{b}{r}")
            c += 1

# mean and standard deviation rows under the day rows
last = len(DAYS) + 1
mean_r, sd_r = last + 2, last + 3
cmp_ws.cell(row=mean_r, column=1, value="Mean")
cmp_ws.cell(row=sd_r, column=1, value="Std dev")
for c in range(2, len(header) + 1):
    L = get_column_letter(c)
    cmp_ws.cell(row=mean_r, column=c, value=f"=AVERAGE({L}2:{L}{last})")
    cmp_ws.cell(row=sd_r, column=c, value=f"=STDEV({L}2:{L}{last})")
    for r in (mean_r, sd_r):
        cmp_ws.cell(row=r, column=c).number_format = "0.000"
for r in range(2, sd_r + 1):
    cmp_ws.cell(row=r, column=1).font = Font(name=FONT, bold=r >= mean_r)
    for c in range(2, len(header) + 1):
        cell = cmp_ws.cell(row=r, column=c)
        cell.font = Font(name=FONT, bold=r >= mean_r)
        if r < mean_r:
            cell.number_format = "0.000"
cmp_ws.freeze_panes = "B2"
cmp_ws.cell(row=sd_r + 2, column=1,
            value="Negative difference = policy is lower than baseline (good for time, cost, trips; bad for delivery_rate).")

# ---- tidy widths and fonts ----
for ws in (raw, cmp_ws):
    for i in range(1, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(i)].width = 18
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            if cell.font.name != FONT:
                cell.font = body_font

wb.save("results.xlsx")
print(f"Saved results.xlsx ({len(rows)} runs)")