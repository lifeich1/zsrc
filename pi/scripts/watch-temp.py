#!/usr/bin/env python3
import time
import sys

TEMP_FILE = '/sys/class/thermal/thermal_zone0/temp'
LOG_LV_HI = 50
LOG_LV_LO = 46
FREQ_FILE = '/sys/devices/system/cpu/cpu%d/cpufreq/scaling_cur_freq'
PERIOD = 5
LOG_FILE = '/var/log/z/watch-temp.log'

def get_temp():
    with open(TEMP_FILE, 'r') as f:
        s = f.readlines(1)[0]
    return float(s) * 0.001

def get_cpu_freqs():
    fs = []
    for i in range(4):
        with open(FREQ_FILE % i, 'r') as f:
            s = f.readlines(1)[0]
        fs.append(float(s) * 1e-6)
    return fs

def fmt_out(T, Fs, vt=False):
    return '%11d%7.1f%6.3f%6.3f%6.3f%6.3f' % (int(time.time()) if vt else 0, T, *Fs)

def printl(s):
    with open(LOG_FILE, 'a') as f:
        print(s, file=f, flush=True)


last_hi = False
print('t_hi', LOG_LV_HI, 't_lo', LOG_LV_LO, 'log:', LOG_FILE, file=sys.stderr, flush=True)

while True:
    t = get_temp()
    if ((not last_hi) and t > LOG_LV_HI) or (last_hi and t > LOG_LV_LO):
        fs = get_cpu_freqs()
        printl(fmt_out(t, fs, not last_hi))
        last_hi = True
    elif last_hi:
        # exit rec
        last_hi = False
        fs = get_cpu_freqs()
        printl(fmt_out(t, fs, vt=True))

    time.sleep(PERIOD)

