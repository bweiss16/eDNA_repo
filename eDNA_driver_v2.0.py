# VERSION 2.0
# Last updated 7/10/24 by Ben Weiss

#################################################################################################
# This driver commands the MultiPuffer Sampler System from DAP                                  #
# Pump time and duration are set in config.ini                                                  #
# Pump time is defined in seconds afer the lander reaches the bottom                            #
# WARNING: RUN NO MORE THAN 2 PUMPS SIMULTANEOUSLY                                              #
# Code developed at WHOI by Ben Weiss <bweiss@whoi.edu> in collaboration with Chris Roman at URI#
#################################################################################################

#!/usr/bin/pytho
import sys, lcm, select, serial, time, math, string
from argparse import ArgumentParser
from datetime import datetime, date
from urioce_lcm import *
from mission_utils import *  #gets the mission parser
from threading import Timer
import configparser

STATE_MSG_TIME = 2 #how often state messages should be sent out
LOGFILE_NAME = '/home/ednavbox_lander1/Desktop/field/src/applications/drivers/eDNA_driver/edna.txt'
configFilePath = r'/home/ednavbox_lander1/Desktop/field/src/applications/drivers/eDNA_driver/config.ini'

# read values from pump_times.ini
def read_config():
	# Create a ConfigParser object
	config = configparser.RawConfigParser()
	config.read(configFilePath)

	# create vars to return
	pump_starts = [0]*16
	pump_durations = [0]*16
	pump_off = 500000 #initializing as a large number beyond scope of mission

	# Access values from the configuration file
	for i in range(0,16,1):
		pump_starts[i] = int(config.get('Starts', 'pump_' + str(i) + '_start'))
		pump_durations[i] = int(config.get('Durations', 'pump_' + str(i) + '_duration'))

	pump_off = int(config.get('Off', 'pump_off'))

	return pump_durations, pump_off, pump_starts 
  

#use the function
# Call the function to read the configuration file
pump_durations, pump_off, pump_starts = read_config()

