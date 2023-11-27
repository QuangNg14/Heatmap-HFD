import pandas as pd
import numpy as np
import plotly.express as px
import dash
from dash import html, dcc
from dash.dependencies import Input, Output
from dotenv import load_dotenv
import boto3
from io import StringIO
import os

load_dotenv()
# Read data
# data = pd.read_csv("HFD_22_Final_index.csv")

column_types = {"problematic_column": str}


def read_csv_from_s3(bucket_name, file_name, column_types=None):
    s3 = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("REGION"),
    )

    response = s3.get_object(Bucket=bucket_name, Key=file_name)

    data = response["Body"].read().decode("utf-8")
    if column_types:
        df = pd.read_csv(StringIO(data), dtype=column_types)
    else:
        df = pd.read_csv(StringIO(data))

    return df

    return df


# Assuming your bucket and file names
bucket_name = "comp449-heatmap-hfd"
file_name = "HFD_22_Final_index.csv"

# Read the data
data = read_csv_from_s3(bucket_name, file_name, column_types)

data["Contributing Factors List"] = (
    data["Contributing Factors"]
    .str.split(";")
    .apply(lambda x: [factor.strip() for factor in x])
)


def update_factors_list(factors):
    # Define the replacements and removals
    replacements = {
        "UNSAFE SPEED": "FAILED TO CONTROL SPEED",
        "SPEEDING - (OVERLIMIT)": "FAILED TO CONTROL SPEED",
        "HAD BEEN DRINKING": "UNDER INFLUENCE - ALCOHOL",
    }

    # Create a new list to store the updated factors
    updated_factors = []

    # Iterate through the factors and apply the logic
    for factor in factors:
        replacement = replacements.get(factor)
        if replacement:
            # If the replacement is already in the list, we'll skip adding this factor
            if replacement in factors:
                continue
            else:
                # Otherwise, we add the replacement to the list
                factor = replacement
        updated_factors.append(factor)

    # Remove duplicates that could have been created by the replacements
    updated_factors = list(set(updated_factors))

    return updated_factors


# Apply the function to each row's 'Contributing Factors List'
data["Contributing Factors List"] = data["Contributing Factors List"].apply(
    update_factors_list
)


# Define the mapping for "Crash Severity"
severity_mapping = {
    "N - NOT INJURED": 0,
    "C - POSSIBLE INJURY": 1,
    "B - SUSPECTED MINOR INJURY": 2,
    "A - SUSPECTED SERIOUS INJURY": 3,
    "K - FATAL INJURY": 4,
    "99 - UNKNOWN": 0,
}

# Apply the mapping to create a new column
data["severity_score"] = data["Crash Severity"].map(severity_mapping)

data = data.dropna(subset=["Latitude", "Longitude"])


# Normalize bottleneck_values to a range of 0 to 100
min_value = data["bottleneck_values"].min()
max_value = data["bottleneck_values"].max()
data["normalized_bottleneck"] = (
    (data["bottleneck_values"] - min_value) / (max_value - min_value)
) * 100

data["normalized_bottleneck_percentile_rank"] = (
    data["normalized_bottleneck"].rank(pct=True) * 100
)

# Round coordinates to the nearest fourth decimal place
data["Latitude"] = data["Latitude"].round(4)
data["Longitude"] = data["Longitude"].round(4)


# Initialize Dash app
app = dash.Dash(__name__)

