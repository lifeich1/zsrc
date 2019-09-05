#!/usr/bin/env python3
import argparse

parser = argparse.ArgumentParser(description='CPU temperature watcher')
parser.add_argument('-hi', '--temp-hi', type=float, required=True,
                    help='enable threshold')
parser.add_argument('-hh', '--temp-night-hi', type=float, required=True,
                    help='enable threshold at night')
parser.add_argument('-lo', '--temp-lo', type=float, required=True,
                    help='disable threshold')
parser.add_argument('-n', '--nsec-wait', type=int, default=5,
                    help='time wait between detections')
parser.add_argument('-p', '--pin', type=int, default=32,
                    help='fan control gpio no. =32 (GPIO12)')
parser.add_argument('--log-temp-hi', default=48, type=float)
parser.add_argument('--log-file', default='/var/log/z/watch-temp.log')
parser.add_argument('--log-report-time-count', type=int, default=24)
parser.add_argument('--workday-wake', default='7:30')
parser.add_argument('--workday-sleep', default='22:30')
parser.add_argument('--weekend-wake', default='9:30')
parser.add_argument('--weekend-sleep', default='22:30')
parser.add_argument('--reverse-day-type-dir', default='/var/tmp/rev-day-type')
parser.add_argument('--fan-least-open', default=30, type=int)

#args = parser.parse_args()
args = None

import os
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

def is_weekend(lt=None):
    if lt is None:
        lt = time.localtime(time.time())
    fl = (lt.tm_wday >= 5)
    s = time.strftime('%Y-%m-%d')
    if os.path.exists(os.path.join(args.reverse_day_type_dir, s)):
        fl = not fl
    return fl

def is_at_night():
    lt = time.localtime(time.time())
    if is_weekend(lt):
        st, ed = args.weekend_wake, args.weekend_sleep
    else:
        st, ed = args.workday_wake, args.workday_sleep
    st = time.strptime(st, '%H:%M')
    ed = time.strptime(ed, '%H:%M')
    fo = lambda ts: (ts.tm_hour, ts.tm_min)
    st, ed, lt = list(map(fo, [st, ed, lt]))
    return lt < st or lt >= ed

def current_temp_hi():
    return args.temp_night_hi if is_at_night() else args.temp_hi

def fmt_out(T, Fs, vt=False):
    return '%11d%7.1f%6.3f%6.3f%6.3f%6.3f' % (int(time.time()) if vt else 0, T, *Fs)

def printl(s):
    with open(args.log_file, 'a') as f:
        print(s, file=f, flush=True)


class Handlers:
    # 0: active
    # 1: rest
    _dispatch = [None] * 2

    @classmethod
    def _reg_handle(cls, no):
        def reg(func):
            cls._dispatch[no] = func
            return func
        return reg


class Watcher(Handlers):
    def __init__(self):
        self.logging = False
        self.status = 0
        self.log_cnt = 0
        self.fan_open_time = time.time()
        GPIO.setmode(GPIO.BOARD)
        self.T = get_temp()
        self._log('on')
        self._pin_on(True)
        #GPIO.setup(args.pin, GPIO.OUT, initial=GPIO.LOW)

    def _pin_on(self, log=False):
        #GPIO.output(args.pin, GPIO.LOW)
        GPIO.setup(args.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        if log:
            self.fan_open_time = time.time()
            printl('>%11d fan ON; is_weekend=%d is_night=%d' % (int(time.time()), is_weekend(), is_at_night()))

    def _pin_off(self, log=False):
        #GPIO.output(args.pin, GPIO.HIGH)
        GPIO.setup(args.pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        if log:
            printl('<%11d fan OFF' % int(time.time()))

    @Handlers._reg_handle(0)
    def _handle0(self):
        self._pin_on()
        if self.T < args.temp_lo and time.time() - self.fan_open_time >= args.fan_least_open:
            self.status = 1
            self._log('exit')
            self._pin_off(True)
        else:
            self._log('in')

    @Handlers._reg_handle(1)
    def _handle1(self):
        self._pin_off()
        if self.logging:
            self._log('in')
        elif self.T >= args.log_temp_hi:
            self._log('on')
        if self.T >= current_temp_hi():
            self.status = 0
            self._pin_on(True)

    def _log(self, op):
        fs = get_cpu_freqs()
        if 'on' == op:
            s = fmt_out(self.T, fs, True)
            self.log_cnt = 1
            self.logging = True
        elif 'in' == op:
            if self.log_cnt >= args.log_report_time_count:
                self.log_cnt = 0
                fl = True
            else:
                fl = False
            s = fmt_out(self.T, fs, fl)
            self.log_cnt += 1
        elif 'exit' == op:
            s = fmt_out(self.T, fs, True)
            self.logging = False
        else:
            raise NotImplementedError()
        s = ('*' if 'on' == op else ' ') + s
        printl(s)

    def sched(self):
        self.T = get_temp()
        self._dispatch[self.status](self)


def onsignal_quit(tag=-1, fr=None):
    GPIO.cleanup()
    print('cleanup GPIO, sig', tag, file=sys.stderr, flush=True)
    exit(0)

if __name__ == '__main__':
    args = parser.parse_args()
    print('pin', args.pin, 't_hi', args.temp_hi, 't_lo', args.temp_lo, 'log:', args.log_file, file=sys.stderr, flush=True)

    import signal
    signal.signal(signal.SIGTERM, onsignal_quit)
    signal.signal(signal.SIGQUIT, onsignal_quit)

    w = Watcher()
    try:
        while True:
            w.sched()
            time.sleep(args.nsec_wait)
    except KeyboardInterrupt:
        onsignal_quit()
