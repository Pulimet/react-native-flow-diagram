from collections import defaultdict, Counter
from parsing_utils import MSG_PARAM, TIME_PARAM, DURATION_PARAM, TYPE_PARAM, REQ_RSP_PARAM, SYNC_ASYNC_PARAM, LEVEL_PARAM

COUNT_PARAM = "count"
MIN_TIME_PARAM = "minTime"
MAX_TIME_PARAM = "maxTime"
ALL_TIME_PARAM = "allTime"

def calculate_averages(input_data):
    print("Calculating averages...")
    grouped_data = defaultdict(list)
    for item in input_data:
        key = item[MSG_PARAM]
        grouped_data[key].append(item)

    averages_list = []
    for message, group in grouped_data.items():
        total_time_since_start = sum(item[TIME_PARAM] for item in group)
        total_time_since_log = sum(item[DURATION_PARAM] for item in group)
        num_items = len(group)

        # Calculate the number of occurrences of the message
        message_count = Counter(item[MSG_PARAM] for item in group)[message]

        # Calculate the list of all timeSinceStart values
        all_time_since_start_string = " ".join(str(value) for value in [item[TIME_PARAM] for item in group])

        # Calculate the list of all timeSinceStart values
        all_time_since_start_list = [item[TIME_PARAM] for item in group]

        # Calculate min and max timeSinceStart
        min_time_since_start = min(all_time_since_start_list)
        max_time_since_start = max(all_time_since_start_list)

        req_res = group[0].get(REQ_RSP_PARAM, "")
        sync_async = group[0].get(SYNC_ASYNC_PARAM, "")
        level = group[0].get(LEVEL_PARAM, "")

        average_item = {
            TIME_PARAM: int(total_time_since_start / num_items),
            DURATION_PARAM: int(total_time_since_log / num_items),
            TYPE_PARAM: group[0][TYPE_PARAM],  # Assuming 'type' is consistent within a group
            MSG_PARAM: message,
            COUNT_PARAM: message_count,
            MIN_TIME_PARAM: min_time_since_start,
            MAX_TIME_PARAM: max_time_since_start,
            ALL_TIME_PARAM: all_time_since_start_string,
            REQ_RSP_PARAM: req_res,
            SYNC_ASYNC_PARAM: sync_async,
            LEVEL_PARAM: level
        }
        averages_list.append(average_item)

    # Sort the averages list by timeSinceStart in ascending order
    sorted_averages = sorted(averages_list, key=lambda it: it[TIME_PARAM])

    return sorted_averages
