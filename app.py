from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import requests
from bs4 import BeautifulSoup
import re
import math
from datetime import datetime
import json
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

# Constants
ECAMPUS_URL = "https://ecampus.psgtech.ac.in/studzone2/"
ATTENDANCE_PAGE_URL = "https://ecampus.psgtech.ac.in/studzone2/AttWfPercView.aspx"
TIMETABLE_PAGE_URL = "https://ecampus.psgtech.ac.in/studzone2/AttWfStudTimtab.aspx"

class BunkerScraper:
    def __init__(self, username, password):
        self.session = requests.Session()
        self.username = username
        self.password = password
        self.logged_in = False
        
    def login(self):
        try:
            login_page = self.session.get(ECAMPUS_URL)
            soup = BeautifulSoup(login_page.text, 'html.parser')
            
            view_state = soup.select("#__VIEWSTATE")[0]["value"]
            event_validation = soup.select("#__EVENTVALIDATION")[0]["value"]
            view_state_gen = soup.select("#__VIEWSTATEGENERATOR")[0]["value"]
            
            login_data = {
                "__EVENTTARGET": "",
                "__EVENTARGUMENT": "",
                "__LASTFOCUS": "",
                "__VIEWSTATE": view_state,
                "__VIEWSTATEGENERATOR": view_state_gen,
                "__EVENTVALIDATION": event_validation,
                "rdolst": "S",
                "txtusercheck": self.username,
                "txtpwdcheck": self.password,
                "abcd3": "Login",
            }
            
            response = self.session.post(
                url=login_page.url,
                data=login_data,
                headers={"Referer": login_page.url}
            )
            
            if "Invalid" in response.text:
                return False, "Invalid username or password"
                
            self.logged_in = True
            return True, "Login successful"
            
        except Exception as e:
            return False, f"Login error: {str(e)}"
    
    def get_attendance(self):
        if not self.logged_in:
            return None, "Not logged in"
            
        try:
            attendance_page = self.session.get(ATTENDANCE_PAGE_URL)
            soup = BeautifulSoup(attendance_page.text, 'html.parser')
            
            table = soup.find("table", attrs={"class": "cssbody"})
            if not table:
                message = str(soup.find("span", attrs={"id": "Message"}))
                if "On Process" in message:
                    return None, "Attendance update in progress"
                return None, "No attendance data found"
            
            data = []
            rows = table.find_all("tr")
            for row in rows:
                cols = row.find_all("td")
                cols = [ele.text.strip() for ele in cols]
                data.append([ele for ele in cols if ele])
            
            attendance_data = []
            for item in data[1:]:
                if len(item) >= 10:
                    course_data = {
                        'course_code': item[0],
                        'total_hours': int(item[1]),
                        'exemption_hours': int(item[2]),
                        'total_absent': int(item[3]),
                        'total_present': int(item[4]),
                        'percentage': int(item[5]),
                        'percentage_with_exemp': int(item[6]),
                        'attendance_from': item[8],
                        'attendance_to': item[9]
                    }
                    
                    # Calculate bunk/attend recommendation
                    threshold = session.get('threshold', 75) / 100
                    if course_data['percentage'] <= 75:
                        course_data['classes_to_attend'] = math.ceil(
                            (threshold * course_data['total_hours'] - course_data['total_present']) / (1 - threshold)
                        )
                        course_data['action'] = 'attend'
                    else:
                        course_data['classes_to_bunk'] = math.floor(
                            (course_data['total_present'] - (threshold * course_data['total_hours'])) / threshold
                        )
                        course_data['action'] = 'bunk'
                    
                    attendance_data.append(course_data)
            
            return attendance_data, "Success"
            
        except Exception as e:
            return None, f"Error fetching attendance: {str(e)}"
    
    def get_timetable(self):
        if not self.logged_in:
            return None, "Not logged in"
            
        try:
            timetable_page = self.session.get(TIMETABLE_PAGE_URL)
            soup = BeautifulSoup(timetable_page.text, 'html.parser')
            
            table = soup.find("table", attrs={"id": "DtStfTimtab"})
            if not table:
                return None, "No timetable data found"
            
            # Parse timetable
            timetable_data = {}
            rows = table.find_all("tr")[2:]  # Skip header rows
            
            days = ["MON", "TUE", "WED", "THU", "FRI"]
            time_slots = [
                "8:30-9:20", "9:20-10:10", "10:30-11:20", "11:20-12:10",
                "1:40-2:30", "2:30-3:20", "3:30-4:20", "4:20-5:10",
                "5:30-6:20", "6:20-7:10", "7:15-8:05", "8:05-8:55"
            ]
            
            for i, row in enumerate(rows):
                if i >= len(days):
                    break
                    
                day = days[i]
                timetable_data[day] = {}
                
                cells = row.find_all("td")[1:13]  # Skip day cell, get period cells
                for j, cell in enumerate(cells):
                    if j < len(time_slots):
                        cell_text = cell.get_text(strip=True)
                        if cell_text and cell_text != "&nbsp;":
                            # Extract course code and name
                            parts = cell_text.split('\n')
                            if len(parts) >= 2:
                                course_name = parts[0].strip()
                                course_code = parts[1].strip()
                                timetable_data[day][time_slots[j]] = {
                                    'course_name': course_name,
                                    'course_code': course_code
                                }
            
            return timetable_data, "Success"
            
        except Exception as e:
            return None, f"Error fetching timetable: {str(e)}"

