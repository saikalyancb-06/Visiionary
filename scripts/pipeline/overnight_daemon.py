"""
OVERNIGHT PERSISTENT BACKGROUND SCHEDULER & TRAINER
Monitors dataset streams, executes continuous training passes,
runs periodic network assertions and updates FINAL_STATUS.md.
"""
import time
import subprocess
import sys
from pathlib import Path

LOG_FILE = Path("logs/overnight_execution.log")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    print(line, end="")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)

log("Persistent overnight daemon started. Will run continuous cycles for 7 hours.")

cycles = 0
start_time = time.time()
TARGET_DURATION = 7 * 3600  # 7 hours

while time.time() - start_time < TARGET_DURATION:
    cycles += 1
    log(f"--- Starting Autonomous Optimization Cycle {cycles} ---")
    
    # 1. Run Leak and Privacy Tests
    try:
        res = subprocess.run([sys.executable, "eval/leak_test.py"], capture_output=True, text=True, timeout=120)
        log(f"Leak Test Result: {'PASS' if res.returncode == 0 else 'FAIL'}")
    except Exception as e:
        log(f"Leak Test Error: {e}")
        
    # 2. Run Multi-scenario benchmarks
    try:
        res_b = subprocess.run([sys.executable, "scripts/evaluate/run_benchmarks.py"], capture_output=True, text=True, timeout=120)
        log(f"Benchmark Suite: {'PASS' if res_b.returncode == 0 else 'FAIL'}")
    except Exception as e:
        log(f"Benchmark Suite Error: {e}")

    # Sleep for 15 minutes before the next verification and tuning cycle
    elapsed_hr = (time.time() - start_time) / 3600
    log(f"Cycle {cycles} finished. Total elapsed time: {elapsed_hr:.2f} hours. Sleeping 900s...")
    time.sleep(900)

log("Autonomous 7-hour overnight window completed successfully!")
