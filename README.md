# IS115 Project README
# IS115 Project: Last-Mile Delivery Dispatch

This repository contains our dispatch policies, performance monitor and results for the IS115 last-mile delivery project. This README explains how to **reproduce every result** in the `results/` folder.

- **Policies:** `baseline` (supplied), `nearest_neighbour`, `two_opt` (recommended) and `greedy_nn_2opt`
- **Data:** all 20 days, `day_001` to `day_020`

---

## 1. Requirements

- **Python 3.9 or later.** The simulator, policies and performance monitor use only the Python standard library, so nothing needs to be installed to reproduce the results.
- **Optional:** the Excel summary script `results.py` needs the `openpyxl` package: `pip install openpyxl`.
- Run **every command from the project root**, the folder that contains `data/`, `simulator/` and `solution/`.
- **Terminal:** on Windows, use **PowerShell** (the default terminal in VS Code). Every command below is given first as a **Windows PowerShell** version, followed by a **macOS / Linux / Git Bash** version.
- **Windows:** use `python` (or `py` if `python` is not recognised). On macOS / Linux, use `python3`.
- The macOS / Linux / Git Bash versions split long commands over several lines with `\`. **PowerShell does not support this**, which is why the PowerShell versions are written on one line. In Git Bash on Windows, replace `python3` with `python` if `python3` is not recognised.

Check your Python version:
```powershell
python --version
```

---

## 2. Project structure

```
project/
├── simulator/                       # Supplied simulator (unchanged)
├── data/                            # Supplied demand, distances and config (unchanged)
│   ├── demand/day_001.csv … day_020.csv
│   ├── dist.csv
│   └── config.json
├── solution/
│   ├── performance_monitor.py       # Calculates our metrics from a run's event log
│   └── policies/
│       ├── baseline.py              # Supplied FIFO policy (unchanged)
│       ├── helpers.py               # Shared helper functions used by our policies
│       ├── nearest_neighbour.py     # Policy: greedy selection + nearest-neighbour ordering
│       ├── two_opt.py               # Policy: greedy selection + 2-opt on waiting time (recommended)
│       └── greedy_nn_2opt.py        # Policy: greedy selection + grouping + nearest-neighbour + 2-opt on distance
├── results/
│   ├── baseline/day_001 … day_020/            # log.txt + metrics.json for each day
│   ├── nearest_neighbour/day_001 … day_020/
│   ├── two_opt/day_001 … day_020/
│   └── greedy_nn_2opt/day_001 … day_020/
├── results.py                       # Collects every metrics.json into results.xlsx (needs openpyxl)
├── test_order_stops.py              # Checks the stop-ordering helper on the baseline's trips
└── README.md
```

Each results folder contains:
- **`log.txt`**: the event log written by the simulator, one JSON record per line.
- **`metrics.json`**: our metrics, calculated from that log by `performance_monitor.py`.

---

## 3. Reproducing the results

Each result takes **two commands**: run the simulator to produce `log.txt`, then run the performance monitor on that log to produce `metrics.json`.

### 3.1 Baseline, one day

**Step 1: run the simulation**

**Windows PowerShell:**
```powershell
python -m simulator --policy solution.policies.baseline --data data --day day_001 --output results/baseline/day_001
```

**macOS / Linux / Git Bash:**
```bash
python3 -m simulator --policy solution.policies.baseline \
    --data data --day day_001 \
    --output results/baseline/day_001
```

This runs `solution/policies/baseline.py` on day_001 and saves the event log to `results/baseline/day_001/log.txt`. The terminal should end with `Delivered: 349`.

**Step 2: run the performance monitor**

**Windows PowerShell:**
```powershell
python -m solution.performance_monitor --data data --day day_001 --log results/baseline/day_001/log.txt
```

**macOS / Linux / Git Bash:**
```bash
python3 -m solution.performance_monitor \
    --data data --day day_001 \
    --log results/baseline/day_001/log.txt
```

This reads the log and writes `results/baseline/day_001/metrics.json`.

### 3.2 Our policies, one day

The commands are the same for every policy; only the policy name changes. The example below uses `greedy_nn_2opt`. For another policy, replace `greedy_nn_2opt` with `nearest_neighbour` or `two_opt` in **both** commands.

**Step 1: run the simulation**

**Windows PowerShell:**
```powershell
python -m simulator --policy solution.policies.greedy_nn_2opt --data data --day day_001 --output results/greedy_nn_2opt/day_001
```

**macOS / Linux / Git Bash:**
```bash
python3 -m simulator --policy solution.policies.greedy_nn_2opt \
    --data data --day day_001 \
    --output results/greedy_nn_2opt/day_001
