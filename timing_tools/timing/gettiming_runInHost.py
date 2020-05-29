from os import listdir
from os.path import isfile, join
import sys
import subprocess
import os
import re
import time
import argparse


def wait_timeout(proc, seconds):
    """Wait for a process to finish, or raise exception after timeout"""
    start = time.time()
    end = start + seconds
    interval = min(seconds / 1000.0, .25)

    while True:
        result = proc.poll()
        if result is not None:
            return result
        if time.time() >= end:
            proc.kill()
            return None
        time.sleep(interval)

def insert_col_values(f_out, values, code_id):
        
    valuestr = ''

    for j, val in enumerate(values): 
        if j != len(values) - 1:
            valuestr += str(val) + ','
        else:
            valuestr += str(val)
            
    f_out.write(code_id + ',' + valuestr + '\n')


class PMCValue:

    def __init__(self, value):
        self.value = value
        self.count = 1

class PMC:

    def __init__(self, name):
        self.name = name
        self.values = []

        self.mod_values = []
        self.mode = None
        self.percentage = 5

    def add_value(self, nvalue):

        self.values.append(nvalue)

        added = False
        for val in self.mod_values:
            if val.value == 0:
                val.value = 1e-3
            if (abs(val.value - nvalue) * 100.0 / val.value)  < self.percentage:
                val.value = (val.value * val.count + nvalue) / (val.count + 1)
                val.count += 1
                added = True
                break

        if not added:
            val = PMCValue(nvalue)
            self.mod_values.append(val)
        
    def set_mode(self):

        max_count = 0

        for val in self.mod_values:
            if val.count > max_count:
                self.mode = val.value
                max_count = val.count

class PMCCounters:

    def __init__(self,line):
        names = line.split()
        #print names
        self.counters = list()
        for name in names:
            self.counters.append(PMC(name))

    def add_to_counters(self, line):
        values = line.split()
        #print values

        if len(values) != len(self.counters):
            return

        for i, value in enumerate(values):
            self.counters[i].add_value(int(value))

    def set_modes(self):

        for counter in self.counters:
            counter.set_mode()

    def get_value(self, name):

        for counter in self.counters:
            if name == counter.name:
                return counter.values
        return None

    def get_mode(self, name):

        for counter in self.counters:
            if name == counter.name:
                return counter.mode
        return None

def check_error(line):

    errors = ['error','fault']
    warnings = ['warning']

    for error in errors:
        for warning in warnings:
            if error in line and not warning in line:
                return True
    return False

if __name__ == '__main__':

    #command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--tp',action='store',type=bool,default=False)

    args = parser.parse_args(sys.argv[1:])

    try:    
        f_in = open('codeDump.txt', 'r')
    except Exception as e:
        print(e)
        print('cannot open block dump file!\n')
        assert False

    try:    
        f_out = open('codeTiming.csv', 'w')
        #write('code_id,timing\n')
    except Exception as e:
        print(e)
        print('cannot create block timing file!\n')
        assert False

    harness_dir = os.getcwd() + '/../timing_tools/harness'
    os.chdir(harness_dir)

    total = 0
    errors = 0
    except_errors = 0
    success = 0
    not_finished = 0

    total_time = 0.0
    total_bbs = 0

    # do a dry run to figure out measurement overhead
    with open('bb.nasm', 'w') as f:
      f.close()
    proc = subprocess.Popen('./a64-out.sh', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = wait_timeout(proc, 10)
    startHeading = False
    startTimes = False
    counters = None
    for i, line in enumerate(iter(proc.stdout.readline, '')):
        if 'Clock' in line and startTimes == False and startHeading == False: #still didn't start collecting the actual timing data
            startHeading = True
        if startHeading == True:
            counters = PMCCounters(line)
            startTimes = True
            startHeading = False
        elif startTimes == True:
            counters.add_to_counters(line)
    assert counters is not None
    counters.set_modes()
    overhead = counters.get_mode('Core_cyc')
    print 'OVERHEAD =', overhead
    
    for ln in f_in:

        splitted = ln.split(';')
        codeId = splitted[0]

        written = 0
        final_bb = []
        for i, line in enumerate(splitted):
            if i > 0 and line != '' and line != '\n':
                final_bb.append(line + '\n')
                written += 1

        if written > 0:
            total += 1
            with open('bb.nasm','w+') as f:
                f.writelines(final_bb)
            proc = subprocess.Popen('./a64-out.sh', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            start_time = time.time()
            result = wait_timeout(proc, 10)
            end_time = time.time()

            if result != None:
                #print final_bb
                try:
                    error_lines = False
                    for line in iter(proc.stderr.readline, ''):
                        if check_error(line):
                            print 'error ' + line
                            error_lines = True
                            break

                    if error_lines == False:
                        startHeading = False
                        startTimes = False
                        counters = None
                        for i, line in enumerate(iter(proc.stdout.readline, '')):
                            #print line
                            if 'Clock' in line and startTimes == False and startHeading == False: #still didn't start collecting the actual timing data
                                startHeading = True
                            if startHeading == True:
                                #print 'headings ' + line
                                counters = PMCCounters(line)
                                startTimes = True
                                startHeading = False
                            elif startTimes == True:
                                #print 'values ' + line
                                counters.add_to_counters(line)
                        if counters != None:
                            counters.set_modes()
                            
                            names = ['Core_cyc', 'L1_read_misses', 'L1_write_misses', 'iCache_misses', 'Context_switches']
                            columns = ['time_actual', 'l1drmisses', 'l1dwmisses', 'l1imisses', 'conswitch']

                            values = []
                            aval_cols = []

                            for i, name in enumerate(names):
                                vs = counters.get_mode(name)
                                if vs != None:
                                    values.append(vs)
                                    aval_cols.append(columns[i])
                                    if name == 'Core_cyc':
                                        values[-1] -= overhead
                            #print values

                            if not args.tp:
                                #print('code_id ' + codeId)
                                insert_col_values(f_out, values, codeId)
                                    
                            total_time += end_time - start_time
                            total_bbs += 1
                            #print float(total_bbs)/total_time
                            success += 1
                        else:
                            values = [-1,0,0,0,0]
                            insert_col_values(f_out, values, codeId)
                            print('counters are None, code id=', codeId)
                            for line in final_bb:
                                print line[:-1]
                    else:
                        values = [-1,0,0,0,0]
                        insert_col_values(f_out, values, codeId)
                        print('Program output error, code id=', codeId)
                        for line in final_bb:
                            print line[:-1]
                        errors += 1
                except Exception as e:
                    print e
                    print 'exception occurred'
                    except_errors += 1   
                    print('code_id=' + codeId)     
            else:
                values = [-1,0,0,0,0]
                insert_col_values(f_out, values, codeId)
                print 'error program not completed '
                print('code id is' + codeId)
                for line in final_bb:
                    print line[:-1]
                not_finished += 1
        else:
		    print('enmpty code for code id=' + codeId)

        #print str(row[1]), total, success, errors, not_finished, except_errors

    f_in.close()
    f_out.close()
