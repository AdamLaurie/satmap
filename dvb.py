#!/usr/bin/python
#  dvb.py - python wrapper for dvb api
# -*- coding: iso-8859-15 -*-
#
#  Adam Laurie <adam@algroup.co.uk> aka Major Malfunction <majormal@pirate-radio.org>
#
#  http://rfidiot.org/ 
#  http://alcrypto.co.uk
#
#  This code is copyright (c) Adam Laurie, 2010, 2011, All rights reserved.
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
# steering / diseqc
#
# diseqc specifications
#
#  http://www.eutelsat.com/satellites/pdf/Diseqc/Reference%20docs/bus_spec.pdf
#  http://www.eutelsat.com/satellites/pdf/Diseqc/associated%20docs/positioner_appli_notice.pdf
#
# diseqc example program - xdipo
#  
#  http://panteltje.com/panteltje/satellite/ 
#
#  ported sections of xdipo are originally copyright Jan Panteltje 2005 and later
#
# *** note on Diseqc support...
#
#    If you get timeout errors trying to send diseqc commands, your DVB card may not
#    loading it's firmware properly. Check dmesg for warnings...
#
#    This code has only been tested on diseqc 1.2 capable systems, so everything is done 'blind' with
#    no status returned from the positioner.

import os
#import sys
import fcntl
from ctypes import *
import select
import struct
import errno
from utils import *
import time

#
# local defs
#

pydvb_version= "1.0b"

# default adapter
DVB_Adapter=	0

#
# macros for ioctl commands
#

_IOC_NRBITS   = 8
_IOC_TYPEBITS = 8
_IOC_SIZEBITS = 14
_IOC_DIRBITS  = 2

_IOC_NRSHIFT   = 0
_IOC_TYPESHIFT = _IOC_NRSHIFT + _IOC_NRBITS
_IOC_SIZESHIFT = _IOC_TYPESHIFT + _IOC_TYPEBITS
_IOC_DIRSHIFT  = _IOC_SIZESHIFT + _IOC_SIZEBITS

_IOC_WRITE = 1
_IOC_READ  = 2

_IO = lambda t,nr: (ord(t) << _IOC_TYPESHIFT) | (nr << _IOC_NRSHIFT)
_IOC = lambda d,t,nr,size: (d << _IOC_DIRSHIFT) | (ord(t) << _IOC_TYPESHIFT) | \
    (nr << _IOC_NRSHIFT) | (size << _IOC_SIZESHIFT)
_IOW  = lambda t,nr,size: _IOC(_IOC_WRITE, t, nr, size)
_IOR  = lambda t,nr,size: _IOC(_IOC_READ, t, nr, size)
_IOWR = lambda t,nr,size: _IOC(_IOC_READ | _IOC_WRITE, t, nr, size)

#
# DVB structures & defs (from /usr/include/linux/dvb/*)
#

FE_TYPE_QPSK = 0x00
FE_TYPE_QAM = 0x01
FE_TYPE_OFDM = 0x02
FE_TYPE_VSB = 0x03

FE_TYPE_T = {
	FE_TYPE_QPSK:'QPSK (DVB-S)',
	FE_TYPE_QAM:'QAM (DVB-C)',
	FE_TYPE_OFDM:'OFDM (DVB-T)',
	FE_TYPE_VSB:'VSB/QAM (ATSC)'
	}

FE_IS_STUPID = 0x0
FE_CAN_INVERSION_AUTO = 0x1
FE_CAN_FEC_1_2 = 0x2
FE_CAN_FEC_2_3 = 0x4
FE_CAN_FEC_3_4 = 0x8
FE_CAN_FEC_4_5 = 0x10
FE_CAN_FEC_5_6 = 0x20
FE_CAN_FEC_6_7 = 0x40
FE_CAN_FEC_7_8 = 0x80
FE_CAN_FEC_8_9 = 0x100
FE_CAN_FEC_AUTO = 0x200
FE_CAN_QPSK = 0x400
FE_CAN_QAM_16 = 0x800
FE_CAN_QAM_32 = 0x1000
FE_CAN_QAM_64 = 0x2000
FE_CAN_QAM_128 = 0x4000
FE_CAN_QAM_256 = 0x8000
FE_CAN_QAM_AUTO = 0x10000
FE_CAN_TRANSMISSION_MODE_AUTO = 0x20000
FE_CAN_BANDWIDTH_AUTO = 0x40000
FE_CAN_GUARD_INTERVAL_AUTO = 0x80000
FE_CAN_HIERARCHY_AUTO = 0x100000
FE_CAN_8VSB = 0x200000
FE_CAN_16VSB = 0x400000
FE_HAS_EXTENDED_CAPS = 0x800000
FE_CAN_2G_MODULATION = 0x10000000
FE_NEEDS_BENDING = 0x20000000
FE_CAN_RECOVER = 0x40000000
FE_CAN_MUTE_TS = 0x80000000

