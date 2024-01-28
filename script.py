import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import requests

from bokeh.plotting import figure, output_file, show, curdoc
from bokeh.models import ColumnDataSource, Legend, GeoJSONDataSource, LinearColorMapper, ColorBar, Range1d
from bokeh.models import NumeralTickFormatter, HoverTool, LabelSet, Panel, Tabs, Slider, CustomJS, TapTool, CDSView
from bokeh.models.widgets import TableColumn, DataTable, NumberFormatter, Dropdown, Select, RadioButtonGroup, TableColumn
from bokeh.palettes import Category20c
from bokeh.io import curdoc, output_notebook, show, output_file
from bokeh.layouts import row, column, gridplot
from bokeh.palettes import Viridis6 as palette
from bokeh.transform import cumsum

import colorcet

import geopandas as gpd
import pycountry
import json

import warnings
warnings.filterwarnings('ignore')

from rich.console import Console

rc = Console()

# - Functions

def create_data(attr, old, new):
    """Create and modify data for the bokeh map"""

    # Mask data to the required year value
    chosen_year = year_slider.value
    df1 = geo_df1[geo_df1['year']==str(chosen_year)].copy()
    df2 = gen_df1.query('country.isin(@continents)')[gen_df1['year']==str(chosen_year)].copy()

    # Read data to json
    df_json = json.loads(df1[['country', 'country_code', 'geometry', 'technology', 'unit', 'year', 'percentage']].to_json())

    map_data = json.dumps(df_json)

    # Assign Source
    map_source.geojson = map_data
    bar_sc.data = df2

def up_scat(attr, old, new):
    """Select country name"""
    name = country_sel.value
    time_sc.data = gen_df1[~gen_df1['country'].isin(continents)].query('country=="'+name+'"')
    ren_sc.data = ren_df1[~ren_df1['country'].isin(continents)].query('country=="'+name+'"')

def build_map(src):
    """Build map data"""

    # Data source
    map_source = src

    # Map Geometry
    color_mapper = LinearColorMapper(palette=colorcet.bgy, low=0, high=100)

    color_bar = ColorBar(color_mapper = color_mapper, location = (0,0))

    # Map
    TOOLS = "pan,wheel_zoom,reset,hover,save"

    map_all = figure(plot_width=725, plot_height=500,
                    title="Renewable energy generation in % from different countries",
                    tools=TOOLS, x_axis_location=None, y_axis_location=None,
                    tooltips = [
                        ("Country", "@country"),
                        ("Energy generated %", "@percentage%")
                    ]
                )

    map_all.grid.grid_line_color = None
    map_all.hover.point_policy = "follow_mouse"

    # Create patches (of map)
    map_all.patches(
        "xs", "ys", source=map_source,
        fill_color={
            "field": 'percentage',
            "transform": color_mapper
        },
        fill_alpha=0.7, line_color="black", line_width=0.5
    )

    map_all.add_layout(color_bar, 'below')

    return map_all

def bar_cont(src):
    """Create bar chart for visualising annual percentage of renewable energy generation"""
    bar_sc = src

    cont_bar = figure(plot_width=379, plot_height=500, title="Renewable energy by Continents",
            y_range=bar_sc.data['country'], y_axis_label='Continents', x_axis_location=None,
            tooltips=[
                ('Continent', "@country"),
                ('Energy', "@percentage")
                ])

    cont_bar.xgrid.grid_line_color = None

    cont_bar.hbar(
        y="country", left="percentage", source=bar_sc.data,
        right=0, height=0.5,
        fill_color="#b3de69"
    )

    return cont_bar

def chart_time(src):
    """Create time series chart for countries"""
    # Source
    time_sc = src

    # Map
    TOOLS = "pan,wheel_zoom,reset,hover,save"

    time_chart = figure(plot_width=375, plot_height=300,
                    title="Time series data for countries",
                    tools=TOOLS, tooltips=[
                    ('country', '@country'), 
                    ('Energy', '@percentage %')
                    ]
                )

    time_chart.line(
        "year", "percentage", source=time_sc,
        line_color="green", line_width=5
    )

    time_chart.circle(
        x="year", y="percentage", size=10, source=time_sc, 
        fill_color="green", fill_alpha=0.7
    )

    return time_chart

def chart_energy(src):
    """Create time series chart for countries"""
    # Source
    time_sc = src

    # Map
    TOOLS = "pan,wheel_zoom,reset,hover,save"

    time_chart = figure(plot_width=375, plot_height=300,
                    title="Time series data for countries",
                    tools=TOOLS, tooltips=[
                    ('country', '@country'), 
                    ('Energy', '@percentage GWh')
                    ]
                )

    time_chart.line(
        "year", "percentage", source=time_sc,
        line_color="red", line_width=5
    )

    time_chart.circle(
        x="year", y="percentage", size=10, source=time_sc, 
        fill_color="red", fill_alpha=0.7
    )

    return time_chart

def findcountry(country_name):
    """Find the official country name"""
    try:
        return pycountry.countries.get(name=country_name.capitalize()).official_name
    except:
        return country_name

# Load data
df = pd.read_csv(r'data/REGEN_%_RAW.csv', encoding_errors='replace', header=2)

ren_df = pd.read_csv(r'data/REGEN_GWh_RAW.csv', encoding_errors='replace', header=1)

gen_df = df.query('Indicator=="RE share of electricity generation (%)"')

# Process data
ren_df['unit'] = 'gwh'

ren_df.columns = [
    'country',
    'technology',
    '2018',
    '2019',
    '2020',
    '2021',
    'unit'
]

