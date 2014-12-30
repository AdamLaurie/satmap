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
import pygame
pygame.init()

infile_east= open(sys.argv[1])
infile_west= open(sys.argv[2])
lines= infile_east.read()
lines += infile_west.read()

def scale(value, min, max, newmax):
	return float(((value - min) / float((max - min)))) * newmax

# first get scales
min_x= 99999999
max_x= 0
min_y= 99999999
max_y= 0
min_strength= 99999999
max_strength= 0

for data in lines.split('\n'):
	if len(data) == 0:
		break
	splitdata= data.split(',')
	x= int(splitdata[0])
	if x < min_x:
		min_x= x
	if x > max_x:
		max_x= x
	freq= int(splitdata[1])
	if freq < min_y:
		min_y= freq
	if freq > max_y:
		max_y= freq
	strength= int(splitdata[2].strip())
	if strength < min_strength:
		min_strength= strength
	if strength > max_strength:
		max_strength= strength

height= 480
width= 640
center= width / 2
window = pygame.display.set_mode((width, height))

for data in lines.split('\n'):
	if len(data) == 0:
		break
	splitdata= data.split(',')
	x= int(splitdata[0])
	freq= float(splitdata[1])
	strength= int(splitdata[2].strip())
	strength= int(scale(strength, min_strength, max_strength, 0xffffff))
	colour= pygame.Color('#%06X' % strength)
	y= int(scale(freq, min_y, max_y, height))
	pygame.draw.line(window, colour, (center + x, height - y), (center + x, height - y))
	#print x,y, (freq - min_y), (max_y - min_y)

#new_value = ( (old_value - old_min) / (old_max - old_min) ) * (new_max - new_min) + new_min

pygame.display.flip()

while True:
	pygame.event.get()
