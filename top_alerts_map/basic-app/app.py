from shiny import App, render, ui
from shinywidgets import render_altair, output_widget
import pandas as pd
import altair as alt
import json
import requests

# Load datasets
merged_df = pd.read_csv("merged_data.csv")

url = 'https://data.cityofchicago.org/api/geospatial/igwz-8jzy?method=export&format=GeoJSON'
response = requests.get(url)
file_path = "chicago_neighborhoods.geojson"

with open(file_path, 'wb') as file:
    file.write(response.content)
with open(file_path) as f:
    chicago_geojson = json.load(f)

geo_data = alt.Data(values=chicago_geojson["features"])

# Function to get top alerts
def get_top_alerts(selected_type, selected_subtype):
    filtered_df = merged_df[(merged_df['updated_type'] == selected_type) & (merged_df['updated_subtype'] == selected_subtype)]
    
    if "latitude_bin" not in filtered_df.columns:
        filtered_df["latitude_bin"] = filtered_df["latitude"].round(2)
    if "longitude_bin" not in filtered_df.columns:
        filtered_df["longitude_bin"] = filtered_df["longitude"].round(2)
    
    # Aggregate alerts
    collapsed_df = (
        filtered_df.groupby(['latitude_bin', 'longitude_bin'])
        .size()
        .reset_index(name='alert_count')
    )
    
    top_alerts = collapsed_df.sort_values('alert_count', ascending=False).head(10)
    return top_alerts

dropdown_choices = (
    merged_df[['updated_type', 'updated_subtype']]
    .drop_duplicates()
    .sort_values(by=['updated_type', 'updated_subtype']) 
    .apply(lambda row: f"{row['updated_type']} - {row['updated_subtype']}", axis=1)
    .tolist()
)
# Chatgpt, can you help me write a lamba function that find the unique combination 
# of updated_type and updated_subtype from my dataset, and show it as combination.

ui = ui.page_fluid(
    ui.input_select(
        "alert_type_subtype",
        "Select Alert Type and Subtype",
        choices=dropdown_choices,  
        selected=dropdown_choices[0]  # Pre-select the first option
    ),
    output_widget("top_alerts_plot")
)

# Chatgpt, 'how to make pre-select for my dropdown menu, debug my code'

def server(input, output, session):
    @output
    @render_altair
    def top_alerts_plot():
        selected_type, selected_subtype = input.alert_type_subtype().split(" - ")
        
        top_alerts = get_top_alerts(selected_type, selected_subtype)   
        
        lat_min, lat_max = top_alerts['latitude_bin'].min() - 0.02, top_alerts['latitude_bin'].max() + 0.02
        long_min, long_max = top_alerts['longitude_bin'].min() - 0.02, top_alerts['longitude_bin'].max() + 0.02
        
        # Scatter plot for top alerts
        scatter_plot = alt.Chart(top_alerts).mark_circle().encode(
            x=alt.X('longitude_bin:Q', title='Longitude', scale=alt.Scale(domain=[long_min, long_max])),
            y=alt.Y('latitude_bin:Q', title='Latitude', scale=alt.Scale(domain=[lat_min, lat_max])),
            size=alt.Size('alert_count:Q', title='Number of Alerts'),
            tooltip=['latitude_bin', 'longitude_bin', 'alert_count']
        ).properties(
            title=f'Top 10 Locations for {selected_type} - {selected_subtype} Alerts',
            width=600,
            height=600
        )
        
        # Map layer for Chicago 
        map_layer = alt.Chart(geo_data).mark_geoshape(
            fillOpacity=0.4,stroke='black'
        ).encode(
            tooltip=["properties.neighborhood:N"]
        ).project(type="identity", reflectY=True)
        
        combined_plot = map_layer + scatter_plot

        return combined_plot

app = App(ui, server)
