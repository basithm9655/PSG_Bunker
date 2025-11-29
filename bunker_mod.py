import math
import requests
from bs4 import BeautifulSoup


THRESHOLD = 0.75  # 75%


def _process_attendance_table(raw_data):
    """
    Convert raw table rows from StudZone attendance page into
    a clean list of dicts + bunker/attend suggestion.
    """
    results = []

    # raw_data[0] is header row, so start from index 1
    for i in range(1, len(raw_data)):
        row = raw_data[i]

        # NOTE: index positions are based on the old PSG table layout.
        # If college changes columns, you only adjust these indices.
        temp = {}

        # course code / name
        temp["course_code"] = row[0]

        # convert numbers safely
        def to_int_safe(x, default=0):
            try:
                return int(x)
            except Exception:
                return default

        temp["total_hours"] = to_int_safe(row[1])
        temp["exemption_hours"] = to_int_safe(row[2])

        # row[3] is usually total absent (depends on psg table)
        temp["total_absent"] = to_int_safe(row[3])
        temp["total_present"] = to_int_safe(row[4])
        temp["percentage_of_attendance"] = to_int_safe(row[5])

        # these are usually date range columns
        temp["attendance_percentage_from"] = row[8] if len(row) > 8 else ""
        temp["attendance_percentage_to"] = row[9] if len(row) > 9 else ""

        # bunker logic
        temp["remark"] = {}

        perc = temp["percentage_of_attendance"]
        total_hours = temp["total_hours"]
        total_present = temp["total_present"]

        if total_hours <= 0:
            # avoid divide-by-zero issues
            temp["remark"]["class_to_attend"] = 0
        else:
            if perc <= 75:
                # how many classes to ATTEND to reach 75%
                # formula: ceil( (0.75*T - P) / (1 - 0.75) )
                need_to_attend = math.ceil(
                    (THRESHOLD * total_hours - total_present) / (1 - THRESHOLD)
                )
                if need_to_attend < 0:
                    need_to_attend = 0
                temp["remark"]["class_to_attend"] = need_to_attend
            else:
                # how many classes can you BUNK and still stay ≥ 75%
                # formula: floor( (P - 0.75*T) / 0.75 )
                can_bunk = math.floor(
                    (total_present - THRESHOLD * total_hours) / THRESHOLD
                )
                if can_bunk < 0:
                    can_bunk = 0
                temp["remark"]["class_to_bunk"] = can_bunk

        results.append(temp)

    return results


def return_attendance(username, pwd):
    """
    Logs into StudZone, fetches attendance table and returns:
    (processed_attendance_data, session)
    or an error string.
    """
    try:
        session = requests.Session()

        # 1) open login page to get VIEWSTATE, etc.
        r = session.get("https://ecampus.psgtech.ac.in/studzone2/")
        loginpage = session.get(r.url)
        soup = BeautifulSoup(loginpage.text, "html.parser")

        viewstate = soup.select("#__VIEWSTATE")[0]["value"]
        eventvalidation = soup.select("#__EVENTVALIDATION")[0]["value"]
        viewstategen = soup.select("#__VIEWSTATEGENERATOR")[0]["value"]

        payload = {
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            "__LASTFOCUS": "",
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstategen,
            "__EVENTVALIDATION": eventvalidation,
            "rdolst": "S",
            "txtusercheck": username,
            "txtpwdcheck": pwd,
            "abcd3": "Login",
        }

        response = session.post(
            url=r.url, data=payload, headers={"Referer": r.url}
        )

        if response.status_code != 200:
            return "Try again after some time"

        # 2) go to attendance page
        defaultpage = "https://ecampus.psgtech.ac.in/studzone2/AttWfPercView.aspx"
        page = session.get(defaultpage)
        soup = BeautifulSoup(page.text, "html.parser")

        table = soup.find("table", attrs={"class": "cssbody"})
        if table is None:
            message_span = soup.find("span", attrs={"id": "Message"})
            if message_span and "On Process" in str(message_span):
                return "Table is being updated"
            return "No attendance table found"

        raw_data = []
        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            cols = [ele.text.strip() for ele in cols]
            raw_data.append([ele for ele in cols if ele])

        processed = _process_attendance_table(raw_data)
        if not processed:
            return "No attendance data found"

        return processed, session

    except Exception:
        return "Try again after some time"


def return_course_title_map(session):
    """
    Old-style "course description" table from timetable page.
    Maps course_code -> course_title
    If the table doesn't exist, returns empty dict.
    """
    url = "https://ecampus.psgtech.ac.in/studzone2/AttWfStudTimtab.aspx"
    page = session.get(url)
    soup = BeautifulSoup(page.text, "html.parser")

    # old table id used in many PSG tools
    table = soup.find("table", attrs={"id": "TbCourDesc"})
    if table is None:
        return {}

    data = []
    rows = table.find_all("tr")
    for row in rows:
        cols = row.find_all("td")
        cols = [ele.text.strip() for ele in cols]
        data.append([ele for ele in cols if ele])

    # data[0] is header
    course_map = {}
    for i in range(1, len(data)):
        row = data[i]
        if len(row) < 2:
            continue
        code = row[0]
        title = row[1]
        course_map[code] = title

    return course_map


def return_weekly_timetable(session):
    """
    Scrape the timetable grid you sent (table id = DtStfTimtab).

    Returns a dict like:
    {
      "periods": ["1", "2", ..., "12"],
      "time_ranges": ["8.30 - 9.20", ...],
      "days": [
        {"day": "MON", "slots": ["", "BE ICE_1 23U101", ...]},
        ...
      ]
    }
    """
    url = "https://ecampus.psgtech.ac.in/studzone2/AttWfStudTimtab.aspx"
    page = session.get(url)
    soup = BeautifulSoup(page.text, "html.parser")

    table = soup.find("table", attrs={"id": "DtStfTimtab"})
    if table is None:
        # timetable not found
        return {}

    rows = table.find_all("tr")
    if len(rows) < 3:
        return {}

    # Row 0: "Period | 1 | 2 | ... | 12"
    header_periods = [td.get_text(strip=True) for td in rows[0].find_all("td")]
    periods = header_periods[1:]  # skip "Period"

    # Row 1: "Day/Time | 8.30 - 9.20 | ..."
    header_times = [td.get_text(strip=True) for td in rows[1].find_all("td")]
    time_ranges = header_times[1:]  # skip "Day/Time"

    days = []
    for row in rows[2:]:
        tds = row.find_all("td")
        if not tds:
            continue

        # first cell = day name (e.g. "MON")
        day_text = tds[0].get_text(strip=True).replace("\xa0", "").strip()
        slots = []

        for cell in tds[1:]:
            # each cell may contain "BE ICE_1<br>23U101" or just &nbsp;
            parts = [s.strip() for s in cell.stripped_strings]
            if not parts:
                slots.append("")
            elif len(parts) == 1:
                slots.append(parts[0])
            else:
                # join both lines: "BE ICE_1 - 23U101"
                slots.append(" - ".join(parts))

        days.append({"day": day_text, "slots": slots})

    return {
        "periods": periods,
        "time_ranges": time_ranges,
        "days": days,
    }