FE_CAPS = { 
	FE_IS_STUPID:'Stupid FE',
	FE_CAN_INVERSION_AUTO:'Auto inversion',
	FE_CAN_FEC_1_2:'FEC 1/2',
        FE_CAN_FEC_2_3:'FEC 2/3',
        FE_CAN_FEC_3_4:'FEC 3/4',
        FE_CAN_FEC_4_5:'FEC 4/5',
        FE_CAN_FEC_5_6:'FEC 5/6',
        FE_CAN_FEC_6_7:'FEC 6/7',
        FE_CAN_FEC_7_8:'FEC 7/8',
        FE_CAN_FEC_8_9:'FEC 8/9',
        FE_CAN_FEC_AUTO:'Auto FEC',
        FE_CAN_QPSK:'QPSK',
       	FE_CAN_QAM_16:'QAM 16',
        FE_CAN_QAM_32:'QAM 32',
        FE_CAN_QAM_64:'QAM 64',
        FE_CAN_QAM_128:'QAM 128',
        FE_CAN_QAM_256:'QAM 256',
        FE_CAN_QAM_AUTO:'Auto QAM',
        FE_CAN_TRANSMISSION_MODE_AUTO:'Auto transmission',
        FE_CAN_BANDWIDTH_AUTO:'Auto bandwidth',
        FE_CAN_GUARD_INTERVAL_AUTO:'Auto guard interval',
        FE_CAN_HIERARCHY_AUTO:'Auto hierarchy',
        FE_CAN_8VSB:'8vSB',
        FE_CAN_16VSB:'16vSB',
        FE_HAS_EXTENDED_CAPS:'Extended capabilities',
        FE_CAN_2G_MODULATION:'2G modulation',
        FE_NEEDS_BENDING:'Needs frequency bending (no longer supported)',
        FE_CAN_RECOVER:'Can recover from cable unplug',
        FE_CAN_MUTE_TS:'Can stop spurious TS data output'
	}

FE_NO_SIGNAL = 0x00
FE_HAS_SIGNAL = 0x01  # /* found something above the noise level */
FE_HAS_CARRIER = 0x02 # /* found a DVB signal  */
FE_HAS_VITERBI = 0x04 # /* FEC is stable  */
FE_HAS_SYNC = 0x08    # /* found sync bytes  */
FE_HAS_LOCK = 0x10    # /* everything's working... */
FE_TIMEDOUT = 0x20    # /* no lock within the last ~2 seconds */
FE_REINIT = 0x40      # /* frontend was reinitialized  */

FE_STATUS= {
	FE_NO_SIGNAL:'No signal - cable unplugged?',
	FE_HAS_SIGNAL:'Signal detected',
	FE_HAS_CARRIER:'Carrier detected',
	FE_HAS_VITERBI:'FEC is stable (VITERBI)',
	FE_HAS_SYNC:'Found sync bytes',
	FE_HAS_LOCK:'Signal locked',
	FE_TIMEDOUT:'No lock in last ~2 seconds',
	FE_REINIT:'Frontend re-initialised'
	}

FEC_NONE = 0x00
FEC_1_2 = 0x01
FEC_2_3 = 0x02
FEC_3_4 = 0x03
FEC_4_5 = 0x04
FEC_5_6 = 0x05
FEC_6_7 = 0x06
FEC_7_8 = 0x07
FEC_8_9 = 0x08
FEC_AUTO = 0x09
FEC_3_5 = 0x0a
FEC_9_10 = 0x0b

