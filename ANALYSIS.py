from __future__ import print_function
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pytz
import time
import csv
import os.path
import pandas as pd
import glob

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
specific_time = datetime.timedelta(0)

def authenticate_google():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)

    return service


def get_events(id_choosen, start_day, end_day, service):
    # Call the Calendar API
    start_date = datetime.datetime.combine(start_day, datetime.datetime.min.time())
    end_date = datetime.datetime.combine(end_day, datetime.datetime.max.time())
    utc = pytz.UTC
    start_date = start_date.astimezone(utc)
    end_date = end_date.astimezone(utc)

    events_result = service.events().list(calendarId=id_choosen, timeMin=start_date.isoformat(), timeMax=end_date.isoformat(), singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])

    start = []
    end = []
    summary = []

    #if not events:
    #    print('No upcoming events found.')

    for event in events:
        start = start + [string_to_int(event['start'].get('dateTime', event['start'].get('date')))]
        end = end + [string_to_int(event['end'].get('dateTime', event['end'].get('date')))]
        summary = summary + [event['summary']]

    """
    keyword = 'Zeit mit Nina'
    global specific_time
    for i in range(len(summary)):
        if summary[i] == keyword:
            specific_time += np.subtract(end,start)[i]

    print('Time spent on ""' + keyword + '"": ' + str(specific_time))
    """
    return [start, end, summary]


def string_to_int(string):
    if len(string) > 10:
        year = int(string[0:4])
        month = int(string[5:7])
        day = int(string[8:10])
        hour = int(string[11:13])
        minute = int(string[14:16])
        second = int(string[17:19])
        return datetime.datetime(year, month, day, hour, minute, second)
    else:
        return datetime.datetime(1, 1, 1, 1, 1, 1) # whole day event, as long it starts and ends on the same day everything is fine


def duration(events):
    return np.sum(np.subtract(events[1], events[0]))


def evaluate(id_choosen, start_date, end_date, j, t):
    service = authenticate_google()

    path_backlog = 'backlog/' + str(id_choosen) + ".csv"
    if os.path.isfile(path_backlog): # generate data starting at last known date
        # read in previous data
        df = pd.read_csv(path_backlog)
        dates_prev = np.asarray(df['dates'])
        for i in range(len(dates_prev)):
            dates_prev[i] = datetime.datetime.strptime(dates_prev[i][0:19], '%Y-%m-%d')
        durations_prev = np.asarray(df['durations'])

        if start_date >= dates_prev[0]: # check if we even have data that dates this far back
            n = max(((end_date - dates_prev[-1]).days), 0)
            dates = [dates_prev[-1]] * n
        else:
            n = ((end_date - start_date).days + 1)
            dates = [start_date] * n

    else: # generate data from start
        dates_prev = []
        durations_prev = []

        n = ((end_date - start_date).days + 1)
        dates = [start_date - datetime.timedelta(1)] * n #quickfix on 19.04.21

    events = [0] * n
    durations = [0] * n
    i = 0

    while i < n:

        # Because otherwise API crashes
        time.sleep(1)

        dates[i] = dates[i] + datetime.timedelta(1) * (i+1)
        print(str(int(j)) + '/' + str(t) + ' - ' + str(int(100*i/n)) + ' %')
        events[i] = get_events(id_choosen, dates[i], dates[i], service)
        if duration(events[i]) != 0:
            durations[i] = duration(events[i]).seconds / 3600
        else:
            durations[i] = 0
        i = i + 1

    dates = np.concatenate((dates_prev, dates), axis = 0)
    durations = np.concatenate((durations_prev, durations), axis = 0)

    # Write to file
    df = pd.DataFrame({'dates': dates, 'durations': durations})
    df.to_csv(path_or_buf = path_backlog, index=False)

    # Remove everything that's not observed
    idx_obs = df[ df['dates'] < start_date].index
    df.drop(idx_obs , inplace=True)
    idx_obs = df[ df['dates'] > end_date].index
    df.drop(idx_obs , inplace=True)
    dates = np.asarray(df['dates'])
    durations = np.asarray(df['durations'])

    return [dates, durations]


