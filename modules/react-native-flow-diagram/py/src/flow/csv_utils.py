import csv
import subprocess

from calc_average import COUNT_PARAM, MIN_TIME_PARAM, MAX_TIME_PARAM, ALL_TIME_PARAM
from parsing_utils import MSG_PARAM, TIME_PARAM, DURATION_PARAM, TYPE_PARAM, TYPE_NET, REQ_RSP_PARAM


def save_csv_with_data(input_averages, params):
    print("Saving the averages data to csv...")
    save_csv(input_averages, params)
    save_csv_only_with_network_responses(input_averages, params.csv_net_path)

    if params.open_csv:
        open_csv_with_numbers(params.csv_path)


def save_csv(input_averages, params):
    with open(params.csv_path, "w") as f:
        report_package = params.package if params.platform == 'android' else params.bundle_id

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
        writer.writerow([params.wait_time, params.launch_times, "---", report_package, "---", "---", "---", "---", ])


def save_csv_only_with_network_responses(input_averages, csv_net_path):
    print("Saving the averages of only network data to csv...")

    # Filter only network responses
    input_averages = [item for item in input_averages if item[TYPE_PARAM] == TYPE_NET]

    with open(csv_net_path, "w") as f:
        writer = csv.writer(f)

        # Write the header row for the data
        writer.writerow(["Time", "Type", "Duration", "URL", "Count"])

        # Write the data but message is limited to 50 characters. add "..." only if was limited
        for item in input_averages:
            writer.writerow(
                [item[TIME_PARAM],
                 item[REQ_RSP_PARAM],
                 item[DURATION_PARAM],
                 item[MSG_PARAM],
                 item[COUNT_PARAM]]
            )


def open_csv_with_numbers(csv_path):
    print("Open CSV file with Numbers...")
    try:  # Use the 'open' command to launch Numbers with the CSV file
        subprocess.run(["open", "-a", "Numbers", csv_path])
    except subprocess.CalledProcessError as e:
        print(f"Error opening CSV file with Numbers: {e}")
