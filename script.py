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

    # Read data to json
    df_json = json.loads(df1[['country', 'country_code', 'geometry', 'technology', 'unit', 'year', 'percentage']].to_json())

    map_data = json.dumps(df_json)

    # Assign Source
    map_source.geojson = map_data

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
    
    # map_all.background_fill_color="blue"

    map_all.add_layout(color_bar, 'below')

    return map_all

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

en_df = pd.concat([ren_df, gen_df])

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

# Range slider for the year
year_slider = Slider(
    start=2018,
    end=2021,
    value=2018, 
    step=1,
    title='year',
    width=110
)

# Assign official names to data
gen_df['country'] = gen_df['country'].apply(findcountry)

gdf['country'] = gdf['country'].apply(findcountry)

# Correct names in dataframe for matching it with map data
gen_df.country = gen_df.country.apply(lambda x: country_out.get(x, x))

# Merge data with co-ordinates
geo_df = gdf.merge(gen_df, left_on='country', right_on='country', how='left')

geo_df.country = geo_df.country.apply(lambda x: x.capitalize())

# Fill Null values
na_country = list(geo_df[geo_df['2018'].isna()].country)
false_na_country = list(set(en_df.country).difference(na_country))

geo_df.fillna(0, inplace=True)

# Melt the year column
geo_df1 = pd.melt(geo_df, id_vars=['country', 'country_code', 'geometry', 'technology', 'unit'], 
            value_vars=['2018', '2019', '2020', '2021'])

geo_df1.columns = ['country', 'country_code', 'geometry', 'technology', 'unit', 'year', 'percentage']

geo_df1.percentage = round(geo_df1['percentage'], 2)

# Read data to json
df_json = json.loads(geo_df1.query('year=="2018"')[
    ['country', 'country_code', 'geometry', 'technology', 'unit', 'year', 'percentage']
    ].to_json())

# Convert to string like object
map_data = json.dumps(df_json)

# Assign Source
map_source = GeoJSONDataSource(geojson=map_data)

year_slider.on_change('value', create_data)

map_all = build_map(map_source)

curdoc().add_root(row(year_slider, map_all))
curdoc().title = 'Renewable energy generation in % map'

rc.log("Map created", style='yellow')