def plot(dates, durations):
    plt.plot(dates, durations)


def choose_calendar(name_choosen, start_date, end_date):
    name = ['Privat','Aris', 'Car', 'DroGone', 'SeaGlider', 'Stundenplan', 'Arbeit', 'Dipper', 'Amiv', 'Koordination Fokusprojekte', 'Crypto']
    id = ['simonjeger@gmail.com','8kr78seiflopv5brbl6h3d99bo@group.calendar.google.com', 'lv1bdbitcmflf49hek1q999seo@group.calendar.google.com', 'sdjr4mcua71dhke935srmuuies@group.calendar.google.com', 'askh7fn9npk6mma9e7oo6dn96o@group.calendar.google.com', 'gljlq3fa3rp0is3kkrcg9gsmd0@group.calendar.google.com', 'eqa215j7sqpru28o7e9qgph4g4@group.calendar.google.com', 'v8oi46ort679nopg3pahkvlsh4@group.calendar.google.com', '57hlk6nr14pf2im1nn5epkb7n0@group.calendar.google.com', 'lcb8rr1h49pvnmrgo22se2t57k@group.calendar.google.com', 'ctgifgcmla84iuo6eo7bb3ql84@group.calendar.google.com']
    id_choosen = []

    timeframe = end_date - start_date
    stride = int(timeframe.days/20)
    if stride < 1:
        stride = 1

    for r in name_choosen:
        if r in name:
            id_choosen = id_choosen + [id[name.index(r)]]

    result = []
    j = 0
    for r in id_choosen:
        j = j + 1
        result = result + [evaluate(r, start_date, end_date, j, len(name_choosen))]

    # plot curves
    total = [0] * len(result[0][1])
    for r in result:
        r[1] = np.add(r[1], total)
        total = r[1]
    for r in result[::-1]:
        plt.fill_between(r[0], r[1])

    # calculate moving average
    total = result[-1][1]
    m_length = len(total)-2*stride
    m_average = [0]*m_length
    for i in range(m_length):
        m_average[i] = np.average(total[i:i+2*stride])
    plt.plot(result[-1][0][stride:-stride], m_average, 'k')

    plt.legend(['moving average (stride = '+ u"\u00B1" + str(stride) + ')'] + name_choosen[::-1], loc='best')
    print('\n')
    print('total since ' + str(start_date.date()) + ': ' + str(np.round(np.sum(total),2)))
    print('average since ' + str(start_date.date()) + ': ' + str(np.round(np.sum(total)/len(total),2)))
    print('total today: ' + str(np.round(total[-1],2)))
    plt.show()
    plt.close()

def delete(days):
    for filename in glob.glob(os.path.join('backlog/', '*.csv')):
        df = pd.read_csv(filename)
        df.drop(df.tail(days).index,inplace=True)
        df.to_csv(path_or_buf = filename, index=False)

# Total
#choose_calendar(['Aris', 'Car', 'DroGone', 'SeaGlider', 'Stundenplan', 'Arbeit', 'Dipper', 'Amiv', 'Koordination Fokusprojekte', 'Crypto'], datetime.datetime(2019, 8, 26, 0,0,0), datetime.datetime.today())

# Refresh last n days (to refresh)
#delete(1)

# Calculate this semester
choose_calendar(['Aris', 'Car', 'DroGone', 'SeaGlider', 'Stundenplan', 'Arbeit', 'Dipper', 'Amiv', 'Koordination Fokusprojekte', 'Crypto'], datetime.datetime(2021, 8, 1, 0,0,0), datetime.datetime.today())
#choose_calendar(['Privat'], datetime.datetime(2020, 9, 14, 0,0,0), datetime.datetime.today())
