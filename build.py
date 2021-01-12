import argparse
import sys
from datetime import datetime

import icalendar
import kockatykalendar.api as kkapi
from kockatykalendar.events import Event, EventContestant, EventType, EventScience
from pytz import timezone

PREFIX_OK = "\u001b[32m✔\u001b[0m"
PREFIX_WORK = "\u001b[33m⚒\u001b[0m"
PREFIX_ERROR = "\u001b[31m✗\u001b[0m"
TZ = timezone("Europe/Bratislava")
LANG = {    # TODO: Sync with frontend
    "types": {
        EventType.SUTAZ: "súťaž",
        EventType.SEMINAR: "seminár",
        EventType.SUSTREDENIE: "sústredenie",
        EventType.VIKENDOVKA: "víkendovka",
        EventType.TABOR: "tábor",
        EventType.OLYMPIADA: "olympiáda",
        EventType.PREDNASKY: "prednášky",
        EventType.OTHER: "iný druh akcie",
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
        EventContestant.SchoolType.ZAKLADNA: "ZŠ",
        EventContestant.SchoolType.STREDNA: "SŠ",
    },
    "sciences": {
        EventScience.MAT: "MAT",
        EventScience.FYZ: "FYZ",
        EventScience.INF: "INF",
        EventScience.OTHER: "iné",
    }
}


parser = argparse.ArgumentParser(description="KockatýKalendár.sk iCal builder v0.1.1")
parser.add_argument("-d", "--data-source", help="Source JSON file to use while building. Defaults to current school year.")
parser.add_argument("--school", help="School type to filter output. Defaults to any.", default="any", choices=["any", "zs", "ss"])
parser.add_argument("--science", help="Science to filter output. Defaults to any.", default=["any"], choices=["any", "mat", "fyz", "inf", "other"], nargs="*")
parser.add_argument("-o", "--output", help="Output file.", type=argparse.FileType("w"), default="-")
args = parser.parse_args()


# Select data source JSON file.
if args.data_source:
    dataset = args.data_source
    print(PREFIX_OK, f"Using '{dataset}' as data source.", file=sys.stderr)
else:
    dataset = kkapi.get_current_dataset()
    print(PREFIX_OK, f"Using school year {dataset.school_year} as data source.", file=sys.stderr)


# Load JSON data.
events = kkapi.get_events(dataset)
print(PREFIX_WORK, "Generating iCal file...", file=sys.stderr)


def format_contestant(contestant: EventContestant):
    return "%s %d" % (LANG["contestant_types"][contestant.type], contestant.year)


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


filtered_events = filter(school_filter, events)
filtered_events = filter(science_filter, filtered_events)

ical = icalendar.Calendar()
ical.add("prodid", "-//KockatyKalendar.sk//v0.1//")
ical.add("version", "2.0")  # ical version

for event in filtered_events:
    event: Event = event    # TODO: Remove this line.
    ical_event = icalendar.Event()
    ical_event.add("summary", ("(Zrušený)" if event.cancelled else "") + event.name)
    ical_event.add("dtstart", TZ.localize(datetime.combine(event.date.start, datetime.min.time())).date())

    if event.date.end:
        ical_event.add("dtend", TZ.localize(datetime.combine(event.date.end, datetime.max.time())).date())

    if event.contestants.min.type is None and event.contestants.max.type is None:
        contestants = "ktokoľvek"
    elif event.contestants.min.type is None:
        contestants = format_contestant(event.contestants.max) + " a mladší"
    elif event.contestants.max.type is None:
        contestants = format_contestant(event.contestants.min) + " a starší"
    else:
        contestants = format_contestant(event.contestants.min) + " – " + format_contestant(event.contestants.max)

    type = LANG["types"][event.type]
    sciences = ", ".join(map(lambda x: LANG["sciences"][x], event.sciences))
    description = f"{type} | {sciences} | {contestants}\n"

    if event.info:
        description += f"\n{event.info}\n"

    organizers = ", ".join(map(lambda x: LANG["organizers"][x] if x in LANG["organizers"] else x, event.organizers))
    description += f"\nOrganizátor(i): {organizers}"

    if event.link:
        ical_event.add("url", event.link)
        description += f"\n{event.link}"

    ical_event.add("description", description)
    ical.add_component(ical_event)

with args.output as file:
    file.write(ical.to_ical().decode())

print(PREFIX_OK, f"Generated iCal.", file=sys.stderr)
