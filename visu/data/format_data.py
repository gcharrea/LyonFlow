import pickle
import warnings
import json
import datetime
import pandas as pd
from geopy.distance import vincenty


def get_normalized_activities(activities):
    data = list()
    for activity in activities:
        temp = list()
        for act in activity['activity']:
            temp.append(act)
        total = sum([value['confidence'] for value in temp])
        temp = [{'type':value['type'], 'confidence':value['confidence']/total} for value in temp]
        data += temp
    return data

def get_date(time):
    day = time.day
    hour = time.hour

    day_of_week = time.weekday()
    day_of_week_index = [0, 1, 2, 3, 4, 5, 6]
    day_of_week_name = ['Mon', 'Tues', 'Wed', 'Thurs', 'Fri', 'Sat', 'Sun']
    index = day_of_week_index.index(day_of_week)
    day_of_week = day_of_week_name[index]

    year = time.year

    month = time.month
    month_index = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    month_name = ['Jan', 'Feb', 'March', 'April', 'May', 'June', 'July', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    index = month_index.index(month)
    month = month_name[index]

    return {'day':day, 'hour':hour, 'day_of_week':day_of_week, 'month':month, 'year':year}

def remove_wrong_data(data):
    data_new = list()
    for coord in data:
        longitude = coord['longitudeE7']/float(1e7)
        if longitude > 4.768718 and longitude < 4.968718:
            data_new.append(coord)
    return data_new

def get_data(data):
    data = remove_wrong_data(data)
    data = sorted(data, key=lambda x: x['timestampMs'])
    index_max = len(data)
    for index in range(index_max):
        data[index]['latitudeE7'] = data[index]['latitudeE7']/float(1e7)
        data[index]['longitudeE7'] = data[index]['longitudeE7']/float(1e7)
        data[index]['timestampMs'] = float(data[index]['timestampMs'])/1000
        data[index]['datetime'] = datetime.datetime.fromtimestamp(data[index]['timestampMs'])
        dates = get_date(data[index]['datetime'])
        data[index]['day'] = dates['day']
        data[index]['day_of_week'] = dates['day_of_week']
        data[index]['month'] = dates['month']
        data[index]['year'] = dates['year']
        data[index]['hour'] = dates['hour']
        if 'activity' in data[index].keys():
            data[index]['activity'] = get_normalized_activities(data[index]['activity'])
        if index != 0:
            lat1 = data[index-1]['latitudeE7']
            lat2 = data[index]['latitudeE7']
            long1 = data[index-1]['longitudeE7']
            long2 = data[index]['longitudeE7']
            coords_1 = (lat1, long1)
            coords_2 = (lat2, long2)
            data[index]['distance'] = vincenty(coords_1, coords_2).km
    del data[0]
    return data

def filter_activities(data):
    data_new = list()
    for dictionary in data:
        if 'activity' in dictionary.keys() and dictionary['accuracy'] > 0 and dictionary['accuracy'] < 1000:
            for activity in dictionary['activity']:
                data_new.append({
                    'latitude':dictionary['latitudeE7'],
                    'longitude':dictionary['longitudeE7'],
                    'timeStamp':dictionary['timestampMs'],
                    'accuracy':dictionary['accuracy'],
                    'type':activity['type'],
                    'confidence':activity['confidence'],
                    'day':dictionary['day'],
                    'hour':dictionary['hour'],
                    'day_of_week':dictionary['day_of_week'],
                    'month':dictionary['month'],
                    'year':dictionary['year'],
                    'distance':dictionary['distance'],
                    'normalized_distance':dictionary['distance'] * activity['confidence']
                })
    return data_new

def save(data):
    with open("data.pkl", "wb") as pickle_out:
        pickle.dump(data, pickle_out)

def load():
    with open("data.pkl", "rb") as pickle_in:
        return pickle.load(pickle_in)

def get_city(latitude, longitude):
    if  longitude > 4.768718 and longitude < 4.968718:
        if latitude > 45.664158 and latitude < 45.823741:
            return 'Lyon'
    return 'Other'


if __name__ == "__main__":
    warnings.filterwarnings('ignore')

    with open('location_history.json', 'r') as fh:
        DATA = json.loads(fh.read())
        DATA = DATA['locations']

    DATA = get_data(DATA)
    DATA = filter_activities(DATA)
    DATA = pd.DataFrame(DATA)
    DATA = DATA[DATA.distance.notnull()]
    DATA['city'] = DATA.apply(lambda x: get_city(x['latitude'], x['longitude']), axis=1)

    save(DATA)
    DATA.to_csv("test.csv", sep=',')
