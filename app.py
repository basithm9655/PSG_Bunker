from flask import Flask, render_template, request, jsonify, session
from scraper import ECampusScraper
import math

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    try:
        scraper = ECampusScraper(username, password)
        
        # Get all data
        attendance = scraper.fetch_attendance()
        timetable = scraper.fetch_timetable()
        basic_timetable = scraper.fetch_basic_timetable()
        
        session['attendance_data'] = attendance
        session['timetable_data'] = timetable
        session['basic_timetable'] = basic_timetable
        
        return render_template('dashboard.html', 
                             attendance=attendance,
                             timetable=timetable,
                             basic_timetable=basic_timetable)
                             
    except Exception as e:
        return render_template('index.html', error=str(e))

@app.route('/what_if', methods=['POST'])
def what_if():
    data = request.get_json()
    
    current_hours = int(data['current_hours'])
    current_present = int(data['current_present'])
    future_classes = int(data['future_classes'])
    future_attended = int(data['future_attended'])
    threshold = 75
    
    # Calculate new percentages
    new_total_hours = current_hours + future_classes
    new_total_present = current_present + future_attended
    
    if new_total_hours > 0:
        new_percentage = (new_total_present / new_total_hours) * 100
    else:
        new_percentage = 0
    
    current_percentage = (current_present / current_hours) * 100 if current_hours > 0 else 0
    
    # Calculate bunk/attend requirements
    result = {}
    if new_percentage <= threshold:
        result['classes_to_attend'] = math.ceil(
            (threshold * new_total_hours - new_total_present) / (1 - threshold/100)
        )
        result['status'] = 'need_attend'
    else:
        result['classes_to_bunk'] = math.floor(
            (new_total_present - (threshold/100 * new_total_hours)) / (threshold/100)
        )
        result['status'] = 'can_bunk'
    
    result['new_percentage'] = round(new_percentage, 2)
    result['current_percentage'] = round(current_percentage, 2)
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