class eDNA_driver:
  def __init__(self):
    # open serial port
    parser = ArgumentParser(description='eDNA driver')
    parser.add_argument('-b', dest='baudrate', type=int, help='Serial baudrate')
    parser.add_argument('-D', dest='device', type=str, help='Serial device')
    args = parser.parse_args()
    if args.device is None or args.baudrate is None:
      exit('Must specify serial device and baudrate.')
    try:
      self.ser = serial.Serial(port=args.device, baudrate=args.baudrate,
                          bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                          stopbits=serial.STOPBITS_ONE, timeout=None,
                          xonxoff=0, rtscts=0);
      self.ser.nonblocking()
      pass
    except serial.serialutil.SerialException as msg:
      exit('Failed to open %s at %d: %s' % (args.device, args.baudrate, msg.message))

    self.logfile = open(LOGFILE_NAME, 'a+')
      
    # open LCM, set up subscriptions
    self.lc = lcm.LCM()
    self.lc.subscribe("MIS_STATE", self.mission_handler)
    self.lc.subscribe("SBE9_DATA",self.sbe_handler)

    self.last_state_msg_time = 0
    self.mis_state = lander_mission_state_t()
  
    # generate a dictionary for the CTD data from sbe9 to be stored in
    self.sbe_data = dict()
    # fill dictionary categories as CTD data titles 
    # set up each category as a data object to be filled
    self.sbe_data['TEMPERATURE'] = dataObj()
    self.sbe_data['PRESSURE'] = dataObj() 
    self.sbe_data['SALINITY'] = dataObj() 
    self.sbe_data['OXYGEN'] = dataObj()
    self.sbe_data['timestamp'] = dataObj()
    self.record = False

  ################################################################### 
  # main loop
  def run(self):

    #flags to track first DOWN event and pumps
    DOWN_flag = True
    PUMPS_flag = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
    DONE_PUMPING = False

    #initialize sampler immediatly so that we can determine if there are problems
    print "initializing sampler"
    self.send_to_serial(b"MP Wake\r")
    time.sleep(1)    

    while True:
      try:
          
        sread, swrite, serr = select.select([self.lc.fileno(), self.ser.fileno()], [], [], 2.)
        if sread.__len__() > 0:
          if sread[0] == self.lc.fileno():
            self.lc.handle()
          elif sread[0] == self.ser.fileno():
            line = self.ser.readline().strip()
            print "Got line %s" % line
            if(len(line) > 1):
              self.logfile.write('RX %10.6f %s\n' % (time.time(), line)) #writes the incoming traffic to a log 


            
          #if you want to publish or print a state message do it here....     
          if(time.time() - self.last_state_msg_time > STATE_MSG_TIME):
            self.last_state_msg_time = time.time()
            #lcm_state_msg = ek80_state_t()
            #lcm_state_msg.timestamp = time.time()*1e6
            #lcm_state_msg.state = self.current_state
            #self.lc.publish(self.state_channel, lcm_state_msg.encode())
            
            mission_time = sec_time(self.mis_state.mis_time)

            if(DOWN_flag == False):
               time_elapsed = mission_time-sample_time_0
            else:
               time_elapsed = 0
               
            print "Mission time %s, state: %s, depth %5.2f, bottom time: %i s" % ( strftime("%H:%M:%S", gmtime(mission_time)), valid_states[self.mis_state.state], self.mis_state.depth, time_elapsed )
        
            #Check to see if sampler has reached the bottom
            if(valid_states[self.mis_state.state] == "BOTTOM" and DOWN_flag == True):
               print "the Eagle has landed"
               sample_time_0 = mission_time
               print "Sample Time 0 = %s" % sample_time_0
               DOWN_flag = False


            elif(DOWN_flag == False):
               time_elapsed = mission_time-sample_time_0
               if(time_elapsed > pump_starts[0] and PUMPS_flag[0]==True):
                  self.send_to_serial(b"MP Run_Pump 0 for " + str(pump_durations[0]).encode() + " S" + b"\r")
                  PUMPS_flag[0]=0
               elif(time_elapsed > pump_starts[1] and PUMPS_flag[1]==True):
                  self.send_to_serial(b"MP Run_Pump 1 for " + str(pump_durations[1]).encode() + " S" + b"\r")
                  PUMPS_flag[1]=0                
               elif(time_elapsed > pump_starts[2] and PUMPS_flag[2]==True):
                  self.send_to_serial(b"MP Run_Pump 2 for " + str(pump_durations[2]).encode() + " S" + b"\r")
                  PUMPS_flag[2]=0
               elif(time_elapsed > pump_starts[3] and PUMPS_flag[3]==True):
                  self.send_to_serial(b"MP Run_Pump 3 for " + str(pump_durations[3]).encode() + " S" + b"\r")
                  PUMPS_flag[3]=0  
               elif(time_elapsed > pump_starts[4] and PUMPS_flag[4]==True):
                  self.send_to_serial(b"MP Run_Pump 4 for " + str(pump_durations[4]).encode() + " S" + b"\r")
                  PUMPS_flag[4]=0  
               elif(time_elapsed > pump_starts[5] and PUMPS_flag[5]==True):
                  self.send_to_serial(b"MP Run_Pump 5 for " + str(pump_durations[5]).encode() + " S" + b"\r")
                  PUMPS_flag[5]=0                
               elif(time_elapsed > pump_starts[6] and PUMPS_flag[6]==True):
                  self.send_to_serial(b"MP Run_Pump 6 for " + str(pump_durations[6]).encode() + " S" + b"\r")
                  PUMPS_flag[6]=0
               elif(time_elapsed > pump_starts[7] and PUMPS_flag[7]==True):
                  self.send_to_serial(b"MP Run_Pump 7 for " + str(pump_durations[7]).encode() + " S" + b"\r")
                  PUMPS_flag[7]=0  
               elif(time_elapsed > pump_starts[8] and PUMPS_flag[8]==True):
                  self.send_to_serial(b"MP Run_Pump 8 for " + str(pump_durations[8]).encode() + " S" + b"\r")
                  PUMPS_flag[8]=0 
               elif(time_elapsed > pump_starts[9] and PUMPS_flag[9]==True):
                  self.send_to_serial(b"MP Run_Pump 9 for " + str(pump_durations[9]).encode() + " S" + b"\r")
                  PUMPS_flag[9]=0                
               elif(time_elapsed > pump_starts[10] and PUMPS_flag[10]==True):
                  self.send_to_serial(b"MP Run_Pump 10 for " + str(pump_durations[10]).encode() + " S" + b"\r")
                  PUMPS_flag[10]=0
               elif(time_elapsed > pump_starts[11] and PUMPS_flag[11]==True):
                  self.send_to_serial(b"MP Run_Pump 11 for " + str(pump_durations[11]).encode() + " S" + b"\r")
                  PUMPS_flag[11]=0  
               elif(time_elapsed > pump_starts[12] and PUMPS_flag[12]==True):
                  self.send_to_serial(b"MP Run_Pump 12 for " + str(pump_durations[12]).encode() + " S" + b"\r")
                  PUMPS_flag[12]=0  
               elif(time_elapsed > pump_starts[13] and PUMPS_flag[13]==True):
                  self.send_to_serial(b"MP Run_Pump 13 for " + str(pump_durations[13]).encode() + " S" + b"\r")
                  PUMPS_flag[13]=0                
               elif(time_elapsed > pump_starts[14] and PUMPS_flag[14]==True):
                  self.send_to_serial(b"MP Run_Pump 14 for " + str(pump_durations[14]).encode() + " S" + b"\r")
                  PUMPS_flag[14]=0
               elif(time_elapsed > pump_starts[15] and PUMPS_flag[15]==True):
                  self.send_to_serial(b"MP Run_Pump 15 for " + str(pump_durations[15]).encode() + " S" + b"\r")
                  PUMPS_flag[15]=0  
               elif(time_elapsed > pump_off and DONE_PUMPING==False):
                  self.send_to_serial(b"MP Stop_All_Pumps\r")
                  DONE_PUMPING = True  
                                             
        else:
          print "Timeout, no LCM or serial traffic"
          
      except KeyboardInterrupt:
        self.logfile.close()
        return

  ###################################################################    
  # handler for incoming mission state LCM message
  def mission_handler(self, channel, data):
    try:
      msg = lander_mission_state_t.decode(data)
    except ValueError:
      print('Failed to decode LCM message.')
      return

    # while going DOWN set record flag, turn off when no longer going DOWN
    if(msg.state == DOWN):
      self.record = True
    else: 
      self.record = False
    
    self.mis_state.timestamp = msg.timestamp
    self.mis_state.state = msg.state
    self.mis_state.mis_time = msg.mis_time
    self.mis_state.in_water = msg.in_water
    self.mis_state.depth = msg.depth
    self.mis_state.in_water = msg.in_water

  ###################################################################  
  # sending to serial port, and logging    
  def send_to_serial(self,cmd_string):
    self.ser.write(cmd_string)
    self.logfile.write('TX %10.6f %s\n' % (time.time(), cmd_string))
    print "Sent: %s" % cmd_string

  ###################################################################  
  # handler for SBE9_DATA LCM messages          
  def sbe_handler(self, channel, data):
    # while going DOWN save CTD data from the LCM messages
    """Handle data sent from sbe9 """
    try: msg = sbe9_data_t.decode(data)
    except ValueError:
      print("Invalid sbe9 message")
      return
        
    # save CTD data as object oriented lists
    if(self.record):
      self.sbe_data['TEMPERATURE'].append(msg.temp)
      self.sbe_data['PRESSURE'].append(msg.pres)
      self.sbe_data['SALINITY'].append(msg.sal)                
      self.sbe_data['OXYGEN'].append(msg.o2)
      self.sbe_data['timestamp'].append(msg.timestamp)

