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

def fix_reg_names(line):
    # nasm recognizes, for instance, r14d rather than r14l
    regs = [('r%dl'%x, 'r%dd'%x) for x in range(8, 16)]
    for old, new in regs:
        line = line.replace(old, new)
    return line

def remove_unrecog_words(line):

    words = ['ptr', '<rel>']

    for word in words:
        line = line.replace(word,'')
    return line

if __name__ == '__main__':


    #command line arguments
    parser = argparse.ArgumentParser()

    parser.add_argument('--database',action='store',type=str,required=True)
    parser.add_argument('--user',action='store', type=str, required=True)
    parser.add_argument('--password',action='store', type=str, required=True)
    parser.add_argument('--port',action='store', type=int, required=True)
    parser.add_argument('--ctable',action='store',type=str, required=True)

    args = parser.parse_args(sys.argv[1:])

    cnx = ut.create_connection(database=args.database, user=args.user, password=args.password, port=args.port)
    sql = 'SELECT code_intel, code_id from ' + args.ctable
    rows = ut.execute_query(cnx, sql, True)
    print len(rows)

    try:    
        f = open('codeDump.txt', 'w')
        #write('code_id,code\n')
    except Exception as e:
        print(e)
        print('cannot create block dump file!\n')
        assert False

    for row in rows:

        if row[0] == None or row[1] == None:
            continue

        splitted = row[0].split('\n')

        written = 0
        final_bb = ''
        for i, line in enumerate(splitted):
            if line != '':
                line = remove_unrecog_words(line)
                line = fix_reg_names(line)
                final_bb += line + ';'
                written += 1

        if written > 0:
            f.write(str(row[1]) + ';' + final_bb + '\n')
        else:
		    print('enmpty code for code id%d\n', row[1])

    f.close()
    cnx.close()
