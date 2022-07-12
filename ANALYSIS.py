import re
import numpy as np
import matplotlib.pyplot as plt
import datetime
import pickle
import os
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pytz
import time
import pandas as pd

import yaml
import argparse

# Get yaml parameter
parser = argparse.ArgumentParser()
parser.add_argument('yaml_file')
args = parser.parse_args()
with open(args.yaml_file, 'rt') as fh:
    yaml_p = yaml.safe_load(fh)

PATH = 'backlog/'

# If modifying these scopes,delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
specific_time = datetime.timedelta(0)

def authenticate_google():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens,and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle','rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available,let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json',SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle','wb') as token:
            pickle.dump(creds,token)

    service = build('calendar','v3',credentials=creds)

    return service

def get_events(id_choosen,day_start,day_end,service):
    # Call the Calendar API
    start_date = datetime.datetime.combine(day_start,datetime.datetime.min.time())
    end_date = datetime.datetime.combine(day_end,datetime.datetime.max.time())
    utc = pytz.UTC
    start_date = start_date.astimezone(utc)
    end_date = end_date.astimezone(utc)

    events_result = service.events().list(calendarId=id_choosen,timeMin=start_date.isoformat(),timeMax=end_date.isoformat(),singleEvents=True,orderBy='startTime').execute()
    events = events_result.get('items',[])

    start = []
    end = []
    summary = []
    location = []

    for event in events:
        if len(event['start'].get('dateTime',event['start'].get('date'))) > 10: #to filter out whole day events
            start += [string_to_datetime(event['start'].get('dateTime',event['start'].get('date')))]
            end += [string_to_datetime(event['end'].get('dateTime',event['end'].get('date')))]
            summary += [event['summary']]
            try: #not every entry might have a location
                location += [event['location']]
            except:
                location += [None]
    return start,end,summary,location

def string_to_datetime(string):
    year = int(string[0:4])
    month = int(string[5:7])
    day = int(string[8:10])
    hour = int(string[11:13])
    minute = int(string[14:16])
    second = int(string[17:19])
    return datetime.datetime(year,month,day,hour,minute,second)

def scrape(cat,cal,id,start_date,end_date):
    service = authenticate_google()
    
    start = []
    end = []
    summary = []
    location = []
    end_i_old = [start_date - datetime.timedelta(days=1)]
    end_i = [start_date]
    while True: #you can only scrape 250 entries per seconds
        end_i_old = end_i[-1]
        start_i,end_i,summary_i,location_i = get_events(id,end_i[-1],end_date,service)
        if len(end_i) == 0:
            break
        if end_i[-1] == end_i_old:
            break
        start += start_i
        end += end_i
        summary += summary_i
        location += location_i
        if len(end_i) != 0:
            print(cal + ": " + str(end_i[-1]),end='\r')
        else:
            break
        time.sleep(1)
    
    duration = list(np.subtract(end,start))
    for d in range(len(duration)):
        duration[d] = duration[d].total_seconds()/3600 #save in hours

    # Write to file
    df = pd.DataFrame({'cat':[cat]*len(summary),'cal':cal,'summary':summary,'start':start,'end':end,'duration':duration,'location':location})
    df.to_csv(path_or_buf=PATH + str(id) + ".csv",index=False)

def combine(start_date,end_date):
    names = os.listdir(PATH)
    df = pd.DataFrame()
    for name in names:
        df = df.append(pd.read_csv(PATH + name))

    df['start'] = pd.to_datetime(df['start'])
    df['end'] = pd.to_datetime(df['end'])
    df = df[(df['start']>=start_date)&(df['end']<=end_date)]
    df = df.sort_values(by=['start'])
    return df

def sum_per_day(df):
    df['start'] = df['start'].dt.floor(freq='D')
    df = df.groupby(['cat','cal','start'],as_index=False).sum()
    df = df.sort_values(by=['start'])
    return df

def avg_per_day(df):
    df['start'] = df['start'].dt.floor(freq='D')
    df = df.groupby(['cat','start'],as_index=False).mean()
    df = df.sort_values(by=['start'])
    return df

def fill(df,start,end):
    idx = pd.date_range(start, end)
    if len(df) > 0:
        df = df.set_index('start')
        df = df.reindex(idx, fill_value=0)
    return df,idx

def analysis(df):
    fig, axs = plt.subplots(3)

    # top plot
    df_days = sum_per_day(df)
    start = df_days['start'].iloc[0]
    end = df_days['start'].iloc[-1]
    y = np.zeros((int((end - start).total_seconds()/3600/24+1)))
    cat_sum = [0,0,0]
    colors = ['red','green','blue']
    c = 0
    for cat in list(yaml_p):
        for cal in list(yaml_p[cat]):
            df_sub,idx = fill(df_days[(df_days['cat']==cat)&(df_days['cal']==cal)],start,end)
            if len(df_sub) > 0:
                y += df_sub['duration'].to_numpy()
                axs[0].fill_between(idx,y,color=colors[c],zorder=len(list(yaml_p[cat]))-c-10) #so the label is on top
        cat_sum[c] = y[-1]
        c += 1
    
    #Label
    for cs in range(len(cat_sum)-1):
        cat_sum[-cs-1] -= cat_sum[-cs-2]
    legend=[]
    for cs in range(len(cat_sum)):
        legend.append(list(yaml_p)[cs] + ", today: " + str(np.round(cat_sum[cs],2)) + " [h]")
    
    axs[0].legend(legend)
    axs[0].set_ylabel("[h]")

    # middle plot
    df_avg = avg_per_day(df[df['cat']=='Work'])
    for cat in ["Work"]:
        for cal in list(yaml_p[cat]):
            df_sub,idx = fill(df_avg,start,end)
            axs[1].plot(idx,df_sub['duration'],color=colors[0])
    axs[1].legend(["Work" + ", today: " + str(np.round(df_sub['duration'][-1],2)) + " [h]"])
    axs[1].set_ylabel("avg. conc. span [h]")

    # bottom plot
    for cat in ["Privat"]:
        for cal in ["Sport"]:
            df_sub,idx = fill(df_days[(df_days['cat']==cat)&(df_days['cal']==cal)],start,end)
            axs[2].plot(idx,df_sub['duration'],color=colors[2])
    axs[2].legend(["Sport" + ", today: " + str(np.round(df_sub['duration'][-1],2)) + " [h]"])
    axs[2].set_ylabel("[h]")

    plt.gcf().autofmt_xdate()
    plt.show()
    plt.close()

def main():
    end_date = datetime.datetime.today()
    #start_date = datetime.datetime(2019, 8, 26, 0,0,0)
    start_date = end_date - datetime.timedelta(weeks=4)
    for cat in list(yaml_p):
            for cal in list(yaml_p[cat]):
                scrape(cat,cal,yaml_p[cat][cal],start_date,end_date)
    df = combine(start_date,end_date)
    analysis(df)

main()