###################################################################      
def sec_time(microtime):
  return microtime / 1000000

###################################################################
# create object class, this is taken from lander_bottle_adaption.py
class dataObj():
    def __init__(self):
        self.data = list()                # initialize the object input as a list

    def append(self,x):                   # add data to end of list as it comes in
        self.data.append(x)
    
    def max_ind(self):                    # calculate the index of the maximum value in the list
        # find the max value then search the list for the index of that value
        ind = self.data.index(max(self.data))
        return(ind)                       # returns the index value 
        
    def min_ind(self):                    # calculate the index of the minimum value in the list
        # find the min value then search the list for the index of that value
        ind = self.data.index(min(self.data))
        return(ind)                       # returns the index value

    def ind_of_value(self,value):         # returns the index of the input value 
        # calculates the difference between the array and the value of interest and finds the number in the array
        # with the smallest difference (smallest of the abs value)
        data_array = np.array(self.data)  # converts the list to a number array
        data_array = np.absolute(data_array - value) 
        ind = np.argmin(data_array)
        return(ind)                       # returns the index value

    def value_of_ind(self,ind):           # returns the value of the array at the index specified
        return self.data[ind]    
       
    ''' NEED a way to identify all points that return the same values in 'ind_of_value' 
    and a way to parse out multiple locations and pick the one we are interested in '''
    def upper_value(self, value):
        pass
    
    def lower_value(self, value):
        pass
    
    ''' NEED to identify a small mass of water of different properties in deep water 
    (slight temp/o2/salt change for a few meters) '''
    def deep_water_mass(self):
        pass
    
  #  ''' NEED to pull out the thermocline and other gradient positions ''''
    def gradient(self, time_array):
        dt = 24*10 # there are 24 samples per sec -- helps filter down slightly
        # calculate the gradient and find the maximum change of the gradient
        data_array = np.array(self.data)
        
        # in case the time and data arrays are off in length, adjust accordingly
        adjust_array = 0
        while adjust_array == 0:
            if time_array.__len__() < data_array.__len__():
                print 'adjusting data array length'
                data_array = np.delete(data_array,-1)
            elif time_array.__len__() > data_array.__len__():
                print 'adjusting time array length'
                time_array = np.delete(time_array,-1)
            else:
                print 'no adjustment needed'
                adjust_array = 1
            
        # filter/smooth data array before taking the derivative
        smooth_array = np.convolve(data_array, np.ones((dt,))/dt, mode='same')
        print 'here'
        # the convolution contains boundary effects - want to analyze data away from boundaries (dt/2 in on each side of the vector)
        dt_2 = int(dt/2)
        