FEC_TYPE= {
	FEC_NONE:'None',
	FEC_1_2:'FEC 1/2',
	FEC_2_3:'FEC 2/3',
	FEC_3_4:'FEC 3/4',
	FEC_4_5:'FEC 4/5',
	FEC_5_6:'FEC 5/6',
	FEC_6_7:'FEC 6/7',
	FEC_7_8:'FEC 7/8',
	FEC_8_9:'FEC 8/9',
	FEC_AUTO:'FEC Auto',
	FEC_3_5:'FEC 3/5',
	FEC_9_10:'FEC 9/10'
	}	

POLARITIES=	{
		'H':'Horizontal',
		'V':'Vertical'
		}

INVERSION_OFF= 0x00
INVERSION_ON= 0x01
INVERSION_AUTO= 0x02

SPEC_INVERSION= {
	INVERSION_OFF:'Inversion Off',
	INVERSION_ON:'Inversion On',
	INVERSION_AUTO:'Auto Inversion'
	}

SEC_VOLTAGE_13= 0x00
SEC_VOLTAGE_18= 0x01
SEC_VOLTAGE_OFF= 0x02

VOLTAGE= {
	SEC_VOLTAGE_13:'13 Volts (Vertical Polarity)',
	SEC_VOLTAGE_18:'18 Volts (Horizontal Polarity)',
	SEC_VOLTAGE_OFF:'Off'
	}

SEC_TONE_ON= 0x00
SEC_TONE_OFF= 0x01

class DVB_DISEQC_MASTER_CMD (Structure):
	_fields_ =	[
			('framing', c_ubyte),
			('address', c_ubyte),
			('command', c_ubyte),
			('data', c_ubyte * 3),
			('len', c_ubyte)
			]

class DVB_DISEQC_SLAVE_REPLY (Structure):
	_fields_ =	[
			('framing', c_ubyte),
			('data', c_ubyte * 3),
			('len', c_ubyte),
			('timeout', c_int)
			]


class DVB_FE_STATUS (Structure):
	_fields_ =	[
			('status', c_uint32)
			]

class DVB_FRONTEND_INFO (Structure):
	_fields_ = 	[
			('name', c_char * 128),
			('type',c_uint),
			('frequency_min',c_uint32),
			('frequency_max',c_uint32),
			('frequency_stepsize',c_uint32),
			('frequency_tolerance',c_uint32),
			('symbol_rate_min',c_uint32),
			('symbol_rate_max',c_uint32),
			('symbol_rate_tolerance',c_uint32),
			('notifier_delay',c_uint32),
			('caps',c_uint32)
			]

class DVB_FRONTEND_PARAMETERS_QPSK (Structure):
	_fields_ =	[
			('frequency',c_uint32),
			('spectral_inversion',c_ubyte),
			('symbol_rate',c_uint32),
			('fec_inner',c_ubyte),
			('dummy',c_uint32),
			('dummy1',c_uint32),
			('dummy2',c_uint32),
			('dummy3',c_uint32),
			('dummy4',c_uint32)
			]

class DVB_FRONTEND_EVENT (Structure):
	_fields_ =	[
			('status',c_uint32),
			('params',DVB_FRONTEND_PARAMETERS_QPSK)
			]

class DVB_FRONTEND_VALUE_16 (Structure):
	_fields_ =      [
			('value',c_ushort)
			]

class DVB_FRONTEND_VALUE_32 (Structure):
	_fields_ =      [
			('value',c_uint)
			]

#
# common symbol rates
#

SYMBOL_RATES =	[
		27500000,
#		28000000,
#		29500000,
#		29900000,
		22000000,
		17000000,
#		16300000,
#		3333000,
#		6111000,
#		6666000
		5000000,
		]

#
# ioctl commands
#

DMX_STOP = _IO('o', 42)
FE_GET_INFO = _IOR('o',61,sizeof(DVB_FRONTEND_INFO))

FE_DISEQC_RESET_OVERLOAD = _IO('o', 62)
FE_DISEQC_SEND_MASTER_CMD = _IOW('o', 63, sizeof(DVB_DISEQC_MASTER_CMD))
FE_DISEQC_RECV_SLAVE_REPLY = _IOR('o', 64, sizeof(DVB_DISEQC_SLAVE_REPLY))
FE_DISEQC_SEND_BURST = _IO('o', 65)

