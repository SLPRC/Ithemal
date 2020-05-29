from os import listdir
from os.path import isfile, join
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import sys
import common_libs.utilities as ut
from tqdm import tqdm
import subprocess
import os
import re
import time
import argparse

def insert_col_values(cnx, cols, values, code_id, arch, ttable):
        
    colstr = ''
    valuestr = ''

    for j, col in enumerate(cols): 
        if j != len(cols) - 1:
            colstr += col + ', '
            valuestr += str(values[j]) + ', '
        else:
            colstr += col
            valuestr += str(values[j])
            

    sql = 'INSERT INTO ' + ttable + ' (code_id, arch, ' + colstr + ')  VALUES(' + str(code_id) + ',' + str(arch) + ',' + valuestr + ')'
    #print sql
    ut.execute_query(cnx, sql, False)
    cnx.commit()

if __name__ == '__main__':


    #command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--arch',action='store',type=int,required=True)

    parser.add_argument('--database',action='store',type=str,required=True)
    parser.add_argument('--user',action='store', type=str, required=True)
    parser.add_argument('--password',action='store', type=str, required=True)
    parser.add_argument('--port',action='store', type=int, required=True)
    parser.add_argument('--ctable',action='store',type=str, required=True)
    parser.add_argument('--ttable',action='store',type=str, required=True)
    parser.add_argument('--limit',action='store',type=int, default=None)
    parser.add_argument('--tp',action='store',type=bool,default=False)

    args = parser.parse_args(sys.argv[1:])

    cnx = ut.create_connection(database=args.database, user=args.user, password=args.password, port=args.port)

    try:    
        f = open('codeTiming.csv', 'r')
    except Exception as e:
        print(e)
        print('cannot open block timing file!\n')
        assert False

    for ln in f:

        splitted = ln.split(',')
        codeId = splitted[0]
                            
        names = ['Core_cyc', 'L1_read_misses', 'L1_write_misses', 'iCache_misses', 'Context_switches']
        columns = ['time_actual', 'l1drmisses', 'l1dwmisses', 'l1imisses', 'conswitch']

        values = []
        aval_cols = []

        for i, name in enumerate(names):
            if i+1 < len(splitted):
                values.append(splitted[i+1].rstrip())
                aval_cols.append(columns[i])
        #print aval_cols, values

        if not args.tp:
            #print('code_id=' + codeId)
            insert_col_values(cnx, aval_cols, values, codeId, args.arch, args.ttable)
                                
        #print codeId, total, success, errors, not_finished, except_errors
    f.close()
    cnx.close()