# App layout
app.layout = html.Div(
    [
        html.H1("Houston Collision Dashboard"),
        # Dropdown for Metric
        html.Label("Select Heat Metric"),
        dcc.RadioItems(
            id="metric",
            options=[
                {"label": "Impact Metric", "value": "avg_impact"},
                {"label": "Total HFD Duration", "value": "avg_total_duration"},
            ],
            value="avg_impact",
        ),
        html.Label("Select Contributing Factor:"),
        dcc.Dropdown(
            id="filter-factor",
            options=[
                {"label": "All", "value": "All"},
                {
                    "label": "Failed to Control Speed",
                    "value": "FAILED TO CONTROL SPEED",
                },
                {
                    "label": "Disregarded Stop and Go Signal",
                    "value": "DISREGARD STOP AND GO SIGNAL",
                },
                {
                    "label": "Failed to Yield Right of Way - Stop Sign",
                    "value": "FAILED TO YIELD RIGHT OF WAY - STOP SIGN",
                },
                {
                    "label": "Failed to Drive in Single Lane",
                    "value": "FAILED TO DRIVE IN SINGLE LANE",
                },
                {
                    "label": "Failed to Yield Right of Way - Turning Left",
                    "value": "FAILED TO YIELD RIGHT OF WAY - TURNING LEFT",
                },
                {
                    "label": "Disregarded Stop Sign or Light",
                    "value": "DISREGARD STOP SIGN OR LIGHT",
                },
                {"label": "Driver Inattention", "value": "DRIVER INATTENTION"},
                {
                    "label": "Changed Lane When Unsafe",
                    "value": "CHANGED LANE WHEN UNSAFE",
                },
                {
                    "label": "Failed to Yield Right of Way - Open Intersection",
                    "value": "FAILED TO YIELD RIGHT OF WAY - OPEN INTERSECTION",
                },
                {
                    "label": "Under Influence - Alcohol",
                    "value": "UNDER INFLUENCE - ALCOHOL",
                },
                {
                    "label": "Failed to Yield Right of Way - Private Drive",
                    "value": "FAILED TO YIELD RIGHT OF WAY - PRIVATE DRIVE",
                },
                {"label": "Faulty Evasive Action", "value": "FAULTY EVASIVE ACTION"},
                {
                    "label": "Turned Improperly - Wrong Lane",
                    "value": "TURNED IMPROPERLY - WRONG LANE",
                },
                {
                    "label": "Pedestrian Failed to Yield Right of Way to Vehicle",
                    "value": "PEDESTRIAN FAILED TO YIELD RIGHT OF WAY TO VEHICLE",
                },
                {"label": "Turned When Unsafe", "value": "TURNED WHEN UNSAFE"},
                {
                    "label": "Failed to Yield Right of Way - To Pedestrian",
                    "value": "FAILED TO YIELD RIGHT OF WAY - TO PEDESTRIAN",
                },
                {"label": "Distraction in Vehicle", "value": "DISTRACTION IN VEHICLE"},
                {"label": "None", "value": "NONE"},
                {
                    "label": "Failed to Yield Right of Way - Turn on Red",
                    "value": "FAILED TO YIELD RIGHT OF WAY - TURN ON RED",
                },
                {"label": "Under Influence - Drug", "value": "UNDER INFLUENCE - DRUG"},
            ],
            value="All",
        ),
        # Dropdown for Crash Month
        html.Label("Select Crash Month:"),
        dcc.Dropdown(
            id="crash-month",
            options=[{"label": "All", "value": "All"}]
            + [
                {"label": month, "value": i}
                for i, month in enumerate(
                    [
                        "January",
                        "February",
                        "March",
                        "April",
                        "May",
                        "June",
                        "July",
                        "August",
                        "September",
                        "October",
                        "November",
                        "December",
                    ],
                    start=1,
                )
            ],
            value="All",
        ),
        # Dropdown for Day of Week
        html.Label("Select Day of Week:"),
        dcc.Dropdown(
            id="day-of-week",
            options=[
                {"label": "All", "value": "All"},
                {"label": "Monday", "value": "MONDAY"},
                {"label": "Tuesday", "value": "TUESDAY"},
                {"label": "Wednesday", "value": "WEDNESDAY"},
                {"label": "Thursday", "value": "THURSDAY"},
                {"label": "Friday", "value": "FRIDAY"},
                {"label": "Saturday", "value": "SATURDAY"},
                {"label": "Sunday", "value": "SUNDAY"},
            ],
            value="All",
        ),
        # Dropdown for Hour of Day
        html.Label("Select Hour of Day:"),
        dcc.Dropdown(
            id="hour-of-day",
            options=[{"label": "All", "value": "All"}]
            + [
                {"label": f"{hour}:00 - {hour}:59", "value": hour} for hour in range(24)
            ],
            value="All",
        ),
        # Dropdown for Crash Severity
        html.Label("Select Crash Severity:"),
        dcc.Dropdown(
            id="crash-severity",
            options=[
                {"label": "All", "value": "All"},
                {"label": "Not Injured", "value": "N - NOT INJURED"},
                {"label": "Possible Injury", "value": "C - POSSIBLE INJURY"},
                {
                    "label": "Suspected Minor Injury",
                    "value": "B - SUSPECTED MINOR INJURY",
                },
                {
                    "label": "Suspected Serious Injury",
                    "value": "A - SUSPECTED SERIOUS INJURY",
                },
                {"label": "Fatal Injury", "value": "K - FATAL INJURY"},
                {"label": "Unknown", "value": "99 - UNKNOWN"},
            ],
            value="All",
        ),
        # Dropdown for First Harmful Event
        html.Label("Select First Harmful Event:"),
        dcc.Dropdown(
            id="first-harmful-event",
            options=[
                {"label": "All", "value": "All"},
                {
                    "label": "Motor Vehicle in Transport",
                    "value": "MOTOR VEHICLE IN TRANSPORT",
                },
                {"label": "Fixed Object", "value": "FIXED OBJECT"},
                {"label": "Pedestrian", "value": "PEDESTRIAN"},
            ],
            value="All",
        ),
        # Dropdown for Light Condition
        html.Label("Select Light Condition:"),
        dcc.Dropdown(
            id="light-condition",
            options=[
                {"label": "All", "value": "All"},
                {"label": "Daylight", "value": "1 - DAYLIGHT"},
                {"label": "Dark, Lighted", "value": "3 - DARK, LIGHTED"},
                {"label": "Dark, Not Lighted", "value": "2 - DARK, NOT LIGHTED"},
            ],
            value="All",
        ),
        # Dropdown for Weather Condition
        html.Label("Select Weather Condition:"),
        dcc.Dropdown(
            id="weather-condition",
            options=[
                {"label": "All", "value": "All"},
                {"label": "Clear", "value": "1 - CLEAR"},
                {"label": "Cloudy", "value": "2 - CLOUDY"},
                {"label": "Rain", "value": "3 - RAIN"},
            ],
            value="All",
        ),
        # Dropdown for Surface Condition
        html.Label("Select Surface Condition:"),
        dcc.Dropdown(
            id="surface-condition",
            options=[
                {"label": "All", "value": "All"},
                {"label": "Dry", "value": "1 - DRY"},
                {"label": "Wet", "value": "2 - WET"},
            ],
            value="All",
        ),
        dcc.Graph(id="heatmap"),
    ]
)


