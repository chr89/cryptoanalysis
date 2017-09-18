# -*- coding: utf-8 -*-
"""
Created on Fri Sep 15 17:09:31 2017

@author: chr89
"""

### DEPENDENCIES ###
import matplotlib
matplotlib.use('TkAgg')
from matplotlib import dates
from numpy import arange, sin, pi
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
# implement the default mpl key bindings
from matplotlib.backend_bases import key_press_handler
from matplotlib.finance import quotes_historical_yahoo_ohlc, candlestick_ohlc
from matplotlib.dates import DateFormatter, WeekdayLocator,\
    DayLocator, MONDAY, HourLocator, MinuteLocator, AutoDateLocator, AutoDateFormatter
from matplotlib.figure import Figure
import tkMessageBox
#import pyglet
import pygame
import time
import numpy as np
import requests
import datetime
import sys


#############################
if sys.version_info[0] < 3:
    import Tkinter as Tk
else:
    import tkinter as Tk
    
###########################################################################
###########################################################################
###########################################################################

## CONFIGURATION ########
coins = ['ETH','XRP','BTC','ICN','BCH','LTC','ZEC']
reference_currency = 'EUR'
exchange = "Kraken"
plot_lines = 1 # 0 or 1
plot_coin = 4 # 0-4
histo_type = 0 # 0=Minute, 1=Hour, 2=Day
histo_limit = 200
aggregate_data = 1 # 1=default, max=30

###########################################################################
###########################################################################    
###########################################################################    

#####################
## aux functions
#####################

def binning(arr,size):
    arr = np.array(arr)
    residual_length = len(arr) % size
    length = len(arr) / size
    if residual_length == 0:
        new_len = length
    else:
        new_len = length+1
    av_array = np.zeros(new_len)
    for j in range(new_len):
        if residual_length != 0 and j == length-1:
            av_array[j] = np.mean(arr[j*size:])
        else:
            av_array[j] = np.mean(arr[j*size:(j+1)*size])
    return av_array
    
def averaging(arr,size):
    arr = np.array(arr)
    length = len(arr)
    new_arr = np.zeros(length)
    for j in range(length):
        dist = min([j,length-1-j])
        if dist > size:
            new_arr[j] = sum(arr[j-size:j+size+1])/float(2*size+1)
        elif dist == 0:
            new_arr[j] = arr[j]
        else:
            new_arr[j] = sum(arr[j-dist:j+dist+1])/float(2*dist+1)
    return new_arr

def derivative(x,y):
    x = np.array(x)
    length = len(x)
    new_arr = np.zeros(length)
    for j in range(length):
        if j != length-1:
            new_arr[j] = (y[j+1]-y[j])/(x[j+1]-x[j])
        else:
            new_arr[j] = 0
    return new_arr
    
def exp_smoothing(vals,alpha):
    res = np.zeros(len(vals))
    res[0] = vals[0]
    for j in range(1,len(res),1):
        res[j] = res[j-1] + alpha*(vals[j]-res[j-1])
    return res
    
def MACD(vals):
    ema12 = exp_smoothing(vals,0.15)
    ema26 = exp_smoothing(vals,0.075)
    macd = ema12 - ema26
    trigger = exp_smoothing(macd,0.2)
    return macd,trigger
    

def loadCoinHisto(hist_st,coin,reference_currency,histo_limit,aggregate_data,exchange):
    coin_hist = requests.get("https://min-api.cryptocompare.com/data/histo"+str(hist_st)+"?fsym="+coin+"&tsym="+reference_currency+"&limit="+str(histo_limit)+"&aggregate="+str(aggregate_data)+"&e="+exchange).json()["Data"]
    coin_to_eth_hist = requests.get("https://min-api.cryptocompare.com/data/histo"+str(hist_st)+"?fsym="+coin+"&tsym=ETH&limit="+str(histo_limit)+"&aggregate="+str(aggregate_data)+"&e="+exchange).json()["Data"]
    eth_hist = requests.get("https://min-api.cryptocompare.com/data/histo"+str(hist_st)+"?fsym=ETH&tsym=EUR&limit="+str(histo_limit)+"&aggregate="+str(aggregate_data)+"&e="+exchange).json()["Data"]
    
    #print coin_hist[0]["time"]

    progress_close = []
    progress_high = []
    progress_low = []
    progress_open = []
    progress_time = []
    progress_time_raw = []
    transf_progress = []
    transf_time = []
    
    for j in range(len(coin_hist)):
        progress_close.append(coin_hist[j]["close"])
        progress_high.append(coin_hist[j]["high"])
        progress_low.append(coin_hist[j]["low"])
        progress_open.append(coin_hist[j]["open"])
        progress_time.append(dates.date2num(datetime.datetime.fromtimestamp(coin_hist[j]["time"])))
        progress_time_raw.append(coin_hist[j]["time"])
        #print datetime.datetime.fromtimestamp(coin_hist[j]["time"])
        
    for j in range(len(coin_to_eth_hist)):
        transf_progress.append(coin_to_eth_hist[j]["close"]*eth_hist[j]["close"])
        transf_time.append(dates.date2num(datetime.datetime.fromtimestamp(coin_to_eth_hist[j]["time"])))
        
    return progress_close,progress_high,progress_low,progress_open,progress_time,progress_time_raw,transf_progress,transf_time
    