FE_SET_TONE = _IO('o', 66)
FE_SET_VOLTAGE = _IO('o', 67)
FE_READ_STATUS = _IOR('o',69,sizeof(DVB_FE_STATUS))
FE_READ_BER = _IOR('o',70,sizeof(DVB_FRONTEND_VALUE_32))
FE_READ_SIGNAL_STRENGTH = _IOR('o',71,sizeof(DVB_FRONTEND_VALUE_16))
FE_READ_SNR = _IOR('o',72,sizeof(DVB_FRONTEND_VALUE_16))
FE_READ_READ_UNCORRECTED_BLOCKS = _IOR('o',73,sizeof(DVB_FRONTEND_VALUE_32))
FE_SET_FRONTEND = _IOW('o',76,sizeof(DVB_FRONTEND_PARAMETERS_QPSK))
FE_GET_FRONTEND = _IOR('o',77,sizeof(DVB_FRONTEND_PARAMETERS_QPSK))
FE_GET_EVENT = _IOR('o',78,sizeof(DVB_FRONTEND_EVENT))

#
# diseqc commands
#

DISEQC_RESET = 0x00
DISEQC_CLEAR_RESET = 0x01
DISEQC_STANDBY = 0x02
DISEQC_POWER_ON = 0x03
DISEQC_STATUS = 0x10
DISEQC_HALT = 0x60
DISEQC_LIMITS_OFF = 0x63
DISEQC_POS_SAT = 0x64
DISEQC_LIMIT_E = 0x66
DISEQC_LIMIT_W = 0x67
DISEQC_DRIVE_E = 0x68
DISEQC_DRIVE_W = 0x69
DISEQC_STORE = 0x6A
DISEQC_GOTO_STORE = 0x6B
DISEQC_GOTO_ANGLE = 0x6E
DISEQC_SET_POSITIONS = 0x6F

FRAMING = 0
ADDRESS = 1
DESCRIPTION = 2

DISEQC_FRAME_COMMAND_NO_REPLY = 0xE0
DISEQC_FRAME_COMMAND_NO_REPLY_REPEATED = 0xE1
DISEQC_FRAME_COMMAND_REPLY = 0xE2
DISEQC_FRAME_COMMAND_REPLY_REPEATED = 0xE3
DISEQC_FRAME_REPLY_NO_ERROR = 0xE4
DISEQC_FRAME_REPLY_NOT_SUPPORTED = 0xE5
DISEQC_FRAME_REPLY_PARITY_ERROR = 0xE6
DISEQC_FRAME_REPLY_NOT_RECOGNISED = 0xE7

DISEQC_ADDRESS_ANY_DEVICE = 0x00
DISEQC_ADDRESS_ANY_POSITIONER = 0x30
DISEQC_ADDRESS_AZIMUTH_POSITIONER = 0x31
DISEQC_ADDRESS_ELEVATION = 0x32

DISEQC_COMMANDS= {
		# command : (framing, address, description)
		# note that these have only been tested on AZIMUTH motor and may need tweaking for other applications
		DISEQC_POWER_ON : (DISEQC_FRAME_COMMAND_NO_REPLY, DISEQC_ADDRESS_AZIMUTH_POSITIONER, "Switch peripheral power on"),
		DISEQC_STATUS : (DISEQC_FRAME_COMMAND_REPLY, DISEQC_ADDRESS_AZIMUTH_POSITIONER, "Read positioner status"),
		DISEQC_HALT : (DISEQC_FRAME_COMMAND_NO_REPLY, DISEQC_ADDRESS_AZIMUTH_POSITIONER, "Stop Positioner movement"),
		DISEQC_LIMITS_OFF : (DISEQC_FRAME_COMMAND_NO_REPLY, DISEQC_ADDRESS_AZIMUTH_POSITIONER, "Disable limits"),
		DISEQC_POS_SAT : (DISEQC_FRAME_COMMAND_REPLY, DISEQC_ADDRESS_AZIMUTH_POSITIONER, "Read Positioner Status Register"),
		DISEQC_LIMIT_E : (DISEQC_FRAME_COMMAND_NO_REPLY, DISEQC_ADDRESS_AZIMUTH_POSITIONER, "Set East Limit"),
		DISEQC_LIMIT_W : (DISEQC_FRAME_COMMAND_NO_REPLY, DISEQC_ADDRESS_AZIMUTH_POSITIONER, "Set West Limit"),
		DISEQC_DRIVE_E : (DISEQC_FRAME_COMMAND_NO_REPLY, DISEQC_ADDRESS_AZIMUTH_POSITIONER, "Drive Motor East"),
		DISEQC_DRIVE_W : (DISEQC_FRAME_COMMAND_NO_REPLY, DISEQC_ADDRESS_AZIMUTH_POSITIONER, "Drive Motor West"),
		DISEQC_STORE : (DISEQC_FRAME_COMMAND_NO_REPLY, DISEQC_ADDRESS_AZIMUTH_POSITIONER, "Store Satellite Position & Enable Limits"),
		DISEQC_GOTO_STORE : (DISEQC_FRAME_COMMAND_NO_REPLY, DISEQC_ADDRESS_AZIMUTH_POSITIONER, "Drive Motor to stored Satellite Position"),
		DISEQC_GOTO_ANGLE : (DISEQC_FRAME_COMMAND_NO_REPLY, DISEQC_ADDRESS_AZIMUTH_POSITIONER, "Drive Motor to Angular Position"),
		DISEQC_SET_POSITIONS : (DISEQC_FRAME_COMMAND_NO_REPLY, DISEQC_ADDRESS_AZIMUTH_POSITIONER, "(Re-)Calulate Satellite Positions")
		}

