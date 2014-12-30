#!/usr/bin/python

#  satmap.py - python tool for mapping satellite coverage
# -*- coding: iso-8859-15 -*-
#
#  Adam Laurie <adam@algroup.co.uk> aka Major Malfunction <majormal@pirate-radio.org>
#
#  http://rfidiot.org/ 
#  http://alcrypto.co.uk
#
#  This code is copyright (c) Adam Laurie, 2010, All rights reserved.
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
# this code was written as an exercise in understanding the DVB API, and
# to that end I relied heavily on other's examples... in particular:
#
# how to do ioctls in python:
#
#   http://wiki.maemo.org/Programming_FM_radio
# 
# general dvb foo:
#
#   dvbsnoop - http://dvbsnoop.sourceforge.net/
#
# dvb tuning:
#
#   dvbtune - http://sourceforge.net/projects/dvbtools/
#
# dvb api
#
#   http://www.linuxtv.org/docs/dvbapi/Contents.html
#
# linux hardware support
#
#   http://www.linuxtv.org/wiki/index.php/Main_Page
#
# streaming video (in GUI)
#
#  http://www.gstreamer.net/
#  http://gstreamer.freedesktop.org/modules/gst-python.html
#
#  a lot of the examples you'll find appear to be based on the same code, so it's
#  hard to say where it actually originated, but this seems as good a place as any:
#
#  http://pygstdocs.berlios.de/pygst-tutorial/pipeline.html
#
# gstreamer internals
#
#  http://www.flumotion.net/
#

import os
import sys
import fcntl
from ctypes import *
import errno
from dvb import *
import time

#
# local defs
#

version= "1.0i"

#
# main code starts here
#

#
# unbuffered output
#

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', UNBUFFERED)

#
# setup frontend device
#

fe= DVB_FRONTEND_INFO()
try:
	fe_fd= open(DVB_FE_Device,'wb',UNBUFFERED)
	fcntl.ioctl(fe_fd,FE_GET_INFO,fe,True)
except:
	print 'No DVB frontend device detected (%s)!' % DVB_FE_Device
	os._exit(False)

#
# open demux
#

try:
	demux_audio_fd= open(DVB_DEMUX_Device,'wb',UNBUFFERED)
	demux_video_fd= open(DVB_DEMUX_Device,'wb',UNBUFFERED)
	demux_teletext_fd= open(DVB_DEMUX_Device,'wb',UNBUFFERED)
except:
	print 'No DVB demux device detected (%s)!' % DVB_FE_Device
	os._exit(False)

#
# switch off filters
#

fcntl.ioctl(demux_audio_fd,DMX_STOP)
fcntl.ioctl(demux_video_fd,DMX_STOP)
fcntl.ioctl(demux_teletext_fd,DMX_STOP)

#
# show frontend details
#

print
print '                 Device:', DVB_FE_Device
print '                   Name:', fe.name
print '                   Type:', FE_TYPE_T[fe.type]
if not fe.type == FE_TYPE_QPSK:
	print
	print 'Wrong DVB type! Only QPSK (DVB-S) devices supported.'
	print
	os._exit(False)
print '               Min Freq:', fe.frequency_min / 1000.0, 'MHz'
print '               Max Freq:', fe.frequency_max / 1000.0, 'MHz'
print '              Freq Step:', fe.frequency_stepsize / 1000.0, 'MHz'
print '         Freq Tolerance:', fe.frequency_tolerance / 1000.0, 'MHz'
print '        Min Symbol Rate:', fe.symbol_rate_min / 1000000.0, 'MSym/s'
print '        Max Symbol Rate:', fe.symbol_rate_max / 1000000.0, 'MSym/s'
print '  Symbol Rate Tolerance:', fe.symbol_rate_tolerance, 'ppm'
print '         Notifier Delay:', fe.notifier_delay, 'ms'
print '           Capabilities:',
indent= False
for caps in sorted(FE_CAPS.keys()):
	if fe.caps & caps or fe.caps == caps:
		if indent:
			print '                        ', 
		else:
			indent= True
		print FE_CAPS[caps]
print

#
# (IO is asynch, so we need a polling mechanism)
#

fe_poll= select.poll()
fe_poll.register(fe_fd,select.POLLPRI)

#
# clear events
#

while True:
	if not get_event(fe_fd,fe_poll,100)[0]:
		break
#
# set scan range
#

polarity= 'H'
#frequency = 10714000
frequency = fe.frequency_min + LOW_OFFSET
frequency_max = fe.frequency_max + HIGH_OFFSET
#frequency =  11222000
if frequency < LOW_BAND_MIN:
	print 'Min frequency is below settable minimum! Adjusting to:',LOW_BAND_MIN
	frequency = LOW_BAND_MIN
symbol_rate= fe.symbol_rate_max / 2
#symbol_rate= 22000000
#symbol_rate= 27500000
step= fe.frequency_stepsize
if not step:
	step= 1000.0

#
# create output file for GUI
#
print 'Writing to test.txt'
try:
	outfile= open('test.txt','r+', UNBUFFERED)
	print 'found exisiting data - continuing...'
	# read 4 header lines
	for x in range(4):
		outfile.readline()
	while 42:
		try:
			position,frequency,symbol_rate,polarity,strength= outfile.readline().strip().split(',')
			frequency= int(frequency)
			symbol_rate= int(symbol_rate)
		except:
			print 'setting frequency start to', frequency
			break
except:
	outfile= open('test.txt','w', UNBUFFERED)
	outfile.write('start frequency, end frequency, step size\n')
	outfile.write('%d,%d,%d\n' % (frequency, frequency_max, step))
	outfile.write('position,frequency,symbol_rate,polarity,signal_strength\n')


# limit range for testing
#frequency= 10740440
#frequency_max= 10742462
print
print 'Scanning from %d to %d (%d MHz total), in %f MHz steps (%d samples)' % (frequency, frequency_max, (frequency_max - frequency) / 1000, step / 1000.0, ((frequency_max - frequency) / step))

#
# do scan!
#

frequency_list= []


position= 0


start_frequency= frequency
steps= 200
while True:
	ret, symbol_rate, polarity = detect_symbol_rate(fe_fd, fe_poll, frequency, polarity,symbol_rate)
	if ret:
		sys.stdout.write(polarity)
		frequency_list.append((frequency,symbol_rate,polarity))
		ret, strength= get_signal_strength(fe_fd)
		outfile.write('%d,%d,%d,%s,%d\n' % (position,frequency,symbol_rate,polarity,strength))
                #status, ber, snr = dvb_fe_status(fe_fd)
#               # display_fe_status(status, ber, snr)
	else:
		sys.stdout.write('-')
	frequency += step
	if frequency >  frequency_max:
		if steps == 0:
			break
		else:
			steps -= 1
			position += 1
			frequency= start_frequency
			print
			print 'steer'
			diseqc_drive(fe_fd, fe_poll, DISEQC_DRIVE_E, 'STEP', 1, 1)

print
print 'Done!'
print

print frequency_list
outfile.close()