def loadAllCoinsHistory():
    for j in range(len(coins)):
        coin_data[j] = loadCoinHisto(hist_st,coins[j],reference_currency,histo_limit,aggregate_data,exchange)
        
    
############################################################
############################################################
############################################################    


### global definitions ##

# coin data is stored globally
coin_data = [[] for i in range(len(coins))]
subplot_handles = [[],[],[],[],[]]
             
if histo_type == 0:
    hist_st = "minute"
elif histo_type == 1:
    hist_st = "hour"
elif histo_type == 2:
    hist_st = "day"    

coin_selection = 0

# general settings for plotting

#mondays = WeekdayLocator(MONDAY)        # major ticks on the mondays
#alldays = DayLocator()              # minor ticks on the days
hours = HourLocator()
minutes = MinuteLocator(interval=20)

#weekFormatter = DateFormatter('%b %d')  # e.g., Jan 12
#dayFormatter = DateFormatter('%d')      # e.g., 12
hourFormatter = DateFormatter('%H')      # e.g., 23
minuteFormatter = DateFormatter('%H:%M')      # e.g., 24:12 
    
###########################################################


## get coinlist with all coin names

coinlist_fullinfo = requests.get("https://www.cryptocompare.com/api/data/coinlist/").json()

coinlist_names_unicode = coinlist_fullinfo["Data"].keys()
coinlist_names = []

for elem in coinlist_names_unicode:
    coinlist_names.append(elem.encode("ascii","ignore"))
coinlist_names.sort()

###
print "COMPLETE COINLIST:\n"
print coinlist_names
print
print "Number of total coins:",len(coinlist_names)
print 

for j in range(len(coins)):
    print coinlist_fullinfo["Data"][coins[j]]["FullName"].encode("ascii","ignore")
print "\n\n"

###########################################################################


##############################################    

print "load history..."
loadAllCoinsHistory()

#print coin_data


root = Tk.Tk()
root.wm_title("Cryptoanalysis")

##############################################