DISEQC_FRAMING= {
	# command : description
	DISEQC_FRAME_COMMAND_NO_REPLY : 'Command from Master, No reply required, First transmission',
	DISEQC_FRAME_COMMAND_NO_REPLY_REPEATED : 'Command from Master, No reply required, Repeated transmission',
	DISEQC_FRAME_COMMAND_REPLY : 'Command from Master, Reply required, First transmission',
	DISEQC_FRAME_COMMAND_REPLY_REPEATED : 'Command from Master, No reply required, Repeated transmission',
	DISEQC_FRAME_REPLY_NO_ERROR : 'Reply from Slave, "OK", no errors detected',
	DISEQC_FRAME_REPLY_NOT_SUPPORTED : 'Reply from Slave, Command not supported by slave',
	DISEQC_FRAME_REPLY_PARITY_ERROR : 'Reply from Slave, Parity Error detected - Request repeat',
	DISEQC_FRAME_REPLY_NOT_RECOGNISED : 'Reply from Slave, Command not recognised - Request repeat'
	}

DISEQC_POS_MASK= {
		0:'Position reference data has been lost or corrupted',
		1:'Hardware switch (limit or reference) is activated',
		2:'Power is not available',
		3:'Software Limit (end-stop) has been reached',
		4:'Motor is running',
		5:'Movement direction is (or last was) West',
		6:'Software Limits are Enabled',
		7:'Movement command has been completed'
		}

UNBUFFERED = 0

# universal LNB settings
# Low Band: 10.70 - 11.70 GHz; LOF 9750 MHz
# High Band: 11.70 - 12.75 GHz; LOF 10600 MHz
LOW_BAND_MAX = 11700000
LOW_BAND_MIN = 10700000
LOW_OFFSET = 9750000
HIGH_OFFSET = 10600000

# return standard device name strings
def adapter():
	global DVB_Adapter
	return '/dev/dvb/adapter%d' % DVB_Adapter

def frontend():
	return '%s/frontend0' % adapter()

def demux():
	return '%s/demux0' % adapter()

#
# show contents of frontend parameter structure
#
def display_fe_params(params):
	print 'Frequency:', params.frequency
	print 'Spectral Inversion:', SPEC_INVERSION[params.spectral_inversion]
	print 'Symbol Rate:', params.symbol_rate
	print 'FEC:', FEC_TYPE[params.fec_inner]

# read frontend status
def dvb_fe_status(fd):
	status= DVB_FE_STATUS()
	ber= DVB_FRONTEND_VALUE_32()
	snr= DVB_FRONTEND_VALUE_16()
	strength= DVB_FRONTEND_VALUE_16()

	fcntl.ioctl(fd, FE_READ_BER, ber, True)
	fcntl.ioctl(fd, FE_READ_SNR, snr, True)
	fcntl.ioctl(fd, FE_READ_SIGNAL_STRENGTH, strength, True)

	try:
		fcntl.ioctl(fd, FE_READ_STATUS, status, True)
	except:
		print "can't get status!"


	if status.status & FE_HAS_LOCK:
		fe_params= DVB_FRONTEND_PARAMETERS_QPSK() 
		fcntl.ioctl(fd,FE_GET_FRONTEND,fe_params,True)
	else:
		fe_params= None

	return status, ber.value, snr.value, strength.value, fe_params

