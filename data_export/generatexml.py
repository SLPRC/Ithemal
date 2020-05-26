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

def insert_col_xml(cnx, code_id, xml, ttable):
    
    sql = 'UPDATE ' + ttable + ' SET code_xml = ' + '\''  + xml + '\'' + ' WHERE code_id = ' + str(code_id)
    #print sql
    ut.execute_query(cnx, sql, False)
    cnx.commit()

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
    sql = 'SELECT code_id, code_raw from ' + args.ctable
    rows = ut.execute_query(cnx, sql, True)
    #print len(rows)
    _TOKENIZER = os.path.join(os.environ['ITHEMAL_HOME'], 'data_collection', 'build', 'bin', 'tokenizer')
    except_errors = 0

    for row in rows:
        if row[0] == None or row[1] == None:
            continue 

        try:
            xml = subprocess.check_output([_TOKENIZER, row[1], '--token'])
            insert_col_xml(cnx, row[0], xml, args.ctable)
            
        except Exception as e:
            print e
            print 'exception occurred'
            except_errors += 1
   
    cnx.close()
