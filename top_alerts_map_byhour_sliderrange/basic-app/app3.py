from shiny import App, ui, render
from shinywidgets import render_altair, output_widget
import pandas as pd
import altair as alt
import json

# Load datasets
merged_data = pd.read_csv("/Users/sara/Desktop/Python/problem_sets/ps6/PS6_Xinyi/merged_data.csv")
with open("Boundaries_Neighborhoods.geojson") as f:
    chicago_geojson = json.load(f)
geo_data = alt.Data(values=chicago_geojson["features"])

merged_data['hour'] = pd.to_datetime(merged_data['ts']).dt.hour

dropdown_choices = (
    merged_data[['updated_type', 'updated_subtype']]
    .drop_duplicates()
    .sort_values(by=['updated_type', 'updated_subtype'])
    .apply(lambda row: f"{row['updated_type']} - {row['updated_subtype']}", axis=1)
    .tolist()
)

app_ui = ui.page_fluid(
    ui.input_select(
        id="type_subtype",
        label="Select Alert Type and Subtype:",
        choices=dropdown_choices,
        selected=dropdown_choices[0]
    ),
    ui.input_switch(
        id="switch",
        label="Toggle to switch to range of hours",
        value=False  # Default: single hour
    ),
    ui.output_ui("single_hour_slider"),  
    ui.output_ui("hour_range_slider"),  
    output_widget("top_alerts_plot")  
)

# ChatGpt, 'why my code here show both output, I want my bottom to control 
# help me debug'. ask help for ui part debug

def server(input, output, session):
    @output
    @render.ui
    def single_hour_slider():
        # Single hour if switch is OFF
        if not input.switch():
            return ui.input_slider(
                id="hour_slider",
                label="Select Single Hour:",
                min=0,
                max=23,
                value=8,
                step=1
            )
        return None

    @output
    @render.ui
    def hour_range_slider():
        # Range if switch is ON
        if input.switch():
            return ui.input_slider(
                id="hour_range",
                label="Select Hour Range:",
                min=0,
                max=23,
                value=(6, 9),
                step=1
            )
        return None

    @output
    @render_altair
    def top_alerts_plot():
        selected_type, selected_subtype = input.type_subtype().split(" - ")

        if input.switch():
            # Range of hours
            start_hour, end_hour = input.hour_range()
            filtered_data = merged_data[
                (merged_data['updated_type'] == selected_type) &
                (merged_data['updated_subtype'] == selected_subtype) &
                (merged_data['hour'] >= start_hour) &
                (merged_data['hour'] < end_hour)
            ].copy()
        else:
            # Single hour
            selected_hour = input.hour_slider()
            filtered_data = merged_data[
                (merged_data['updated_type'] == selected_type) &
                (merged_data['updated_subtype'] == selected_subtype) &
                (merged_data['hour'] == selected_hour)
            ].copy()
            # Chatgpt: 'can you help me debug my code to see why my switch
            # bottom is not working her.

        filtered_data['binned_latitude'] = filtered_data['latitude'].round(2)
        filtered_data['binned_longitude'] = filtered_data['longitude'].round(2)
        aggregated_data = (
            filtered_data.groupby(['binned_latitude', 'binned_longitude'])
            .size()
            .reset_index(name='alert_count')
        )

        # Get top 10 locations
        top_alerts = aggregated_data.sort_values(by='alert_count', ascending=False).head(10)

        lat_min, lat_max = top_alerts['binned_latitude'].min() - 0.02, top_alerts['binned_latitude'].max() + 0.02
        long_min, long_max = top_alerts['binned_longitude'].min() - 0.02, top_alerts['binned_longitude'].max() + 0.02

        # scatter plot
        scatter_plot = alt.Chart(top_alerts).mark_circle().encode(
            x=alt.X('binned_longitude:Q', title='Longitude', scale=alt.Scale(domain=[long_min, long_max])),
            y=alt.Y('binned_latitude:Q', title='Latitude', scale=alt.Scale(domain=[lat_min, lat_max])),
            size=alt.Size('alert_count:Q', title='Number of Alerts'),
            tooltip=['binned_latitude', 'binned_longitude', 'alert_count']
        ).properties(
            title=f'Top 10 Locations for {selected_type} - {selected_subtype}',
            width=600,
            height=600
        )

        # Chicago map
        map_layer = alt.Chart(geo_data).mark_geoshape(
            fillOpacity=0.3,
            stroke='black'
        ).encode(
            tooltip=["properties.neighborhood:N"]
        ).project(
            type="identity", reflectY=True
        ).properties(
            width=600,
            height=600
        )

        combined_plot = map_layer + scatter_plot
        return combined_plot

app = App(app_ui, server)
