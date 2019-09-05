#!/usr/bin/env python3
import argparse

parser = argparse.ArgumentParser(description='CPU temperature watcher')
parser.add_argument('-hi', '--temp-hi', type=float, required=True,
                    help='enable threshold')
parser.add_argument('-lo', '--temp-lo', type=float, required=True,
                    help='disable threshold')
parser.add_argument('-n', '--nsec-wait', type=int, default=5,
                    help='time wait between detections')
parser.add_argument('--log-file', default='/var/log/z/watch-temp.log')
parser.add_argument('--log-report-time-count', type=int, default=24)

args = parser.parse_args()

import time
import sys

TEMP_FILE = '/sys/class/thermal/thermal_zone0/temp'
FREQ_FILE = '/sys/devices/system/cpu/cpu%d/cpufreq/scaling_cur_freq'

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
    with open(args.log_file, 'a') as f:
        print(s, file=f, flush=True)


last_hi = False
log_hi_cnt = 0
print('t_hi', args.temp_hi, 't_lo', args.temp_lo, 'log:', args.log_file, file=sys.stderr, flush=True)

while True:
    t = get_temp()
    if ((not last_hi) and t > args.temp_hi) or (last_hi and t > args.temp_lo):
        fs = get_cpu_freqs()
        printl((' ' if last_hi else '+') + fmt_out(t, fs, (not last_hi) or log_hi_cnt > args.log_report_time_count))
        last_hi = True
        if log_hi_cnt > args.log_report_time_count:
            log_hi_cnt = 0
        log_hi_cnt += 1
    elif last_hi:
        # exit rec
        last_hi = False
        log_hi_cnt = 0
        fs = get_cpu_freqs()
        printl(fmt_out(t, fs, vt=True))

    time.sleep(args.nsec_wait)