#        difference = np.diff(smooth_array)          # data difference
#        time_diff = np.diff((time_array)*1e-6)     # time difference
        
        difference = smooth_array[(dt_2+1):(-(dt_2))]-smooth_array[(dt_2):(-(dt_2+1))]           # data difference
        time_diff = (time_array[(dt_2+1):(-(dt_2))]-time_array[(dt_2):(-(dt_2+1))])*10**(-6)     # time difference
        # calculate the gradient
        d_dt = (difference/time_diff)
        # find max index
        dt_ind = np.argmax(np.abs(d_dt))
        ind = int((dt_ind))
        print ind
        return(ind)
        
    def get_density(self, SP, t, p, lat):
        SA = gsw.conversions.SA_from_SP(SP,p,-70,lat)
        CT = gsw.conversions.CT_from_t(SA,t,p)
        density = gsw.rho(SA, CT, p)
        self.data = density.tolist()
    
    def obj_to_array(self):
        array = np.array(self.data)
        return array
    
    def get_time(self, top_ind, bottom_ind):
        time_array = np.array(self.data)
        time_array = time_array[top_ind:bottom_ind]
        return time_array
        
    def window(self, top_ind, bottom_ind):
        return self.data[top_ind:bottom_ind]
        
    def equals(self, data_list):
        self.data = data_list
    
    def clear(self):
        self.data[:] = []



      
eDNA_obj = eDNA_driver()
eDNA_obj.run()
 