# Routes
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    scraper = BunkerScraper(username, password)
    success, message = scraper.login()
    
    if success:
        session['username'] = username
        session['scraper'] = {
            'session_cookies': dict(scraper.session.cookies),
            'logged_in': True
        }
        session['manual_attendance'] = {}
        session['threshold'] = 75  # Default threshold
        return jsonify({'success': True, 'redirect': url_for('dashboard')})
    else:
        return jsonify({'success': False, 'message': message})

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('index'))
    
    # Restore scraper session
    scraper_data = session.get('scraper', {})
    scraper = BunkerScraper(session['username'], '')
    if scraper_data.get('logged_in'):
        scraper.session.cookies.update(scraper_data['session_cookies'])
        scraper.logged_in = True
    
    # Get attendance data
    attendance_data, att_message = scraper.get_attendance()
    
    # Merge with manual attendance if any
    manual_data = session.get('manual_attendance', {})
    if manual_data and attendance_data:
        for course in attendance_data:
            if course['course_code'] in manual_data:
                manual = manual_data[course['course_code']]
                course['total_hours'] += manual.get('additional_hours', 0)
                course['total_present'] += manual.get('additional_present', 0)
                course['percentage'] = round(
                    (course['total_present'] / course['total_hours']) * 100, 2
                ) if course['total_hours'] > 0 else 0
    
    # Calculate overall stats
    overall_stats = {
        'total_courses': len(attendance_data) if attendance_data else 0,
        'average_attendance': 0,
        'safe_courses': 0,
        'warning_courses': 0,
        'danger_courses': 0
    }
    
    if attendance_data:
        total_percentage = sum(course['percentage'] for course in attendance_data)
        overall_stats['average_attendance'] = round(total_percentage / len(attendance_data), 2)
        
        threshold = session.get('threshold', 75)
        for course in attendance_data:
            if course['percentage'] >= threshold + 5:
                overall_stats['safe_courses'] += 1
            elif course['percentage'] >= threshold:
                overall_stats['warning_courses'] += 1
            else:
                overall_stats['danger_courses'] += 1
    
    return render_template('dashboard.html', 
                         attendance_data=attendance_data,
                         overall_stats=overall_stats,
                         message=att_message)

@app.route('/timetable')
def timetable():
    if 'username' not in session:
        return redirect(url_for('index'))
    
    scraper_data = session.get('scraper', {})
    scraper = BunkerScraper(session['username'], '')
    if scraper_data.get('logged_in'):
        scraper.session.cookies.update(scraper_data['session_cookies'])
        scraper.logged_in = True
    
    timetable_data, message = scraper.get_timetable()
    return render_template('timetable.html', timetable_data=timetable_data, message=message)

@app.route('/settings')
def settings():
    if 'username' not in session:
        return redirect(url_for('index'))
    return render_template('settings.html', threshold=session.get('threshold', 75))

@app.route('/update_threshold', methods=['POST'])
def update_threshold():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    threshold = request.json.get('threshold', 75)
    session['threshold'] = threshold
    return jsonify({'success': True, 'message': 'Threshold updated'})

@app.route('/update_manual_attendance', methods=['POST'])
def update_manual_attendance():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    data = request.json
    course_code = data.get('course_code')
    additional_hours = data.get('additional_hours', 0)
    additional_present = data.get('additional_present', 0)
    
    manual_data = session.get('manual_attendance', {})
    manual_data[course_code] = {
        'additional_hours': additional_hours,
        'additional_present': additional_present,
        'last_updated': datetime.now().isoformat()
    }
    session['manual_attendance'] = manual_data
    
    return jsonify({'success': True, 'message': 'Manual attendance updated'})

@app.route('/clear_manual_attendance', methods=['POST'])
def clear_manual_attendance():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    session['manual_attendance'] = {}
    return jsonify({'success': True, 'message': 'Manual attendance cleared'})

@app.route('/bunk_planner', methods=['POST'])
def bunk_planner():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    data = request.json
    course_code = data.get('course_code')
    planned_bunks = data.get('planned_bunks', 0)
    
    # Get current attendance data
    scraper_data = session.get('scraper', {})
    scraper = BunkerScraper(session['username'], '')
    if scraper_data.get('logged_in'):
        scraper.session.cookies.update(scraper_data['session_cookies'])
        scraper.logged_in = True
    
    attendance_data, _ = scraper.get_attendance()
    if not attendance_data:
        return jsonify({'success': False, 'message': 'No attendance data'})
    
    # Find the course and calculate impact
    course = next((c for c in attendance_data if c['course_code'] == course_code), None)
    if not course:
        return jsonify({'success': False, 'message': 'Course not found'})
    
    current_percentage = course['percentage']
    new_present = course['total_present']
    new_total = course['total_hours'] + planned_bunks
    
    # Calculate new percentage
    new_percentage = round((new_present / new_total) * 100, 2) if new_total > 0 else 0
    
    threshold = session.get('threshold', 75)
    status = "safe" if new_percentage >= threshold else "warning" if new_percentage >= threshold - 5 else "danger"
    
    return jsonify({
        'success': True,
        'current_percentage': current_percentage,
        'new_percentage': new_percentage,
        'status': status,
        'can_bunk': new_percentage >= threshold
    })

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