def get_signal_strength(fd):
	strength= DVB_FRONTEND_VALUE_16()

	try:	
		fcntl.ioctl(fd, FE_READ_SIGNAL_STRENGTH, strength, True)
	except:
		return False, 0

	return True, strength.value

def display_fe_status(status, ber, snr, strength):
	print
	print '                 Status:',
	indent= False
	for stat in sorted(FE_STATUS.keys()):
		if status.status & stat or status.status == stat:
			if indent:
				print '                        ', 
			else:
				indent= True
			print FE_STATUS[stat]
	print ' BER:', ber
	print ' SNR:', snr
	print ' STRENGTH:', strength
	print
	print 

def display_fe_device(device,fe):
	#
	# show frontend details
	#

	print
	print '                 Device:', device
	print '                   Name:', fe.name
	print '                   Type:', FE_TYPE_T[fe.type]
	print '               Min Freq: %.3f MHz (%d)' % (fe.frequency_min / 1000.0, fe.frequency_min + LOW_OFFSET)
	print '               Max Freq: %.3f MHz (%d)' % (fe.frequency_max / 1000.0, fe.frequency_max + HIGH_OFFSET)
	print '              Freq Step:', fe.frequency_stepsize / 1000.0, 'MHz'
	print '         Freq Tolerance:', fe.frequency_tolerance / 1000.0, 'MHz'
	print '        Min Symbol Rate: %d MSym/s (%d)' % (fe.symbol_rate_min / 1000000.0, fe.symbol_rate_min)
	print '        Max Symbol Rate: %d MSym/s (%d)' % (fe.symbol_rate_max / 1000000.0, fe.symbol_rate_max)
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

#
# open frontend device
#
def open_fe(frontend):
	fe= DVB_FRONTEND_INFO()
	try:
		fe_fd= open(frontend,'wb',UNBUFFERED)
		fcntl.ioctl(fe_fd,FE_GET_INFO,fe,True)
	except:
		return None, None, None

	if not fe.type == FE_TYPE_QPSK:
		print 'Fail! Wrong DVB type: %s - Only QPSK (DVB-S) devices supported.' % FE_TYPE_T[fe.type]
		print
		os._exit(False)
	#
	# (IO is asynch, so we need a polling mechanism)
	#

	fe_poll= select.poll()
	fe_poll.register(fe_fd,(select.POLLIN | select.POLLPRI))

	return fe_fd, fe_poll, fe

def open_demux(demux):
	try:
		demux_audio_fd= open(demux,'rb',UNBUFFERED)
		fcntl.ioctl(demux_audio_fd,DMX_STOP)
		demux_video_fd= open(demux,'rb',UNBUFFERED)
		fcntl.ioctl(demux_video_fd,DMX_STOP)
		demux_teletext_fd= open(demux,'rb',UNBUFFERED)
		fcntl.ioctl(demux_teletext_fd,DMX_STOP)
	except:
		return None, None, None

	return demux_audio_fd, demux_video_fd, demux_teletext_fd

# 
# return frontend event
# timeout of 0 will block until one occurs
# auto-retry after overflow event (EOVERFLOW)
#
def get_event(fd, poller, timeout):
	fe_event= DVB_FRONTEND_EVENT()
	while True:
		result = poller.poll(timeout)
		if result == []:
			return False, errno.EWOULDBLOCK
		else:
			for fd, event in result:
				if event & select.POLLIN:
					try:
						fcntl.ioctl(fd,FE_GET_EVENT,fe_event,True)
					except IOError, e:
						if e[0] == errno.EOVERFLOW:
							continue
						else:
							print "Can't read FE event!", e
							return False, e[0]
					return True, fe_event

#
# adjust frequency to offset for universal LNB
# return frequency and tone setting
# tone is OFF for L-Band (low)
#
def frequency_universal_lnb(frequency):
	if frequency < LOW_BAND_MAX:
		return frequency - LOW_OFFSET, SEC_TONE_OFF
	else:
		return frequency - HIGH_OFFSET, SEC_TONE_ON

# 
# inverse - convert back from universal LNB offset to absolute
#
def frequency_universal_absolute(frequency, tone):
	if tone == SEC_TONE_OFF:
		return frequency + LOW_OFFSET
	return frequency + HIGH_OFFSET

