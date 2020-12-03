import argparse
import icalendar
import sys
from datetime import date, datetime
import requests
import json
from pytz import timezone


PREFIX_OK = "\u001b[32m✔\u001b[0m"
PREFIX_WORK = "\u001b[33m⚒\u001b[0m"
PREFIX_ERROR = "\u001b[31m✗\u001b[0m"
TZ = timezone("Europe/Bratislava")
LANG = {    # TODO: Sync with frontend
    "types": {
        "sutaz": "súťaž",
        "seminar": "seminár",
        "sustredenie": "sústredenie",
        "vikendovka": "víkendovka",
        "tabor": "tábor",
        "olympiada": "olympiáda",
        "prednasky": "prednášky",
        "other": "iný druh akcie",
    },
    "organizers": {
        "trojsten": "Trojsten",
        "p-mat": "P-mat",
        "sezam": "SEZAM",
        "riesky": "Riešky",
        "strom": "Strom",
        "siov": "ŠIOV",
        "iuventa": "Iuventa",
        "matfyz": "FMFI UK",
    },
    "contestant_types": {
        "zs": "ZŠ",
        "ss": "SŠ",
    },
    "sciences": {
        "mat": "MAT",
        "fyz": "FYZ",
        "inf": "INF",
        "other": "iné",
    }
}


parser = argparse.ArgumentParser(description="KockatýKalendár.sk iCal builder v0.1")
parser.add_argument("-d", "--data-source", help="Source JSON file to use while building. Defaults to current school year.")
parser.add_argument("--school", help="School type to filter output. Defaults to any.", default="any", choices=["any", "zs", "ss"])
parser.add_argument("--science", help="Science to filter output. Defaults to any.", default=["any"], choices=["any", "mat", "fyz", "inf", "other"], nargs="*")
parser.add_argument("-o", "--output", help="Output file.", type=argparse.FileType("w"), default="-")
args = parser.parse_args()


# Select data source JSON file.
if args.data_source:
    data_source = args.data_source
else:
    today = date.today()
    current_school_year = today.year if today.month >= 9 else today.year - 1

    # We will load index.json and find the correct filename for current school year.
    index_data = requests.get("https://data.kockatykalendar.sk/index.json")
    if index_data.status_code != 200:
        print(PREFIX_ERROR, f"Could not load index.json file. HTTP {index_data.status_code}", file=sys.stderr)
        raise SystemExit(1)

    index_years = json.loads(index_data.text)
    selected_file = None
    for year in index_years:
        if year["start_year"] == current_school_year:
            selected_file = year["filename"]
            break

    if not selected_file:
        print(PREFIX_ERROR, f"Could not find any data file for school year {current_school_year}.", file=sys.stderr)
        raise SystemExit(1)

    data_source = f"https://data.kockatykalendar.sk/{selected_file}"
print(PREFIX_OK, f"Using '{data_source}' as data source.", file=sys.stderr)


# Load JSON data.
calendar_res = requests.get(data_source)
if calendar_res.status_code != 200:
    print(PREFIX_ERROR, f"Could not read data. HTTP {calendar_res.status_code}", file=sys.stderr)
calendar_data = json.loads(calendar_res.text)
print(PREFIX_WORK, "Generating iCal file...", file=sys.stderr)


# School filter:
def science_filter(event):
    if args.science == ["any"]:
        return True

    for science in args.science:
        if science in event["sciences"]:
            return True
    return False


# Science filter:
def school_filter(event):
    if args.school == "any":
        return True
    event_schools = set()
    event_schools.add(event["contestants"]["min"][0:2])
    if "max" in event["contestants"]:
        event_schools.add(event["contestants"]["max"][0:2])

    return args.school in event_schools


filtered_events = filter(school_filter, calendar_data)
filtered_events = filter(science_filter, filtered_events)

ical = icalendar.Calendar()
ical.add("prodid", "-//KockatyKalendar.sk//v0.1//")
ical.add("version", "2.0")  # ical version

for event in filtered_events:
    ical_event = icalendar.Event()
    ical_event.add("summary", ("(Zrušený)" if "cancelled" in event and event["cancelled"] else "") + event["name"])

    event_start = datetime.strptime(event["date"]["start"], "%Y-%m-%d")
    event_start = TZ.localize(event_start)
    ical_event.add("dtstart", event_start.date())

    if "end" in event["date"]:
        event_end = datetime.strptime(event["date"]["end"], "%Y-%m-%d")
        event_end = TZ.localize(event_end)
        ical_event.add("dtend", event_end.date())

    contestants = LANG["contestant_types"][event["contestants"]["min"][0:2]] + " " + event["contestants"]["min"][2:]
    if "max" in event["contestants"]:
        contestants += " - "
        if event["contestants"]["min"][0:2] != event["contestants"]["max"][0:2]:
            contestants += LANG["contestant_types"][event["contestants"]["max"][0:2]] + " "
        contestants += event["contestants"]["max"][2:]

    type = LANG["types"][event["type"]]
    sciences = ", ".join(map(lambda x: LANG["sciences"][x], event["sciences"]))
    description = f"{type} | {sciences} | {contestants}\n"

    if "info" in event:
        description += f"\n{event['info']}\n"

    organizers = ", ".join(map(lambda x: LANG["organizers"][x] if x in LANG["organizers"] else x, event["organizers"]))
    description += f"\nOrganizátor(i): {organizers}"

    if "link" in event:
        ical_event.add("url", event["link"])
        description += f"\n{event['link']}"

    ical_event.add("description", description)
    ical.add_component(ical_event)

with args.output as file:
    file.write(ical.to_ical().decode())

print(PREFIX_OK, f"Generated iCal.", file=sys.stderr)
