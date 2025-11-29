from flask import Flask, render_template, request
from bunker_mod import (
    return_attendance,
    return_course_title_map,
    return_weekly_timetable,
)

app = Flask(__name__)
app.secret_key = "super-secret-change-me"  # any random string


@app.route("/", methods=["GET"])
def home():
    # first load: only show login form
    return render_template("home.html")


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("usr", "").strip()
    password = request.form.get("pwd", "").strip()

    if not username or not password:
        # show alert using output.html logic
        return render_template(
            "output.html",
            load=False,
            text="Please enter both Roll Number and Password",
        )

    result = return_attendance(username, password)

    # if result is string => error
    if isinstance(result, str):
        return render_template("output.html", load=False, text=result)

    # else we get (data, session)
    attendance_data, session = result

    # map course codes -> titles (if available)
    time_table = return_course_title_map(session)

    # get weekly timetable grid from DtStfTimtab
    weekly_timetable = return_weekly_timetable(session)

    # last updated date from first course (safe check)
    if attendance_data:
        last_date_updated = attendance_data[0].get(
            "attendance_percentage_to", ""
        )
    else:
        last_date_updated = ""

    return render_template(
        "output.html",
        load=True,
        data=attendance_data,
        time_table=time_table,
        weekly_timetable=weekly_timetable,
        last_date_updated=last_date_updated,
        text="",
    )


if __name__ == "__main__":
    app.run(debug=True)