```

**Step 2: run the performance monitor**

**Windows PowerShell:**
```powershell
python -m solution.performance_monitor --data data --day day_001 --log results/greedy_nn_2opt/day_001/log.txt
```

**macOS / Linux / Git Bash:**
```bash
python3 -m solution.performance_monitor \
    --data data --day day_001 \
    --log results/greedy_nn_2opt/day_001/log.txt
```

The simulator's last line on day_001 should be:

| Policy | Terminal shows |
|---|---|
| `nearest_neighbour` | `Delivered: 524` |
| `two_opt` | `Delivered: 539` |
| `greedy_nn_2opt` | `Delivered: 542` |

### 3.3 All 20 days for all four policies

These commands regenerate every `log.txt` and `metrics.json` in `results/`. They take about a minute. For each day, the performance monitor runs only if the simulation succeeded. If either step fails, `FAILED:` is printed with the policy and day, and the loop carries on with the remaining days.

**Windows PowerShell:**
```powershell
foreach ($policy in "baseline", "nearest_neighbour", "two_opt", "greedy_nn_2opt") {
  1..20 | ForEach-Object {
    $day = "day_{0:D3}" -f $_
    python -m simulator --policy "solution.policies.$policy" --data data --day $day --output "results/$policy/$day"
    if ($LASTEXITCODE -eq 0) {
      python -m solution.performance_monitor --data data --day $day --log "results/$policy/$day/log.txt"
    }
    if ($LASTEXITCODE -ne 0) { Write-Host "FAILED: $policy $day" -ForegroundColor Red }
  }
}
```

**macOS / Linux / Git Bash:**
```bash
for POLICY in baseline nearest_neighbour two_opt greedy_nn_2opt; do
  for i in $(seq -w 1 20); do
    day="day_0${i}"
    python3 -m simulator --policy "solution.policies.${POLICY}" \
      --data data --day "$day" \
      --output "results/${POLICY}/$day" \
    && python3 -m solution.performance_monitor \
      --data data --day "$day" \
      --log "results/${POLICY}/$day/log.txt" \
    || echo "FAILED: ${POLICY} $day"
  done
done
```

#### One policy only

To regenerate a single policy, set its name on the first line (`baseline`, `nearest_neighbour`, `two_opt` or `greedy_nn_2opt`).

**Windows PowerShell:**
```powershell
$policy = "greedy_nn_2opt"
1..20 | ForEach-Object {
  $day = "day_{0:D3}" -f $_
  python -m simulator --policy "solution.policies.$policy" --data data --day $day --output "results/$policy/$day"
  if ($LASTEXITCODE -eq 0) {
    python -m solution.performance_monitor --data data --day $day --log "results/$policy/$day/log.txt"
  }
  if ($LASTEXITCODE -ne 0) { Write-Host "FAILED: $day" -ForegroundColor Red }
}
```

**macOS / Linux / Git Bash:**
```bash
POLICY=greedy_nn_2opt
for i in $(seq -w 1 20); do
  day="day_0${i}"
  python3 -m simulator --policy "solution.policies.${POLICY}" \
    --data data --day "$day" \
    --output "results/${POLICY}/$day" \
  && python3 -m solution.performance_monitor \
    --data data --day "$day" \
    --log "results/${POLICY}/$day/log.txt" \
  || echo "FAILED: $day"
done
```

### 3.4 Re-running only the performance monitor

If `performance_monitor.py` changes but the policies do not, the logs stay the same, so only the monitor needs to run again.

**Windows PowerShell:**
```powershell
foreach ($policy in "baseline", "nearest_neighbour", "two_opt", "greedy_nn_2opt") {
  1..20 | ForEach-Object {
    $day = "day_{0:D3}" -f $_
    python -m solution.performance_monitor --data data --day $day --log "results/$policy/$day/log.txt"
    if ($LASTEXITCODE -ne 0) { Write-Host "FAILED: $policy $day" -ForegroundColor Red }
  }
}
```

**macOS / Linux / Git Bash:**
```bash
for POLICY in baseline nearest_neighbour two_opt greedy_nn_2opt; do
  for i in $(seq -w 1 20); do
    day="day_0${i}"
    python3 -m solution.performance_monitor \
      --data data --day "$day" \
      --log "results/${POLICY}/$day/log.txt" \
    || echo "FAILED: ${POLICY} $day"
  done
