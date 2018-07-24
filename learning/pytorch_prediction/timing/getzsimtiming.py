from os import listdir
from os.path import isfile, join
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import sys
sys.path.append('..')
import common.utilities as ut
from tqdm import tqdm
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


class PMCValue:
    
    def __init__(self, value):
        self.value = value
        self.count = 1

class PMC:

    def __init__(self, name):
        self.name = name
        self.values = []
        self.mode = None
        self.percentage = 10

    def add_value(self, nvalue):

        added = False
        for val in self.values:
            if val.value == 0:
                val.value = 1e-3
            if (abs(val.value - nvalue) * 100.0 / val.value)  < self.percentage:
                val.value = (val.value * val.count + nvalue) / (val.count + 1)
                val.count += 1
                added = True
                break

        if not added:
            val = PMCValue(nvalue)
            self.values.append(val)

    def set_mode(self):
        
        max_count = 0

        for val in self.values:
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
                return counter.mode
        return None


def insert_time_value(cnx,code_id, time, arch):

    sql = 'INSERT INTO times (code_id, arch, kind, time) VALUES(' + str(code_id) + ',' + str(arch) + ',\'llvm\',' + str(time) + ')'
    ut.execute_query(cnx, sql, False)
    cnx.commit()


def check_error(line):
    
    errors = ['error','fault']
    
    for error in errors:
        if error in line:
            return True
    return False

if __name__ == '__main__':

    
    #command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--arch',action='store',type=int,required=True)
    parser.add_argument('--database',action='store',type=str)
    parser.add_argument('--input',action='store',type=str)
    parser.add_argument('--output',action='store',type=str)
    args = parser.parse_args(sys.argv[1:])


    assert (args.database != None) or (args.input != None and args.output != None)
    if args.database != None:
        mode = 1
    else:
        mode = 2


    if mode == 1:
        cnx = ut.create_connection(args.database)
        sql = 'SELECT code_att, code_id from code'
        rows = ut.execute_query(cnx, sql, True)
        print len(rows)
    elif mode == 2:
        rows = torch.load(args.input)

    os.chdir('/data/scratch/charithm/projects/cmodel/zsim/misc/hooks')

    lines = []
    start_line = -1
    with open('test.s','r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            rep = re.search('.*\.rept.*', line)
            if rep != None:
                start_line = i
                break
    
    print start_line

    total = 0
    errors = 0
    except_errors = 0
    success = 0
    not_finished = 0



    for row in rows:
    
        if row[0] == None:
            continue

        splitted = row[0].split('\n')
        write_lines = [line for line in lines]
        
        written = 0
        final_bb = []
        for i, line in enumerate(splitted):
            if line != '':
                final_bb.append(line + '\n')
                write_lines.insert(start_line + 1 + i, line + '\n')
                written += 1

        #written = 1
        if written > 0:
            total += 1
            with open('out.s','w+') as f:
                f.writelines(write_lines)
            proc = subprocess.Popen(['gcc','-o','test_c','out.s'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = wait_timeout(proc, 10)

            error_comp = False
        
            if result != None:
                
                try:
                    for line in iter(proc.stderr.readline, ''):
                        print line
                        if check_error(line):
                            error_comp = True
                            break
                    for line in iter(proc.stdout.readline, ''):
                        print line
                        if check_error(line):
                            error_comp = True
                            break
                except:
                    error_comp = True

            else:
                error_comp = True

            if error_comp:
                errors += 1
                continue

            print 'comp succesful'

            proc = subprocess.Popen(['../../build/opt/zsim','../../tests/arch.cfg'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = wait_timeout(proc, 10)

            
            if result != None:
                
                
                error_lines = False
                for line in iter(proc.stderr.readline, ''):
                    print line
                    if check_error(line):
                        error_lines = True
                        break
 
                if error_lines == False:
                    success += 1
                    with open('zsim.out','r') as f1:
                        lines1 = f1.readlines()
                        for line in lines1:
                            found = re.search('.*cycles: ([0-9]+) .*',line)
                            if found:
                                print found.group(0)
                                cycles = int(found.group(1))
                                if cycles != 0:
                                    print cycles
                                    break
                                    #insert_time_value(cnx, row[1], cycles, args.arch) 
                else:
                    for line in final_bb:
                        print line[:-1]
                    errors += 1

            else:
                print 'error not completed'
                not_finished += 1
        if total % 100000 == 0:
            print total, success, errors, not_finished, except_errors
    
    cnx.close()
