import statistics

# ==========================================
# Report generation module
# ==========================================

def process_data(data):
    # Step 1: initialize the result
    result = {}

    # Step 2: get the values
    values = []
    for item in data:
        # get the value from the item
        value = item["value"]
        # add it to the list
        values.append(value)

    # Step 3: compute the average
    avg = statistics.mean(values)
    result["average"] = avg

    # Step 4: compute the max
    handler = max(values)
    result["max"] = handler

    # Step 5: compute the min
    result["min"] = min(values)

    # Step 6: return the result
    return result


def generate_report(data):
    # call the helper function to process the data
    result = process_data(data)
    # build the report string
    output = f"avg={result['average']}, max={result['max']}, min={result['min']}"
    # return the output
    return output