@app.callback(
    Output("heatmap", "figure"),
    [
        Input("filter-factor", "value"),
        Input("crash-month", "value"),
        Input("crash-severity", "value"),
        Input("day-of-week", "value"),
        Input("first-harmful-event", "value"),
        Input("hour-of-day", "value"),
        Input("light-condition", "value"),
        Input("weather-condition", "value"),
        Input("surface-condition", "value"),
        Input("metric", "value"),
    ],
)
def update_graph(
    selected_factor,
    selected_month,
    selected_severity,
    selected_day,
    selected_harmful_event,
    selected_hour,
    selected_light,
    selected_weather,
    selected_surface,
    selected_metric,
):
    filtered_data = data.copy()

    # Apply filters based on dropdown selections
    if selected_factor != "All":
        filtered_data = filtered_data[
            filtered_data["Contributing Factors List"].apply(
                lambda x: selected_factor in x
            )
        ]

    if selected_month != "All":
        filtered_data = filtered_data[filtered_data["Crash Month"] == selected_month]

    if selected_day != "All":
        filtered_data = filtered_data[filtered_data["Day of Week"] == selected_day]

    if selected_hour != "All":
        filtered_data = filtered_data[filtered_data["Hour of Day"] == selected_hour]

    if selected_severity != "All":
        filtered_data = filtered_data[
            filtered_data["Crash Severity"] == selected_severity
        ]

    if selected_harmful_event != "All":
        filtered_data = filtered_data[
            filtered_data["First Harmful Event"] == selected_harmful_event
        ]

    if selected_light != "All":
        filtered_data = filtered_data[
            filtered_data["Light Condition"] == selected_light
        ]

    if selected_weather != "All":
        filtered_data = filtered_data[
            filtered_data["Weather Condition"] == selected_weather
        ]

    if selected_surface != "All":
        filtered_data = filtered_data[
            filtered_data["Surface Condition"] == selected_surface
        ]

    # Aggregate data by latitude and longitude
    aggregated_data = (
        filtered_data.groupby(["Latitude", "Longitude"])
        .agg(
            total_crashes=("Latitude", "size"),
            avg_impact=("normalized_bottleneck", "mean"),
            avg_total_duration=("total_duration", lambda x: x.mean() / 60),
            contributing_factors=(
                "Contributing Factors List",
                lambda x: sum(x, []),
            ),  # Aggregate lists
        )
        .reset_index()
    )

    # Process each group to get the top 3 contributing factors
    aggregated_data["top_factors"] = aggregated_data["contributing_factors"].apply(
        lambda factors: pd.Series(factors).value_counts().head(3).to_dict()
    )

    # Choose the color based on the selected metric
    if selected_metric == "avg_impact":
        color = "avg_impact"
        color_scale = [
            (0, "green"),
            (0.05, "lime"),
            (0.10, "orange"),
            (0.15, "red"),
            (1, "red"),
        ]
        # color_scale=[(0, 'green'), (0.01651173, 'lime'), (0.07483896, 'orange'), (0.13771392, 'red'), (1, 'red')],
        hover_text_label = "Average Impact"
        hover_text_value = aggregated_data["avg_impact"].map("{:.2f}".format)
    else:
        color = "avg_total_duration"
        color_scale = [
            (0, "green"),
            (0.0175, "lime"),
            (0.035, "orange"),
            (0.05, "orange"),
            (0.06, "red"),
            (1, "red"),
        ]
        # color_scale = [(0, '#ADD8E6'), (1, '#00008B')]
        hover_text_label = "Average Total Duration"
        hover_text_value = aggregated_data["avg_total_duration"].map("{:.2f}".format)

    # Create custom hover data with total crashes, average severity, and top 3 factors
    aggregated_data["hover_text"] = aggregated_data.apply(
        lambda row: f"Total Crashes: {row['total_crashes']}<br>{hover_text_label}: {hover_text_value[row.name]}<br>"
        + "<br>".join(
            [
                f"{idx+1}st Factor: {factor} ({count} instances)"
                if idx == 0
                else f"{idx+1}nd Factor: {factor} ({count} instances)"
                if idx == 1
                else f"{idx+1}rd Factor: {factor} ({count} instances)"
                if idx == 2
                else f"{idx+1}th Factor: {factor} ({count} instances)"
                for idx, (factor, count) in enumerate(row["top_factors"].items())
            ]
        ),
        axis=1,
    )

    fig_heatmap = px.scatter_mapbox(
        aggregated_data,
        lat="Latitude",
        lon="Longitude",
        size="total_crashes",
        color=color,
        color_continuous_scale=color_scale,
        # range_color=[0, 0.13],
        mapbox_style="carto-positron",
        zoom=11,
        center={"lat": data["Latitude"].mean(), "lon": data["Longitude"].mean()},
        opacity=0.8,
        height=1000,
        hover_name="hover_text",  # Use custom hover text as the hover name
        hover_data={
            "total_crashes": False,  # Disable default total crashes
            "avg_impact": False,
            "avg_total_duration": False,
        },
    )  # Disable default impact
    return fig_heatmap


# Run app
if __name__ == "__main__":
    app.run_server(debug=True)