def onselect(evt):
    # Note here that Tkinter passes an event object to onselect()
    w = evt.widget
    index = int(w.curselection()[0])
    value = w.get(index)
    print 'You selected item %d: "%s"' % (index, value)
    coin_selection = index
    #tkMessageBox.showinfo("title","FUCK HELL YEAH!")
    
    if len(coin_data[coin_selection][0]) > 0:
        print "coin data {} selected!".format(coin_selection)
        progr = coin_data[coin_selection][0]
        progr_time = coin_data[coin_selection][4]
    else:
        progr = coin_data[coin_selection][6]
        progr_time = coin_data[coin_selection][7]

    # calculate some quantities... 
    avg2 = averaging(progr,2)
    avg4 = averaging(progr,4)
    avg6 = averaging(progr,8)
    slope = derivative(progr_time,avg6)
    curvature = derivative(progr_time,slope)
    #convolved = np.convolve(progr,progr)
    fourier = np.fft.rfft(np.array(progr)/float(sum(np.array(progr))))
    fourier_freq = np.fft.rfftfreq(len(progr),d=aggregate_data)

    
    #pres1.set_data(progr_time,progr)
    subplot_handles[0].clear()
    subplot_handles[0].plot_date(progr_time,progr,"-b",label='closing price')
    subplot_handles[0].plot_date(progr_time,avg2,'-r',label='average-2')
    subplot_handles[0].plot_date(progr_time,avg4,'-g',label='average-4')
    subplot_handles[0].plot_date(progr_time,avg6,'--k',label='average-6')    
    subplot_handles[0].set_title(coinlist_fullinfo["Data"][coins[coin_selection]]["FullName"].encode("ascii","ignore")+" price")
    subplot_handles[0].grid(True)    
    subplot_handles[0].xaxis.set_major_locator(minutes)
    subplot_handles[0].xaxis.set_major_formatter(minuteFormatter)
    
    subplot_handles[1].clear()
    macd,trigger = MACD(progr)
    macd_histo = macd - trigger
    subplot_handles[1].plot_date(progr_time,macd,'-b',label='MACD')
    subplot_handles[1].plot_date(progr_time,trigger,'-r',label='Trigger')
    subplot_handles[1].plot_date(progr_time,macd_histo,'--g')
    subplot_handles[1].legend(prop={'size':10})
    subplot_handles[1].grid(True)
    subplot_handles[1].xaxis.set_major_locator(minutes)
    subplot_handles[1].xaxis.set_major_formatter(minuteFormatter)
    
            
    subplot_handles[2].clear()
    subplot_handles[2].semilogy(fourier_freq[1:],np.abs(fourier[1:]),'-o')
    subplot_handles[2].set_xlabel("Frequency")
    
    subplot_handles[3].clear()
    subplot_handles[3].plot_date(progr_time,slope,'-co',label='Slope')
    subplot_handles[3].grid(True)
    subplot_handles[3].xaxis.set_major_locator(minutes)
    subplot_handles[3].xaxis.set_major_formatter(minuteFormatter)
    
    subplot_handles[4].clear()
    quotes = zip(coin_data[coin_selection][4],coin_data[coin_selection][3],coin_data[coin_selection][1],coin_data[coin_selection][2],coin_data[coin_selection][0])
    progress_time_raw = coin_data[coin_selection][5]
    
    time_min = datetime.datetime.fromtimestamp(progress_time_raw[0])
    time_max = datetime.datetime.fromtimestamp(progress_time_raw[-1])
    subplot_handles[4].set_xlim(time_min,time_max)
    subplot_handles[4].plot_date(progr_time,progr,"--k")
    candlestick_ohlc(subplot_handles[4],quotes,colorup="g",colordown="r",width=6.94e-4)
    subplot_handles[4].set_title(coinlist_fullinfo["Data"][coins[plot_coin]]["FullName"].encode("ascii","ignore")+" price")
    subplot_handles[4].set_ylabel("Price (EUR)",fontsize=20)
    subplot_handles[4].grid(True)
    subplot_handles[4].xaxis.set_major_locator(minutes)
    subplot_handles[4].xaxis.set_major_formatter(minuteFormatter)
    
    f.canvas.draw()
    
    #pygame.init()
    #pygame.mixer.music.load("abc.mp3")
    #pygame.mixer.music.play()
    #time.sleep(30)
    #pygame.mixer.music.stop()

#############################################
############# GUI ###########################
#############################################

listbox = Tk.Listbox(master=root,selectmode=Tk.SINGLE)
listbox.pack(side=Tk.LEFT)
for coin in coins:
    listbox.insert(Tk.END,coin)
listbox.bind('<<ListboxSelect>>',onselect)

##### plotting #####

f = Figure(figsize=(16, 8), dpi=100)
tmp_hndl = f.add_subplot(321)
subplot_handles[0] = tmp_hndl
tmp_hndl = f.add_subplot(322)
subplot_handles[1] = tmp_hndl
tmp_hndl = f.add_subplot(323)
subplot_handles[2] = tmp_hndl
tmp_hndl = f.add_subplot(324)
subplot_handles[3] = tmp_hndl
tmp_hndl = f.add_subplot(325)
subplot_handles[4] = tmp_hndl
f.tight_layout()

if len(coin_data[coin_selection][0]) > 0:
    progr = coin_data[coin_selection][0]
    progr_time = coin_data[coin_selection][4]
else:
    progr = coin_data[coin_selection][6]
    progr_time = coin_data[coin_selection][7]

# calculate some quantities... 
avg2 = averaging(progr,2)
avg4 = averaging(progr,4)
avg6 = averaging(progr,8)
slope = derivative(progr_time,avg6)
curvature = derivative(progr_time,slope)
#convolved = np.convolve(progr,progr)
fourier = np.fft.rfft(np.array(progr)/float(sum(np.array(progr))))
fourier_freq = np.fft.rfftfreq(len(progr),d=aggregate_data)


