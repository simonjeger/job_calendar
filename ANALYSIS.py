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

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

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


def evaluate(id_choosen, start_date, end_date):
    service = authenticate_google()
    n = ((end_date - start_date).days + 1)

    dates = [start_date] * n
    events = [0] * n
    durations = [0] * n

    i = 0
    while i < n:
        dates[i] = dates[i] + datetime.timedelta(1) * i
        print(dates[i])
        events[i] = get_events(id_choosen, dates[i], dates[i], service)
        if duration(events[i]) != 0:
            durations[i] = duration(events[i]).seconds / 3600
        else:
            durations[i] = 0
        i = i + 1

    return [dates, durations]


def plot(dates, durations):
    plt.plot(dates, durations)


def choose_calendar(name_choosen, start_date, end_date):
    name = ['Aris', 'Car', 'DroGone', 'SeaGlider', 'Stundenplan', 'Arbeit', 'Dipper']
    id = ['8kr78seiflopv5brbl6h3d99bo@group.calendar.google.com', 'lv1bdbitcmflf49hek1q999seo@group.calendar.google.com', 'sdjr4mcua71dhke935srmuuies@group.calendar.google.com', 'askh7fn9npk6mma9e7oo6dn96o@group.calendar.google.com', 'gljlq3fa3rp0is3kkrcg9gsmd0@group.calendar.google.com', 'eqa215j7sqpru28o7e9qgph4g4@group.calendar.google.com', 'v8oi46ort679nopg3pahkvlsh4@group.calendar.google.com']
    id_choosen = []

    for r in name_choosen:
        if r in name:
            id_choosen = id_choosen + [id[name.index(r)]]

    result = []
    for r in id_choosen:
        result = result + [evaluate(r, start_date, end_date)]

    total = [0] * len(result[0][1])

    for r in result:
        plot(r[0], r[1])
        total = np.add(total, r[1])
    plot(r[0], total)
    print('\n')
    print('average since ' + str(start_date.date()) + ': ' + str(np.round(np.sum(total)/len(total),2)))
    print('total today: ' + str(np.round(total[-1],2)))
    plt.show()
    plt.close()

choose_calendar(['Aris', 'Car', 'DroGone', 'SeaGlider', 'Stundenplan', 'Arbeit', 'Dipper'], datetime.datetime(2020, 1, 1), datetime.datetime.today())
