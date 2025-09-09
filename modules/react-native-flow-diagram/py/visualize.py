import subprocess

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

from config import OPEN_PNG, VISUAL_URL, VISUAL_ADD_TIME_AT_THE_END, PNG_PATH
from parsing_utils import MSG_PARAM, TIME_PARAM, DURATION_PARAM, TYPE_PARAM, TYPE_NET, TYPE_AD, TYPE_IOS, TYPE_RN, SYNC_ASYNC_PARAM, ASYNC, REQ_RSP_PARAM, REQ, RSP

NATIVE_COLOR = "blue"
RN_COLOR = "green"
NET_REQUEST_COLOR = "orange"
NET_RESPONSE_COLOR = "yellow"
ASYNC_COLOR = "red"

def save_png_with_data(input_averages):
    save_png(input_averages, PNG_PATH)

def save_png(input_averages, png_path):
    print("Visualizing the data, saving to png...")
    num_events = len(input_averages)

    if num_events == 0:
        print("No events to visualize.")
        return

    # Extract the maximum timeSinceStart for scaling the x-axis
    max_time = max(item[TIME_PARAM] for item in input_averages) + VISUAL_ADD_TIME_AT_THE_END

    height = num_events / 4
    width = max_time / 500

    # Create a figure and axis
    plt.figure(figsize=(width, height))
    ax = plt.gca()

    # Set up the x-axis as a timeline
    ax.set_xlim(0, max_time)
    ax.set_xlabel('Time Since Start (ms)')

    # Hide the y-axis ticks and labels
    ax.set_yticks([])
    ax.set_ylabel('')

    box_height = 2  # Adjust box box_height as needed

    # Track the current y-position for each message
    current_y = 100  # Adjust starting position as needed

    # --- Create a visual legend with colored boxes ---
    legend_data = [
        ("Native (Sync)", NATIVE_COLOR),
        ("React Native", RN_COLOR),
        ("Network Request", NET_REQUEST_COLOR),
        ("Network Response", NET_RESPONSE_COLOR),
        ("Async (Native/RN)", ASYNC_COLOR)
    ]

    legend_handles = [mpatches.Patch(color=color, label=label, alpha=0.5) for label, color in legend_data]

    ax.legend(handles=legend_handles,
              loc='upper right',  # Position in the top-left corner
              ncol=len(legend_data),  # Display all items in a single row
              frameon=True,  # Draw a frame around the legend
              facecolor='wheat',
              framealpha=0.5,  # Make the frame background semi-transparent
              borderpad=0.5,  # Padding inside the legend box
              labelspacing=0.5,  # Spacing between the color patch and the label
              columnspacing=1.0,  # Spacing between legend items
              handletextpad=0.5,  # Spacing between handle and text
              prop={'size': 10}  # Font size for legend text
              )

    # Plot each message as a box
    for item in input_averages:
        x = item[TIME_PARAM] - item[DURATION_PARAM]

        width = item[DURATION_PARAM]

        # Each type should have different color
        type_param = item[TYPE_PARAM]
        color = RN_COLOR # TYPE_RN

        if type_param == TYPE_AD or type_param == TYPE_IOS:
            color = NATIVE_COLOR

        if item.get(SYNC_ASYNC_PARAM) == ASYNC:
            width = 40
            color = ASYNC_COLOR

        if type_param == TYPE_NET and item.get(REQ_RSP_PARAM) == REQ:
            width = 40
            color = NET_REQUEST_COLOR

        if type_param == TYPE_NET and item.get(REQ_RSP_PARAM) == RSP:
            color = NET_RESPONSE_COLOR

        # print(f"{type_param} -> {color}")

        # If type is NE then cut message to 50 characters
        if type_param == TYPE_NET:
            item[MSG_PARAM] = item[MSG_PARAM][:VISUAL_URL] + '...'

        # Text label for the message
        plt.text(x + width + 4, current_y, item[MSG_PARAM], ha='left', va='center', wrap=True)

        # Box plot with adjusted y-position
        plt.barh(current_y, width, box_height, left=x, color=color, alpha=0.5)

        # if width great then 300 add inside the box text with width + "ms"
        if width > 300:
            plt.text(x + 4, current_y, f"{width}ms", ha='left', va='center', wrap=True, fontsize=8)

        # Update current y-position for the next message
        current_y -= box_height + 0.2  # Adjust spacing between boxes

    # Add vertical lines for every 100ms and 1000ms
    for i in range(0, int(max_time) + 1, 100):
        plt.axvline(x=i, color='lightgray', linestyle='-', linewidth=0.3)  # Light gray for 100ms

    for i in range(0, int(max_time) + 1, 1000):
        plt.axvline(x=i, color='gray', linestyle='-', linewidth=0.7)  # Gray for 1000ms

    plt.title('Timeline Visualization of Message Averages')
    # Save the plot as a PNG image
    plt.savefig(png_path)  # Replace with desired filename

    if OPEN_PNG:
        # Open png file
        subprocess.run(["open", png_path])
