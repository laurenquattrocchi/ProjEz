'''
This file analyzes Chicago Crime and Citizen data to identify
matches between two data sources. Matches are then written to a csv
file called match_file.cvs
'''

import csv
import datetime
import itertools
# from this import d
# from turtle import shape
import pandas as pd
import geopandas as gpd
from geopy.geocoders import Nominatim
# from shapely.geometry import Point
# from shapely.geometry import shape
import matplotlib.pyplot as plt
# from geopy import distance
# from refresh_data import sql_query
# from ez/refresh_data import sql_query 

DIST_LOWER_BOUND = 0
DIST_UPPER_BOUND = .25
TIME_LOWER_BOUND = 1
TIME_UPPER_BOUND = 1

def go():
    """
    Runs entire py file. Creates Citizen and Chicago dataframes from sql
    queries to sqlite databse. Cleans data i.e. formates lat/long columns,
    deduplicates and calls record_link to find matches.

    Outputs: match_file.csv
    """

    citizen_df, chi_df = sql_query.create_report_df()

    clean_lat_long(citizen_df, 'citizen')
    clean_lat_long(chi_df, 'chi')

    standard_date_time(citizen_df, 'citizen')
    standard_date_time(chi_df, 'chi')

    chi_df = chi_df.drop_duplicates(keep = 'first')
    citizen_df = citizen_df.drop_duplicates(keep = 'first')

    link_records(citizen_df, chi_df, DIST_LOWER_BOUND, DIST_UPPER_BOUND,
                    TIME_LOWER_BOUND, TIME_UPPER_BOUND )
    print_date_timeframes(citizen_df, chi_df)

    return citizen_df, chi_df

def print_date_timeframes(citizen_df, chi_df):
    """
    Prints record link analysis summary for user to have brief
    description of data captured in the csv

    Inputs:
        citizen_df(pandas df) data scraped from Citizen
        chi_df(pandas df) data extracted from Chicago Portal's API
    """
    earliest_match_date = max(chi_df['date'].min(), citizen_df['date'].min())
    latest_match_date = min(chi_df['date'].max(), citizen_df['date'].max())
    print("Record link analysis summary: \n")
    print("Chicago Crime data starts on", chi_df['date'].min(),
            " and ends on", chi_df['date'].max(), "\n")
    print("Citizen data starts on", citizen_df['date'].min(), " and ends on",
            citizen_df['date'].max(), "\n")
    print("The Chicago Crime and Citizen data overlap on the following days: \n",
            earliest_match_date, "to", latest_match_date, "\n")
    print("A cvs file called match_file.csv has been created")


def clean_lat_long(df, source):
    """
    Updates each dataframe in place to insert a lat_long
    column, a tuple of lat (float), long (float).

    Inputs:
        df (pandas df): dataframe to update lat/long for
        source (str): citizen or chi

    Returns none (updates in place)
    """
    if source == 'chi':
        df.astype({'latitude': 'float64', 'longitude': 'float64'})
    df['lat_long'] = list(zip(df.latitude, df.longitude))


def reported_difference_in_dist(loc_1, loc_2, lower_bound, upper_bound):
    """
    Takes in two lat/long tuples and finds the geodesic distance between the
    two points. Uses lower and upper bound limits to determine likelihood of
    accurate match. Rturns True if within distance of lower and upper bound
    from eachother

    Inputs:
        loc_1(tuple): lat/long values for location 1
        loc_2(tuple): lat/long values for location 2
        lower_bound (int): distance in miles
        uper_bound (int): distance in miles

    Returns (boolean)
    """
    dist = distance.great_circle(loc_1, loc_2).miles
    if dist >= lower_bound and dist <= upper_bound:
        return True
    return False


def standard_date_time(df, source):
    """
    Recieves 13-digit unix time/date format from citizen.
    This function updates the dataframe in-place. It updates
    the "created_at" field and replaces it with a date time object

    Inputs:
        df
        source (str): chi or citizen, to handle different date formats
        accordingly

    Returns (pandas dataframe) updates date col in place and
        replaces with a datetime object
    """
    dt_objs = []
    time_objs = []
    for _, row in df.iterrows():
        timestamp = row['date']
        if source == "citizen":
            timestamp = float(timestamp)
            timestamp = int(timestamp) / 1000
            dt_obj = datetime.datetime.fromtimestamp(timestamp)
        elif source == "chi":
            dt_obj = datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f")
        day_obj = dt_obj.date()
        dt_objs.append(day_obj)
        time = dt_obj.time()
        time_objs.append(time)
    df['date'] = dt_objs
    df['time'] = time_objs
    return df