pres1, = subplot_handles[0].plot_date(progr_time,progr,"-b",label='closing price')
print pres1
subplot_handles[0].set_title(coinlist_fullinfo["Data"][coins[coin_selection]]["FullName"].encode("ascii","ignore")+" price")
subplot_handles[0].set_ylabel("price (EUR)")   
subplot_handles[0].plot_date(progr_time,avg2,'-r',label='average-2')
subplot_handles[0].plot_date(progr_time,avg4,'-g',label='average-4')
subplot_handles[0].plot_date(progr_time,avg6,'--k',label='average-6')    
subplot_handles[0].grid(True)
subplot_handles[0].legend(prop={'size':10})
subplot_handles[0].xaxis.set_major_locator(minutes)
subplot_handles[0].xaxis.set_major_formatter(minuteFormatter)

macd,trigger = MACD(progr)
macd_histo = macd - trigger
subplot_handles[1].plot_date(progr_time,macd,'-b',label='MACD')
subplot_handles[1].plot_date(progr_time,trigger,'-r',label='Trigger')
subplot_handles[1].plot_date(progr_time,macd_histo,'--g')
subplot_handles[1].legend(prop={'size':10})
subplot_handles[1].grid(True)
subplot_handles[1].xaxis.set_major_locator(minutes)
subplot_handles[1].xaxis.set_major_formatter(minuteFormatter)


subplot_handles[2].semilogy(fourier_freq[1:],np.abs(fourier[1:]),'-o')
subplot_handles[2].set_xlabel("Frequency")

subplot_handles[3].plot_date(progr_time,slope,'-co',label='Slope')
subplot_handles[3].grid(True)
subplot_handles[3].xaxis.set_major_locator(minutes)
subplot_handles[3].xaxis.set_major_formatter(minuteFormatter)

quotes = zip(coin_data[coin_selection][4],coin_data[coin_selection][3],coin_data[coin_selection][1],coin_data[coin_selection][2],coin_data[coin_selection][0])
progress_time_raw = coin_data[coin_selection][5]

time_min = datetime.datetime.fromtimestamp(progress_time_raw[0])
time_max = datetime.datetime.fromtimestamp(progress_time_raw[-1])
subplot_handles[4].set_xlim(time_min,time_max)

#ax.xaxis.set_minor_formatter(dayFormatter)

subplot_handles[4].plot_date(progr_time,progr,"--k")
candlestick_ohlc(subplot_handles[4],quotes,colorup="g",colordown="r",width=6.94e-4)
subplot_handles[4].set_ylabel("Price (EUR)",fontsize=20)
subplot_handles[4].grid(True)
#ax[1,1].xaxis_date()
#ax[1,1].autoscale_view()
#ax[1,1].setp(plt.gca().get_xticklabels(), rotation=45, horizontalalignment='right')
#ax[1,1].set_xticklabels(plt.gca().get_xticklabels(), rotation=45, horizontalalignment='right')
#subplot_handles[4].set_title(coinlist_fullinfo["Data"][coins[plot_coin]]["FullName"].encode("ascii","ignore")+" price")
subplot_handles[4].xaxis.set_major_locator(minutes)
subplot_handles[4].xaxis.set_major_formatter(minuteFormatter)
#subplot_handles[4].xaxis.set_minor_locator(minutes)
#        ax[1,1].xaxis.set_minor_formatter(minuteFormatter)
#f.autofmt_xdate()


# a tk.DrawingArea
canvas = FigureCanvasTkAgg(f, master=root)
canvas.show()
canvas.get_tk_widget().pack(side=Tk.RIGHT, fill=Tk.BOTH, expand=1)

toolbar = NavigationToolbar2TkAgg(canvas, root)
toolbar.update()
canvas._tkcanvas.pack(side=Tk.TOP, fill=Tk.BOTH, expand=1)


def on_key_event(event):
    print('you pressed %s' % event.key)
    key_press_handler(event, canvas, toolbar)

canvas.mpl_connect('key_press_event', on_key_event)


def _quit():
    root.quit()     # stops mainloop
    root.destroy()  # this is necessary on Windows to prevent
                    # Fatal Python Error: PyEval_RestoreThread: NULL tstate

button = Tk.Button(master=root, text='Quit', command=_quit)
button.pack(side=Tk.BOTTOM)



Tk.mainloop()