def set_polarity(fd, polarity):
	if polarity == 'H':
		voltage = SEC_VOLTAGE_18
	elif polarity == 'V':
		voltage = SEC_VOLTAGE_13
	else:
		return False
	try:
		fcntl.ioctl(fd,FE_SET_VOLTAGE,voltage)
		return True
	except:
		return False

#
# diseqc commands
#

# not done as I don't have a 2.x system!
def display_diseqc_status(fd, poller):
	ret, status= diseqc_get_positioner_status(fd, poller)

	if not ret:
		return ret, status

	print '%02x' % status.data[0]
	print '%02x' % status.data[1]
	print '%02x' % status.data[2]

	return True, None

def diseqc_get_positioner_status(fd, poller):
	status= DVB_DISEQC_SLAVE_REPLY()

	diseqc_send(fd, poller, DISEQC_STATUS, None, False)
	try:
		fcntl.ioctl(fd,FE_DISEQC_RECV_SLAVE_REPLY, status, True)
	except IOError, e:
		return False, e
	return True, status

# documentations says do this twice!
def diseqc_store(fd, poller, satno):
	diseqc_send(fd, poller, DISEQC_STORE, chr(satno), False)
	return diseqc_send(fd, poller, DISEQC_STORE, chr(satno), True)

def diseqc_goto_store(fd, poller, pos):
	diseqc_send(fd, poller, DISEQC_GOTO_STORE, chr(pos), False)
	return diseqc_send(fd, poller, DISEQC_GOTO_STORE, chr(pos), True)

def diseqc_power_on(fd, poller):
	return diseqc_send(fd, poller, DISEQC_POWER_ON, None, False)

def diseqc_halt(fd, poller):
	return diseqc_send(fd, poller, DISEQC_HALT, None, False)

def diseqc_set_limit(fd, poller, compass):
	if compass == 'WEST':
		command= DISEQC_LIMIT_W
	else:
		command= DISEQC_LIMIT_E
	diseqc_send(fd, poller, DISEQC_LIMITS_OFF, None, False)
	diseqc_send(fd, poller, command, None, False)
	return diseqc_enable_limits(fd, poller)

# switch on soft limits - this is a special case of 'Store Satellite Position'
# with a satellite number of 0
def diseqc_enable_limits(fd, poller):
	return diseqc_store(fd, poller, 0)

def diseqc_drive(fd, poller, command, type, steps, power_time):
	# send negative value if stepping
	if type == 'STEP':
		steps= 0xff - (steps - 1)

	# power on
	diseqc_power_on(fd, poller)
	time.sleep(2)
	stat, ret= diseqc_send(fd, poller, command, chr(steps), False)
	if stat and type == 'TIME':
		# stay powered on for desired time
		time.sleep(power_time)
	return stat, ret
		
# point rotor to a specific angle
# (ported from xdipo & simplified)
def diseqc_steer(fd, poller, degrees, compass):
	if compass == 'WEST':
		nib1h= 0x0D
	else:
		nib1h= 0x0E

	nib1l = int(degrees / 16.0)
	nib2h = int(degrees)

	da = degrees - int(degrees)
	nib2l= int(round(da * 16.0))

	# would generate a carry to 0x10 for values close to one of da, because of rounding up to 1
	if( (da > 0.9) and ( (nib2l & 0xf) == 0) ):
		nib2l = 0xf

	data= chr(( (int(nib1h) & 0xf) << 4) | (int(nib1l) & 0xf))
	data += chr(( (int(nib2h) & 0xf) << 4) | (int(nib2l) & 0xf))

	diseqc_send(fd, poller, DISEQC_GOTO_ANGLE, data, False)
	return diseqc_send(fd, poller, DISEQC_GOTO_ANGLE, data, True)


def diseqc_reset(fd, poller):
	diseqc_send(fd, poller, DISEQC_CLEAR_RESET, False)
	return diseqc_send(fd, poller, DISEQC_CLEAR_RESET, True)

