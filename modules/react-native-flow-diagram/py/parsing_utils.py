from config import SHOW_NETWORK_REQUEST, SHOW_NETWORK_RESPONSE, SHOW_REGULAR_LOG, FILTER_NETWORK_REQUEST, LOG_TAG

ARROW = "=>"

TIME_PARAM = "time"
TYPE_PARAM = "type"
MSG_PARAM = "msg"
REQ_RSP_PARAM = "req_rsp"
DURATION_PARAM = "duration"
LEVEL_PARAM = "level"
SYNC_ASYNC_PARAM = "sync_async"

TYPE_NET = "NET"
TYPE_AD = "AD"
TYPE_RN = "RN"
SYNC = "SYNC"
ASYNC = "ASYNC"
NET_REQ = "[REQ]"
NET_RSP = "[RSP]"
REQ = "REQ"
RSP = "RSP"

def parse_data(logcat_output):
    print("Parsing the logcat output...")
    print("LogCat Output length: ", len(logcat_output))
    parsed_data = []

    recent_sync_log_time = 0

    for line in logcat_output:
        # Find the index of the "=>" string and skip the line if it is not found
        arrow_index = line.find(ARROW)
        if arrow_index == -1:
            continue

        # Remove all before LOG_TAG including tag itself
        line = line[line.find(LOG_TAG) + len(LOG_TAG) + 2:]
        time_since_start = int(line[:10].replace(" ", ""))

        line = line[line.find(ARROW) + 3:]
        # print(line)

        # Find in the line a value that is between the first [XXXXXXX]
        start_bracket = line.find('[')
        end_bracket = line.find(']')
        if start_bracket == -1 or end_bracket == -1:
            continue
        log_type = line[start_bracket + 1:end_bracket]

        line = line[end_bracket + 1:].strip()

        # Network request case
        if log_type == TYPE_NET and NET_REQ in line:
            if SHOW_NETWORK_REQUEST:
                if FILTER_NETWORK_REQUEST and FILTER_NETWORK_REQUEST not in line:
                    continue

                parsed = parse_network_request(time_since_start, line)
                parsed_data.append(parsed)
            continue

            # Network response case
        if log_type == TYPE_NET and NET_RSP in line:
            if SHOW_NETWORK_RESPONSE:
                if FILTER_NETWORK_REQUEST and FILTER_NETWORK_REQUEST not in line:
                    continue

                parsed = parse_network_response(time_since_start, line)
                parsed_data.append(parsed)
            continue

            # Regular log case
        if SHOW_REGULAR_LOG:
            # Assuming the format is [TYPE] message, we pass the type and message
            parsed = parse_regular_log(time_since_start, log_type, line, recent_sync_log_time)
            if parsed[SYNC_ASYNC_PARAM] == SYNC:
                recent_sync_log_time = time_since_start
            parsed_data.append(parsed)

    # Add for going over parsed_data and print each one
    # for item in parsed_data:
    #     print(item)

    return parsed_data


def parse_network_request(time_since_start, wrapped):
    url = wrapped.replace("[REQ] ", "").strip()
    return {
        TIME_PARAM: time_since_start,
        DURATION_PARAM: 0,
        TYPE_PARAM: TYPE_NET,
        REQ_RSP_PARAM: REQ,
        MSG_PARAM: url
    }


def parse_network_response(time_since_start, wrapped):
    wrapped = wrapped.replace("[RSP] ", "").strip()

    comma_index = wrapped.find(",")
    # Get only URL
    url = wrapped[:comma_index].strip()
    # Get only status code
    status_code = wrapped[comma_index + 10:comma_index + 13]
    # message in format: [STATUS_CODE] URL
    message = "[" + status_code + "] " + url

    # Get only duration
    duration = int(wrapped[wrapped.find("Elapsed time: ") + 13:])
    return {
        TIME_PARAM: time_since_start,
        DURATION_PARAM: duration,
        TYPE_PARAM: TYPE_NET,
        REQ_RSP_PARAM: RSP,
        MSG_PARAM: message
    }


def parse_regular_log(time_since_start, msg_type, message, recent_sync_log_time):
    start_bracket = message.find('[')
    end_bracket = message.find(']')
    level = message[start_bracket + 1:end_bracket]
    message = message[end_bracket + 1:].strip()

    start_bracket = message.find('[')
    end_bracket = message.find(']')
    sync_async = message[start_bracket + 1:end_bracket]
    message = message[end_bracket + 1:].strip()

    duration = 0
    if sync_async == SYNC:
        duration =  time_since_start - recent_sync_log_time

    return {
        TIME_PARAM: time_since_start,
        DURATION_PARAM: duration,
        TYPE_PARAM: msg_type,
        MSG_PARAM: message,
        LEVEL_PARAM: level,
        SYNC_ASYNC_PARAM: sync_async
    }
