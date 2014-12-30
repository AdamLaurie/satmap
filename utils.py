#!/usr/bin/python

#  utils.py - python extra utilities
# -*- coding: iso-8859-15 -*-
#
#  Adam Laurie <adam@algroup.co.uk> aka Major Malfunction <majormal@pirate-radio.org>
#
#  http://rfidiot.org/ 
#  http://alcrypto.co.uk
#
#  This code is copyright (c) Adam Laurie, 2010-2014 All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#

import sys

#
# local defs
#

utils_version= "1.0h"

#
# service routines
#

SPIN= 	[
	'-',
	'\\',
	'|',
	'/',
	]

Spin= 0

BS= chr(0x08)

def spinner():
	global Spin

	sys.stdout.write(SPIN[Spin % 4])
	sys.stdout.write(BS)
	sys.stdout.flush()
	Spin= Spin + 1

def scale(value, min, max, newmax):
	return float(((value - min) / float((max - min)))) * newmax
