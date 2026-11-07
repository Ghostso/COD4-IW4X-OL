#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
try:
    import numpy
    print('numpy', numpy.__version__)
except Exception as exc:
    print('NO_NUMPY', repr(exc))
print('python', sys.version)
