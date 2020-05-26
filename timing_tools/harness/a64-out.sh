#!/bin/bash

make clean >/dev/null
make NDEBUG=1 >/dev/null

sudo ./test
