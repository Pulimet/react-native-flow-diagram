import csv
import subprocess

from calc_average import COUNT_PARAM, MIN_TIME_PARAM, MAX_TIME_PARAM, ALL_TIME_PARAM
from config import PACKAGE, WAIT_TIME, LAUNCH_COUNT, OPEN_CSV, FILE_PATH, SHOW_NETWORK_RESPONSE
from parsing_utils import MSG_PARAM, TIME_PARAM, DURATION_PARAM, TYPE_PARAM, TYPE_NET, REQ_RSP_PARAM


def save_csv_with_data(input_averages):
    print("Saving the averages data to csv...")
    save_csv(input_averages)

    if SHOW_NETWORK_RESPONSE:
        save_csv_only_with_network_responses(input_averages)

    if OPEN_CSV:
        open_csv_with_numbers()


def save_csv(input_averages):
    csv_path = f"{FILE_PATH}.csv"

    with open(csv_path, "w") as f:
        writer = csv.writer(f)

        # Write the header row for the data
        writer.writerow(["Time", "Duration", "Type", "Message", "Count", "Min", "Max", "All", 'Full Message'])

        # Write the data but message is limited to 50 characters. add "..." only if was limited
        for item in input_averages:
            message = item[MSG_PARAM]
            if len(message) > 50:
                message = message[:50] + '...'

            req_res = ""
            if item[REQ_RSP_PARAM]:
                req_res = " - " + item[REQ_RSP_PARAM]

            type_param = item[TYPE_PARAM] + req_res

            writer.writerow(
                [item[TIME_PARAM],
                 item[DURATION_PARAM],
                 type_param,
                 message,
                 item[COUNT_PARAM],
                 item[MIN_TIME_PARAM],
                 item[MAX_TIME_PARAM],
                 item[ALL_TIME_PARAM],
                 item[MSG_PARAM]]
            )

        # Write TIME, REPEAT and PACKAGE
        writer.writerow(["---", "---", "---", "---", "---", "---", "---", "---"])
        writer.writerow(["TIME", "REPEAT", "---", "PACKAGE", "---", "---", "---", "---", ])
        writer.writerow([WAIT_TIME, LAUNCH_COUNT, "---", PACKAGE, "---", "---", "---", "---", ])


def save_csv_only_with_network_responses(input_averages):
    print("Saving the averages of only network data to csv...")
    csv_path = f"{FILE_PATH}_net.csv"

    # Filter only network responses
    input_averages = [item for item in input_averages if item[TYPE_PARAM] == TYPE_NET]

    with open(csv_path, "w") as f:
        writer = csv.writer(f)

        # Write the header row for the data
        writer.writerow(["Time", "Type",  "Duration", "URL", "Count"])

        # Write the data but message is limited to 50 characters. add "..." only if was limited
        for item in input_averages:
            writer.writerow(
                [item[TIME_PARAM],
                 item[REQ_RSP_PARAM],
                 item[DURATION_PARAM],
                 item[MSG_PARAM],
                 item[COUNT_PARAM]]
            )


def open_csv_with_numbers():
    print("Open CSV file with Numbers...")
    csv_path = f"{FILE_PATH}.csv"
    try:  # Use the 'open' command to launch Numbers with the CSV file
        subprocess.run(["open", "-a", "Numbers", csv_path])
    except subprocess.CalledProcessError as e:
        print(f"Error opening CSV file with Numbers: {e}")
