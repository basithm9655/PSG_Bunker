from flask import Flask, render_template, request, jsonify, session
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import math

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

def parse_timetable(html: str):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="timetable-table")
    if table is None:
        raise ValueError("Could not find timetable table")

    thead = table.find("thead")
    tbody = table.find("tbody")

    header_rows = thead.find_all("tr")
    time_row = header_rows[1]
    time_cells = time_row.find_all("td", class_="ClassHour")
    times = [td.get_text(strip=True) for td in time_cells]

    timetable = []
    days_order = []

    for day_row in tbody.find_all("tr"):
        day_th = day_row.find("th")
        if day_th is None:
            continue

        day_name = day_th.get_text(strip=True)
        days_order.append(day_name)

        period_index = 0

        for cell in day_row.find_all("td"):
            colspan = int(cell.get("colspan", 1))
            cell_text = cell.get_text(strip=True)

            is_free = (cell_text == "-")
            subject_code = None
            subject_name = None

            if not is_free:
                code_tag = cell.find("b")
                if code_tag:
                    subject_code = code_tag.get_text(strip=True)

                name_tag = cell.find("span", class_="tooltip-text")
                if name_tag:
                    subject_name = name_tag.get_text(strip=True)
                else:
                    subject_name = cell_text

            for _ in range(colspan):
                if period_index >= len(times):
                    break

                timetable.append({
                    "day": day_name,
                    "period": period_index + 1,
                    "time": times[period_index],
                    "code": subject_code,
                    "subject": subject_name,
                    "is_free": is_free,
                })
                period_index += 1

    return timetable, days_order

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/timetable', methods=['GET', 'POST'])
def timetable():
    if request.method == 'POST':
        try:
            # For demo purposes, we'll use sample HTML
            # In real implementation, you would fetch from ecampus
            sample_html = """
            <table class="timetable-table">
                <thead>
                    <tr><th colspan="9">Time Table</th></tr>
                    <tr>
                        <th>Day</th>
                        <td class="ClassHour">8:30-9:20</td>
                        <td class="ClassHour">9:20-10:10</td>
                        <td class="ClassHour">10:30-11:20</td>
                        <td class="ClassHour">11:20-12:10</td>
                        <td class="ClassHour">1:00-1:50</td>
                        <td class="ClassHour">1:50-2:40</td>
                        <td class="ClassHour">2:40-3:30</td>
                        <td class="ClassHour">3:30-4:20</td>
                    </tr>
                </thead>
                <tbody>
                    <tr><th>Monday</th>
                        <td>23U101<br><span class="tooltip-text">Mathematics</span></td>
                        <td>23U102<br><span class="tooltip-text">Physics</span></td>
                        <td>-</td>
                        <td>23U103<br><span class="tooltip-text">Chemistry</span></td>
                        <td colspan="2">23U104L<br><span class="tooltip-text">Physics Lab</span></td>
                        <td>23U105<br><span class="tooltip-text">Programming</span></td>
                        <td>-</td>
                    </tr>
                    <tr><th>Tuesday</th>
                        <td>23U102<br><span class="tooltip-text">Physics</span></td>
                        <td>23U101<br><span class="tooltip-text">Mathematics</span></td>
                        <td>-</td>
                        <td>23U105<br><span class="tooltip-text">Programming</span></td>
                        <td colspan="3">23U106L<br><span class="tooltip-text">Programming Lab</span></td>
                        <td>-</td>
                    </tr>
                </tbody>
            </table>
            """
            
            timetable_data, days_order = parse_timetable(sample_html)
            session['timetable_data'] = timetable_data
            session['days_order'] = days_order
            
            # Initialize attendance data
            attendance_data = {}
            for item in timetable_data:
                if not item['is_free'] and item['code']:
                    if item['code'] not in attendance_data:
                        attendance_data[item['code']] = {
                            'subject': item['subject'],
                            'total_classes': 0,
                            'attended': 0,
                            'percentage': 0
                        }
            
            session['attendance_data'] = attendance_data
            
            return render_template('timetable.html', 
                                 timetable_data=timetable_data,
                                 days_order=days_order,
                                 attendance_data=attendance_data)
            
        except Exception as e:
            return render_template('index.html', error=str(e))
    
    return render_template('timetable.html')

@app.route('/update_attendance', methods=['POST'])
def update_attendance():
    data = request.get_json()
    subject_code = data.get('subject_code')
    action = data.get('action')
    
    attendance_data = session.get('attendance_data', {})
    
    if subject_code in attendance_data:
        if action == 'bunk':
            attendance_data[subject_code]['total_classes'] += 1
        elif action == 'attend':
            attendance_data[subject_code]['total_classes'] += 1
            attendance_data[subject_code]['attended'] += 1
        
        # Calculate percentage
        total = attendance_data[subject_code]['total_classes']
        attended = attendance_data[subject_code]['attended']
        if total > 0:
            attendance_data[subject_code]['percentage'] = round((attended / total) * 100, 2)
    
    session['attendance_data'] = attendance_data
    return jsonify(attendance_data)

@app.route('/reset_attendance', methods=['POST'])
def reset_attendance():
    attendance_data = session.get('attendance_data', {})
    for subject in attendance_data:
        attendance_data[subject]['total_classes'] = 0
        attendance_data[subject]['attended'] = 0
        attendance_data[subject]['percentage'] = 0
    
    session['attendance_data'] = attendance_data
    return jsonify(attendance_data)

@app.route('/get_bunker_suggestions', methods=['POST'])
def get_bunker_suggestions():
    data = request.get_json()
    threshold = float(data.get('threshold', 75))
    
    attendance_data = session.get('attendance_data', {})
    suggestions = {}
    
    for subject_code, data in attendance_data.items():
        if data['total_classes'] > 0:
            current_percentage = data['percentage']
            total_classes = data['total_classes']
            attended = data['attended']
            
            if current_percentage > threshold:
                # Can bunk some classes
                max_bunk = math.floor((attended - (threshold/100 * total_classes)) / (threshold/100))
                suggestions[subject_code] = {
                    'subject': data['subject'],
                    'current_percentage': current_percentage,
                    'can_bunk': max(0, max_bunk),
                    'message': f'You can bunk up to {max_bunk} classes' if max_bunk > 0 else 'Maintain current attendance'
                }
            else:
                # Need to attend more classes
                needed_attend = math.ceil(((threshold/100 * total_classes) - attended) / (1 - threshold/100))
                suggestions[subject_code] = {
                    'subject': data['subject'],
                    'current_percentage': current_percentage,
                    'need_attend': max(0, needed_attend),
                    'message': f'You need to attend {needed_attend} more classes'
                }
    
    return jsonify(suggestions)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)