ren_df['country'] = ren_df['country'].copy().apply(lambda x: x.lower())
ren_df['technology'] = ren_df['technology'].copy().apply(lambda x: x.lower())

gen_df.drop(['Indicator', '2022'], axis=1, inplace=True)
gen_df['technology'] = 'total_perc'
gen_df['unit'] = 'perc'

gen_df.columns = [
    'country',
    '2018',
    '2019',
    '2020',
    '2021',
    'technology',
    'unit'
]

gen_df['country'] = gen_df['country'].copy().apply(lambda x: x.lower())
gen_df['technology'] = gen_df['technology'].copy().apply(lambda x: x.lower())

# Feature Engineer

country_out = {
    'turkiye': 'republic of turkey',
    'reunion': 'reunion',
    'kingdom of somaliland': 'somaliland',
    'Commonwealth of the Bahamas': 'the bahamas',
    'falkland islands (malvinas)': 'falkland islands',
    'Western Sahara': 'western sahara',
    'state of palestine': 'palestine',
    'syrian arab republic': 'syria',
    'republic of moldova': 'moldova',
    'russian federation': 'russia',
    'brunei darussalam': 'brunei',
    'Democratic Republic of Timor-Leste': 'east timor',
    'chinese taipei': 'taiwan',
    "democratic people's republic of korea": 'north korea',
    'republic of korea': 'south korea',
    "lao people's democratic republic": 'laos',
    'Republic of the Congo': 'republic of the congo',
    'Republic of Serbia': 'republic of serbia',
    'iran (islamic republic of)': 'iran',
    "cote d'ivoire": 'ivory coast',
    'bonaire, sint eustatius and saba': 'caribbean netherlands',
    'Socialist Republic of Viet Nam': 'vietnam',
    'south georgia and s sandwich islands': 'south georgia island',
    'bolivia (plurinational state of)':'bolivia',
    'venezuela (bolivarian republic of)': 'venezuela'
}

# Map data
borders = 'mapping/ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp'
gdf = gpd.read_file(borders)[['ADMIN', 'ADM0_A3', 'geometry']]

# Rename columns
gdf.columns = ['country', 'country_code', 'geometry']

# Convert the names to lower case
gdf['country'] = gdf['country'].apply(lambda x: x.lower())

gen_df['country'] = gen_df['country'].apply(lambda x: x.lower())

ren_df['country'] = ren_df['country'].apply(lambda x: x.lower())

# Assign official names to data
gen_df['country'] = gen_df['country'].apply(findcountry)

ren_df['country'] = ren_df['country'].apply(findcountry)

gdf['country'] = gdf['country'].apply(findcountry)

# Correct names in dataframe for matching it with map data
gen_df.country = gen_df.country.apply(lambda x: country_out.get(x, x))

ren_df.country = ren_df.country.apply(lambda x: country_out.get(x, x))

en_df = pd.concat([ren_df, gen_df])

# Merge data with co-ordinates
geo_df = gdf.merge(gen_df, left_on='country', right_on='country', how='left')

geo_df.country = geo_df.country.apply(lambda x: x.capitalize())

# Fill Null values
geo_df.fillna(0, inplace=True)

# Melt the year column
geo_df1 = pd.melt(geo_df, id_vars=['country', 'country_code', 'geometry', 'technology', 'unit'], 
            value_vars=['2018', '2019', '2020', '2021'])

geo_df1.columns = ['country', 'country_code', 'geometry', 'technology', 'unit', 'year', 'percentage']

geo_df1.percentage = round(geo_df1['percentage'], 2)

# Bar chart data
continents = ["asia", "africa", "europe", "north america", "south america", "central america", "Antarctica", "australia", "oceania"]

gen_df1 = pd.melt(gen_df, id_vars=['country', 'technology', 'unit'],
        value_vars=['2018', '2019', '2020', '2021'])

gen_df1.columns = ['country', 'technology', 'unit', 'year', 'percentage']

# Energy data
ren_df1 = pd.melt(ren_df, id_vars=['country', 'technology', 'unit'],
        value_vars=['2018', '2019', '2020', '2021'])

ren_df1.columns = ['country', 'technology', 'unit', 'year', 'percentage']

bar_sc = ColumnDataSource(gen_df1.query('country.isin(@continents) and year=="2018"'))

time_sc = ColumnDataSource(gen_df1.query('~country.isin(@continents) and unit=="total_perc"'))

ren_sc = ColumnDataSource(ren_df1.query('~country.isin(@continents) and unit!="total_perc"'))

# Read data to json
df_json = json.loads(geo_df1.query('year=="2018"')[
    ['country', 'country_code', 'geometry', 'technology', 'unit', 'year', 'percentage']
    ].to_json())

# Convert to string like object
map_data = json.dumps(df_json)

## App Design
# Range slider for the year
year_slider = Slider(
    start=2018,
    end=2021,
    value=2018, 
    step=1,
    title='year',
    width=110
)

# Select the required country
country_sel = Select(
    title="Select Country",
    value="Afghanistan", 
    options=list(gen_df1[~gen_df1['country'].isin(continents)].country.unique()),
    width=110
)

# Assign Source
map_source = GeoJSONDataSource(geojson=map_data)

year_slider.on_change('value', create_data)

country_sel.on_change('value', up_scat)

# Update chart
map_all = build_map(map_source)

cont_bar = bar_cont(bar_sc)

count_line = chart_time(time_sc)

ren_line = chart_energy(ren_sc)

curdoc().add_root(column(row(column(year_slider, country_sel), map_all, cont_bar), row(count_line, ren_line)))
curdoc().title = 'Renewable energy generation in % map'

rc.log("Map created", style='yellow')
