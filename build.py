import argparse
import sys
from datetime import datetime
from os import path, makedirs

import icalendar
import kockatykalendar.api as kkapi
from kockatykalendar.events import EventContestant, EventType, EventScience
from pytz import timezone
from hashlib import sha1

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
        EventScience.CHEM: "CHEM",
        EventScience.BIO: "BIO",
        EventScience.OTHER: "iné",
        EventScience.ANY: "všetky",
    }
}


parser = argparse.ArgumentParser(description="KockatýKalendár.sk iCal builder v0.1.1")
parser.add_argument("-d", "--data-source", help="Source JSON file to use while building. Defaults to current school year.")
parser.add_argument("--all", help="Generate all combinations of school, science and organizer", action='store_true')
parser.add_argument("--school", help="School type to filter output. Defaults to any.", default="any", choices=["any", "zs", "ss"])
parser.add_argument("--science", help="Science to filter output. Defaults to any.", default=["any"], choices=["any", "mat", "fyz", "inf", "other"], nargs="*")
parser.add_argument("--organizer", help="Organizer to filter output. Default to any.", default=["any"], choices=["any"]+list(LANG["organizers"].keys()), nargs="*")
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


def format_contestant(contestant: EventContestant, prev_contestant=None):
    if prev_contestant and prev_contestant.type == contestant.type:
        return str(contestant.year)
    return "%s %d" % (LANG["contestant_types"][contestant.type], contestant.year)


# School filter:
def school_filter(args):
    def filter(event):
        if args == "any":
            return True

        # Events for everyone should be always visible.
        if event.contestants.min.type is None and event.contestants.max.type is None:
            return True

        # If we only have max limit
        if event.contestants.min.type is None:
            if event.contestants.max.type == EventContestant.SchoolType.STREDNA:
                return True
            else:
                return args == "zs"

        # If we only have min limit
        if event.contestants.max.type is None:
            if event.contestants.min.type == EventContestant.SchoolType.ZAKLADNA:
                return True
            else:
                return args == "ss"

        return EventContestant.SchoolType(args) in [
            event.contestants.min.type,
            event.contestants.max.type,
        ]
    return filter


# Science filter:
def science_filter(args):
    def filter(event):
        if args == ["any"]:
            return True
        
        if event.sciences == [EventScience.ANY]:
            return True

        for science in args:
            if EventScience(science) in event.sciences:
                return True
        return False
    return filter


# Organizer filter:
def organizer_filter(args):
    def filter(event):
        if args == ["any"]:
            return True

        for organizer in args:
            if organizer in event.organizers:
                return True
        return False
    return filter

def generate_ical(school, science, organizer):
    filtered_events = filter(school_filter(school), events)
    filtered_events = filter(science_filter(science), filtered_events)
    filtered_events = filter(organizer_filter(organizer), filtered_events)

    ical = icalendar.Calendar()
    ical.add("prodid", "-//KockatyKalendar.sk//v0.1//")
    ical.add("version", "2.0")  # ical version

    for event in filtered_events:
        ical_event = icalendar.Event()
        ical_event.add("summary", ("(Zrušený) " if event.cancelled else "") + event.name)
        start = TZ.localize(datetime.combine(event.date.start, datetime.min.time()))
        ical_event.add("dtstamp", start)
        ical_event.add("dtstart", start.date())

        if event.date.end:
            ical_event.add("dtend", TZ.localize(datetime.combine(event.date.end, datetime.max.time())).date())

        if event.contestants.min.type is None and event.contestants.max.type is None:
            contestants = "ktokoľvek"
        elif event.contestants.min.type is None:
            contestants = format_contestant(event.contestants.max) + " a mladší"
        elif event.contestants.max.type is None:
            contestants = format_contestant(event.contestants.min) + " a starší"
        elif event.contestants.min == event.contestants.max:
            contestants = format_contestant(event.contestants.min)
        else:
            contestants = format_contestant(event.contestants.min) + " – " + format_contestant(event.contestants.max, event.contestants.min)

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
        hash_val = event.name + "_" + event.date.start.strftime("%Y%m%d")
        ical_event.add("uid", sha1(hash_val.encode()).hexdigest() + "@kockatykalendar.sk")
        ical.add_component(ical_event)

    return ical.to_ical()


if args.all:
    for school in ["zs", "ss", "any"]:
        for science in ["mat", "fyz", "inf", "other", "any"]:
            if not path.exists(f"build/{school}/{science}"):
                makedirs(f"build/{school}/{science}")
            output = f"build/{school}/{science}.ics"
            with open(output, "w") as file:
                file.write(generate_ical(school, [science], ["any"]).decode())
            print(PREFIX_OK, f"Generated iCal {output}.", file=sys.stderr)

            for organizer in ["trojsten", "p-mat", "sezam", "riesky", "strom", "siov", "iuventa", "matfyz", "any"]:
                output = f"build/{school}/{science}/{organizer}.ics"
                with open(output, "w") as file:
                    file.write(generate_ical(school, [science], [organizer]).decode())
                print(PREFIX_OK, f"Generated iCal {output}.", file=sys.stderr)

else:
    with args.output as file:
        file.write(generate_ical(args.school, args.science, args.organizer).decode())

    print(PREFIX_OK, "Generated iCal.", file=sys.stderr)
