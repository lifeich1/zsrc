#!/usr/bin/env python3
import argparse

parser = argparse.ArgumentParser(description='CPU temperature watcher')
parser.add_argument('-hi', '--temp-hi', type=float, required=True,
                    help='enable threshold')
parser.add_argument('-lo', '--temp-lo', type=float, required=True,
                    help='disable threshold')
parser.add_argument('-n', '--nsec-wait', type=int, default=5,
                    help='time wait between detections')
parser.add_argument('-p', '--pin', type=int, default=12,
                    help='fan control gpio no. (12)')
parser.add_argument('--log-file', default='/var/log/z/watch-temp.log')
parser.add_argument('--log-report-time-count', type=int, default=24)

args = parser.parse_args()

import time
import sys
import RPi.GPIO as GPIO

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


class Watcher:
    # 0: active
    # 1: rest
    _dispatch = [None] * 2

    def __init__(self):
        self.status = 0
        self.log_cnt = 0
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(args.pin, GPIO.OUT, initial=GPIO.LOW)

    def _pin_on(self):
        GPIO.output(args.pin, GPIO.LOW)
        printl('>%11%d fan ON' % int(time.time()))

    def _pin_off(self):
        GPIO.output(args.pin, GPIO.HIGH)
        printl('<%11%d fan OFF' % int(time.time()))

    @classmethod
    def _reg_handle(cls, no):
        def reg(func):
            cls._dispatch[no] = func
            return func
        return reg

    @Watcher._reg_handle(0)
    def _handle0(self):
        self._pin_on()
        if self.T < args.temp_lo:
            self.status = 1
            self._log('exit')
        else:
            self._log('in')

    @Watcher._reg_handle(1)
    def _handle1(self):
        self._pin_off()
        if self.T >= args.temp_hi:
            self.status = 0
            self._log('on')

    def _log(self, op):
        fs = get_cpu_freqs()
        if 'on' == op:
            s = fmt_out(t, fs, True)
            self.log_cnt = 1
        elif 'in' == op:
            if self.log_cnt >= args.log_report_time_count:
                self.log_cnt = 0
                fl = True
            else:
                fl = False
            s = fmt_out(t, fs, fl)
            self.log_cnt += 1
        elif 'exit' == op:
            s = fmt_out(t, fs, True)
        else:
            raise NotImplementedError()
        s = ('*' if 'on' == op else ' ') + s
        printl(s)

    def sched(self):
        self.T = get_temp()
        self._dispatch[self.status](self)


print('t_hi', args.temp_hi, 't_lo', args.temp_lo, 'log:', args.log_file, file=sys.stderr, flush=True)

w = Watcher()

while __name__ == '__main__':
    w.sched()

    time.sleep(args.nsec_wait)