def link_records(citizen, chi, dist_lower_bound, dist_upper_bound,
                    time_lower_bound, time_upper_bound):
    """
    Takes in two datasets and compares location and time of crime events
    in each dataframe. If the time between event is within the lower bound and
    upper bound time from time of event and the distance between events is
    within distance bounds provided the two event sare considered a match
    and outputed to csv file.

    Inputs:
        citizen (df):dataframe created from citizen website
        chi (df): chicago data portal dataframe
        dist_lower_bound (int): distance in miles
        dist_uper_bound (int): distance in miles
        time_lower_bound (int): time in hours
        time_uper_bound (int): time in hours

    Outputs: match_file.csv
    """

    if len(chi) < len(citizen):
        smaller_df = chi
        suffix = '_chi'
        suffix2 ='_citizen'
        larger_df = citizen
    else:
        smaller_df = citizen
        suffix = '_citizen'
        suffix2 = '_chi'
        larger_df = chi

    header = list(smaller_df.add_suffix(suffix). \
                columns) + list(larger_df.add_suffix(suffix2).columns)

    with open('match_file.csv', "w") as file:
        spamwriter = csv.writer(file, delimiter = ",")
        spamwriter.writerow(header)
        for _, small_row in smaller_df.iterrows():
            filtered_df = larger_df.loc[larger_df['date'] == small_row['date']]
            for _,large_row in filtered_df.iterrows():
                #fix time to handle edge cases
                if small_row['time'].hour >= large_row['time'].hour - time_lower_bound and \
                    small_row['time'].hour <= large_row['time'].hour \
                                                    + time_upper_bound:
                    match = reported_difference_in_dist(small_row['lat_long'],
                            large_row['lat_long'], dist_lower_bound, dist_upper_bound)
                    if match:
                        output = pd.concat([small_row, large_row], axis=0)
                        output[4] = str(output[4]).replace(", ", "")
                        spamwriter.writerow(output)


def write_gpd_to_csv(joined):
    """
    """
    # joined = joined.drop('MultiPolygon', 1)
    header = ['pri_neigh', 'sec_neigh', 'shape_are' , 'shape_len', 'geometry',
                                                 'index_right',	'description_citizen', 'date_citizen', 'latitude_citizen',
                                                  'longitude_citizen', 'primary_type_citizen', 'lat_long_citizen', 'time_citizen',
                                                   'date_chi', 'latitude_chi', 'longitude_chi', 'primary_type_chi',	'description_chi',
                                                    'lat_long_chi', 'time_chi']
    with open('neighborhoods.csv', "w") as file:
        spamwriter = csv.writer(file, delimiter = ",")
        spamwriter.writerow(header)
        joined = joined.drop('geometry', 1)
        for _, row in joined.iterrows():
            spamwriter.writerow(row)



def csv_tp_gdf_point(filepath, xcol, ycol):
	'''
	Helper function to read in csv and create points geodataframe
	'''
	df = pd.read_csv(filepath)
	return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[xcol], df[ycol]))

def join_point_count_by_poly(polys, points, groupby_col, count_col):
	'''
	Helper function to join polys and points and create count of points in polys
	'''
	joined = gpd.sjoin(polys, points)
	return pd.DataFrame(joined.groupby(groupby_col)[count_col].count()).reset_index(), joined


def plot_points(base_gdf, points, points_color='blue'):
    '''
    Plot points data over base polygon map
    '''
    fig, ax = plt.subplots(figsize=(10,10))
    base_gdf.boundary.plot(color='grey',alpha=0.3, ax=ax)
    points.plot(ax=ax, markersize=1, legend=True, color=points_color)
    ax.axis('off')
    plt.show()


def plot_choropleth(gdf, column, cmap='Blues'):
    '''
    Plot choropleth map 
    '''
    fig, ax = plt.subplots(figsize=(10,10))
    gdf.plot(ax=ax, column=column, legend=True, cmap=cmap)
    ax.axis('off')
    plt.show()


def run(xcol, ycol, count_by):
    """
    """
    tract_polys = gpd.read_file("neighborhood_bounds.geojson")
    points_gdf = csv_tp_gdf_point('match_file.csv', xcol, ycol).set_crs(epsg=4326)
    plot_points(tract_polys, points_gdf)
    tract_counts, joined = join_point_count_by_poly(tract_polys, points_gdf, 'sec_neigh', count_by) 
    tract_count_polys = tract_polys.merge(tract_counts, on='sec_neigh').set_geometry('geometry')
    plot_choropleth(tract_count_polys, count_by)
    return joined