done
```

### 3.5 Checking your results match ours

The simulator is **deterministic**: the same code and data always produce the same log.

**day_001** should show these values in each policy's `metrics.json`:

| Value in `metrics.json` | baseline | nearest_neighbour | two_opt | greedy_nn_2opt |
|---|---:|---:|---:|---:|
| `avg_time_taken` | 366.448 | 266.978 | 262.536 | 270.900 |
| `km_per_delivered_parcel` | 15.024 | 9.165 | 8.938 | 8.864 |
| `delivered_count` | 349 | 524 | 539 | 542 |
| `number_of_trips` | 20 | 29 | 29 | 30 |

To view every value for one day (works in PowerShell and bash):
```powershell
cat results/greedy_nn_2opt/day_001/metrics.json
```

**20-day averages** for each policy (**Windows PowerShell**):
```powershell
foreach ($p in "baseline", "nearest_neighbour", "two_opt", "greedy_nn_2opt") { $m = 1..20 | ForEach-Object { Get-Content ("results/$p/day_{0:D3}/metrics.json" -f $_) | ConvertFrom-Json }; "{0,-18} time {1,6:N1}  km/parcel {2,5:N2}  delivered {3,5:N1}  trips {4,4:N1}" -f $p, ($m | Measure-Object avg_time_taken -Average).Average, ($m | Measure-Object km_per_delivered_parcel -Average).Average, ($m | Measure-Object delivered_count -Average).Average, ($m | Measure-Object number_of_trips -Average).Average }
```

Expected (the last digit may differ by 1 because of rounding):

| Policy | avg_time_taken | km_per_delivered_parcel | delivered_count | number_of_trips |
|---|---:|---:|---:|---:|
| baseline | 372.0 | 16.33 | 321.1 | 20.7 |
| nearest_neighbour | 291.1 | 10.74 | 449.4 | 27.3 |
| two_opt | 288.0 | 10.64 | 456.0 | 27.4 |
| greedy_nn_2opt | 290.8 | 9.92 | 482.2 | 29.4 |

**Day by day, baseline vs one policy** (**Windows PowerShell**). Change `greedy_nn_2opt` in `$p = ...` to compare another policy:
```powershell
$p = "greedy_nn_2opt"; 1..20 | ForEach-Object { $d = "day_{0:D3}" -f $_; $b = Get-Content "results/baseline/$d/metrics.json" | ConvertFrom-Json; $h = Get-Content "results/$p/$d/metrics.json" | ConvertFrom-Json; "{0}  time {1,6:N1} -> {2,6:N1}  km/parcel {3,5:N2} -> {4,5:N2}  delivered {5,3} -> {6,3}  trips {7,2} -> {8,2}" -f $d, $b.avg_time_taken, $h.avg_time_taken, $b.km_per_delivered_parcel, $h.km_per_delivered_parcel, $b.delivered_count, $h.delivered_count, $b.number_of_trips, $h.number_of_trips }
```

For `greedy_nn_2opt`, the first line should read:
```
day_001  time  366.4 ->  270.9  km/parcel 15.02 ->  8.86  delivered 349 -> 542  trips 20 -> 30
```
If the lines are cut off, widen or maximise the terminal panel.

### 3.6 Stop-ordering check (optional)

`test_order_stops.py` takes the baseline's own trips for one day, reorders each one with `order_stops`, and reports how much shorter they become. It needs that day's baseline log first (Section 3.1).

```powershell
python test_order_stops.py day_001       # Windows PowerShell
python3 test_order_stops.py day_001      # macOS / Linux / Git Bash
```

Expected output:
```
Baseline trips, original order:   5243.3 km
Same trips after order_stops:    3680.8 km  (29.8% shorter)
```

---

## 4. What the performance monitor measures

`solution/performance_monitor.py` reads one run's `log.txt` together with that day's data files, and writes `metrics.json`. Lower is better for both main metrics.

### Main metrics

| Key | Meaning |
|---|---|
| `avg_time_taken` | **Main metric.** Average minutes from a parcel arriving at the hub to being delivered, over **all** parcels that day. Undelivered parcels count as delivered at 18:00, so skipping parcels cannot improve the score. |
| `km_per_delivered_parcel` | **Second metric.** Total km driven by the fleet ÷ parcels delivered. |

### Supporting values

| Key | Meaning |
|---|---|
| `number_of_trips` | Trips that left the hub |
| `total_parcels` | Parcels in that day's demand file |
| `delivered_count`, `delivery_rate` | Parcels delivered, and the share of all parcels delivered |
| `on_time_count`, `late_count`, `early_count` | Deliveries inside, after or before each parcel's preferred window |
| `on_time_rate` | On-time deliveries ÷ **all** parcels |
| `avg_lateness` | Average minutes past the window end, over late parcels only |
| `total_km` | Total distance driven by the fleet |
| `energy_cost`, `driver_cost`, `total_cost` | Cost of the day in SGD (see Section 7) |
| `delivery_cost_per_parcel` | `total_cost` ÷ parcels delivered, in SGD |

---

## 5. Policies

All three of our policies choose parcels the same way as the baseline (`greedy_route`: oldest parcels first, each added if the trip still follows the rules). They differ only in **how they order the stops**. Each one then double-checks the new order: it is used only if it passes `is_feasible` and its `route_cost` is no worse than the original order; otherwise the original order is kept.

| Policy | How it orders the stops | Optimises |
|---|---|---|
| `baseline` | Arrival order (no reordering) | — |
| `nearest_neighbour` | `nearest_neighbour_parcels`: from the hub, always go to the parcel whose stop is closest | Distance (greedy) |
| `two_opt` **(recommended)** | `two_opt_parcels`: starting from arrival order, flip sections of the route and keep any flip that lowers total waiting time (`route_cost`) | Waiting time (local search) |
| `greedy_nn_2opt` | `order_stops`: group parcels by place, order the places with `nearest_neighbour`, then improve with `two_opt` | Distance (greedy + local search) |

`two_opt` and `greedy_nn_2opt` leave trips with fewer than 3 parcels unchanged.

---

## 6. Helper functions (`solution/policies/helpers.py`)

| Function | Purpose |
|---|---|
| `available_parcels` | Lists parcels still waiting at the hub, not yet assigned to a vehicle or delivered. |
| `route_load` | Adds up the size of all parcels on a trip, to check the vehicle isn't overloaded (max load = 30). |
| `route_distance` | Works out how far a trip is: hub → each stop → back to the hub. |
| `arrival_times` | Works out what time the vehicle reaches each parcel's stop (1 km = 1 minute). |
| `is_feasible` | Checks a trip follows all the rules: no parcel listed twice, load ≤ 30 units, trip distance ≤ 320 km, and back at the hub by 18:00. |
| `route_cost` | Scores a trip by how long its parcels wait in total, from arriving at the hub to being delivered. A lower score means the trip is better. It uses the same formula as the main metric (i.e. `avg_time_taken`). |
| `tour_length` | Similar to `route_distance`, but works with a list of places instead of parcels. |
| `nearest_neighbour` | Puts the places in a quick, sensible order: from the hub, always drive to the closest place not yet visited. |
| `nearest_neighbour_parcels` | Same idea as `nearest_neighbour`, but orders the parcels directly: always go next to the parcel whose stop is closest. |
| `two_opt` | Improves the order from `nearest_neighbour`: tries flipping part of the route backwards and keeps any change that makes the trip shorter, until nothing helps. |
| `two_opt_parcels` | Same idea as `two_opt`, but works on parcels and keeps a flip only if the trip is still feasible and its total waiting time (`route_cost`) goes down. |
| `order_stops` | Reorders a trip so the vehicle drives less. It first groups parcels going to the same place, then finds a short order to visit those places (using `nearest_neighbour`, then improving it with `two_opt`), and finally returns the parcels in that order. |
| `greedy_route` | Picks which parcels go on a trip: goes through waiting parcels from oldest to newest and adds each one if the trip still follows the rules. |

---

## 7. Assumptions

- **Cost values** in `performance_monitor.py` are illustrative assumptions, since the data contains no prices:
  - `ENERGY_COST_PER_KM = 0.10` (SGD)
  - `DRIVER_COST_PER_HOUR = 20.0` (SGD)
  - `SPEED_KMH = 60.0` and `LOADING_MINUTES = 30.0` come from the IS115 Project Brief (Operating Model).

  To try different prices, change these lines and re-run only the performance monitor (Section 3.4).
- **Undelivered parcels** count as delivered at 18:00 in `avg_time_taken`.
- The supplied `simulator/`, `data/`, `baseline.py` and all `__init__.py` files are **unchanged**.

---

## 8. Troubleshooting

| Error | Fix |
|---|---|
| `No module named simulator` or `No module named solution` | You are not in the project root. `cd` into the folder that contains `simulator/` and `solution/`. |
| `No such file or directory: results/.../log.txt` | Run the simulator for that policy and day first (Step 1), then the monitor. |
| `python3` is not recognised (Windows) | Use `python` or `py` instead. |
| `ModuleNotFoundError: No module named 'openpyxl'` | Run `pip install openpyxl`, then `python results.py` again. |
| `PermissionError` when running `results.py` | `results.xlsx` is open in Excel. Close it and run the script again. |
| The bash `for` loop fails in PowerShell | Use the PowerShell version of the command. |
| `FAILED: two_opt day_001` (or another policy and day) | That policy crashed on that day. Run its single-day command (Section 3.2) to see the full error. |
| `Missing expression after unary operator '--'` or `unrecognized arguments: \` | A multi-line bash command (ending lines with `\`) was pasted into PowerShell. Use the one-line PowerShell version. |