def diseqc_send(fd, poller, command, data, repeat):
	diseqc_command= DVB_DISEQC_MASTER_CMD()

	diseqc_command.command= command
	diseqc_command.framing= DISEQC_COMMANDS[command][FRAMING]
	if repeat:
		diseqc_command.framing += 1
	diseqc_command.address= DISEQC_COMMANDS[command][ADDRESS]
	diseqc_command.data= (c_ubyte * 3) (0,0,0)
	diseqc_command.len= 3
	if data:
		for x in range(len(data)):
			diseqc_command.data[x]= ord(data[x])
		diseqc_command.len += len(data)
	#print 'sending %s %02x %02x %02x %02x %02x %02x %02x' % (DISEQC_COMMANDS[command][DESCRIPTION], diseqc_command.framing, diseqc_command.address, diseqc_command.command, diseqc_command.data[0], diseqc_command.data[1], diseqc_command.data[2], diseqc_command.len)
	try:
		fcntl.ioctl(fd,FE_DISEQC_SEND_MASTER_CMD,diseqc_command)
	except IOError, e:
		return False, e

	#dvb_fe_wait(fd, poller)
	time.sleep(.1)
	return True, None


#
# tune DVB receiver
# returns frontend event
#
def dvb_tune(fd, poller, frequency, polarity, symbol_rate):
	fe_params= DVB_FRONTEND_PARAMETERS_QPSK()

	fe_params.spectral_inversion = INVERSION_AUTO
	fe_params.symbol_rate = symbol_rate
	fe_params.fec_inner = FEC_AUTO 

	if not set_polarity(fd, polarity):
		print "Can't set polarity!"
		return False

	fe_params.frequency, tone = frequency_universal_lnb(frequency)
	#print 'Setting frequency:', frequency, fe_params.frequency, tone, fe_params.symbol_rate
	try:
		fcntl.ioctl(fd,FE_SET_TONE,tone)
	except:
		print "Can't set TONE!"
		return False
	try:
		#display_fe_params(fe_params)
		fcntl.ioctl(fd,FE_SET_FRONTEND,fe_params,True)
	except:
		print "Can't set FE parameters!"
		display_fe_params(fe_params)

	return dvb_fe_wait(fd,poller)

def dvb_fe_wait(fd,poller):
	# wait for FE to report done
	while True:
		ret, event = get_event(fd,poller,0)
		#print event.status
		if(ret):
			#display_fe_params(event.params)
			#print 'event.status', event.status
			#if event.status == FE_NO_SIGNAL:
			#	# tuner has not settled, try again
			#	continue
			return True, event
		else:
			# event timed out - try again
			continue

# 
# look for carrier with both vertical and horizontal polarisation to eliminate false positives
# signal with SYNC automatically passes straight away to speed things up
#

def detect_carrier(fd, poller, frequency, polarity, symbol_rate):
	ret = dvb_tune(fd, poller, frequency, polarity, symbol_rate)
	if ret.status & FE_HAS_SYNC:
		return True
	if not ret.status & FE_HAS_CARRIER:
		return False
	if polarity == 'H':
		polarity= 'V'
	else:
		polarity= 'H'
	ret = dvb_tune(fd, poller, frequency, polarity, symbol_rate)
	if not ret.status & FE_HAS_CARRIER:
		return False
	return True

#
# find symbol rate
# return True/False, symbol rate, polarity
# retrun True if carrier detected, but couldn't get LOCK (parity is '?')
#

LastPolarity= 'H'
def detect_symbol_rate(fd, poller, frequency, polarity,symbol_rate):
	global LastPolarity

	# signal will tend to have the same symbol rate as the previous
	# so ensure we try it first and only once
	try_rates= [symbol_rate]
	for rate in SYMBOL_RATES:
		if not rate == symbol_rate:
			try_rates.append(rate)

	had_carrier= False
	if LastPolarity == 'H':
		try_polarity= ['H','V']
	else:
		try_polarity= ['V','H']
	for rate in try_rates:
		for polarity in try_polarity:
			spinner()
			stat, ret= dvb_tune(fd, poller, frequency, polarity, rate)
			if stat:
				if ret.status & FE_HAS_LOCK:
					LastPolarity= polarity
					return True, rate, polarity
				if ret.status & FE_HAS_CARRIER:
					had_carrier= True
	# return requested rate to preserve it for next run
	if had_carrier:
		return True, symbol_rate, '-'
	return False, symbol_rate, '!'

def detect_signal_strength(fd, poller, frequency, polarity, rate):
	stat, ret= dvb_tune(fd, poller, frequency, polarity, rate)
	if stat:
		return get_signal_strength(fd)
	else:
		return False, 0
