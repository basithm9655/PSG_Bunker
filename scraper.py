import requests
from bs4 import BeautifulSoup
import re

class ECampusScraper:
    BASE_URL = "https://ecampus.psgtech.ac.in/studzone2/"
    
    def __init__(self, username, password):
        self.session = requests.Session()
        self.login(username, password)
    
    def login(self, username, password):
        login_page = self.session.get(self.BASE_URL)
        soup = BeautifulSoup(login_page.text, 'html.parser')
        
        view_state = soup.find('input', {'name': '__VIEWSTATE'})['value']
        event_validation = soup.find('input', {'name': '__EVENTVALIDATION'})['value']
        view_state_gen = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value']
        
        login_data = {
            '__VIEWSTATE': view_state,
            '__VIEWSTATEGENERATOR': view_state_gen,
            '__EVENTVALIDATION': event_validation,
            'rdolst': 'S',
            'txtusercheck': username,
            'txtpwdcheck': password,
            'abcd3': 'Login'
        }
        
        response = self.session.post(login_page.url, data=login_data)
        
        if 'Invalid' in response.text:
            raise Exception('Invalid username or password')
    
    def fetch_attendance(self):
        url = f"{self.BASE_URL}AttWfPercView.aspx"
        response = self.session.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        table = soup.find('table', {'class': 'cssbody'})
        if not table:
            raise Exception('Attendance data not available')
        
        attendance_data = []
        rows = table.find_all('tr')[1:]  # Skip header row
        
        for row in rows:
            cols = [col.text.strip() for col in row.find_all('td')]
            if len(cols) >= 10:
                attendance_data.append({
                    'course_code': cols[0],
                    'total_hours': int(cols[1]),
                    'total_present': int(cols[4]),
                    'percentage': int(cols[5]),
                    'last_updated': cols[9]
                })
        
        return attendance_data
    
    def fetch_timetable(self):
        url = f"{self.BASE_URL}AttWfStudTimtab.aspx"
        response = self.session.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        table = soup.find('table', {'id': 'TbCourDesc'})
        if not table:
            raise Exception('Timetable not available')
        
        timetable_data = []
        rows = table.find_all('tr')[1:]  # Skip header row
        
        for row in rows:
            cols = [col.text.strip() for col in row.find_all('td')]
            if len(cols) >= 4:
                timetable_data.append({
                    'course_code': cols[0],
                    'course_name': cols[1],
                    'program': cols[2],
                    'semester': cols[3]
                })
        
        return timetable_data
    
    def fetch_basic_timetable(self):
        # This would need to be customized based on your college's timetable structure
        # Returning mock data as example
        return {
            'days': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
            'periods': [
                {'time': '8:30-9:20', 'subjects': ['Math', 'Physics', 'Chemistry', 'Math', 'English']},
                {'time': '9:20-10:10', 'subjects': ['Physics', 'Chemistry', 'Math', 'Physics', 'Math']},
                {'time': '10:30-11:20', 'subjects': ['Chemistry', 'Math', 'Physics', 'Chemistry', 'Physics']},
                {'time': '11:20-12:10', 'subjects': ['Lab', 'Lab', 'Lab', 'Lab', 'Lab']},
                {'time': '1:00-1:50', 'subjects': ['English', 'Math', 'Chemistry', 'Physics', 'Chemistry']},
                {'time': '1:50-2:40', 'subjects': ['Math', 'Physics', 'English', 'Math', 'Physics']}
            ]
        }

# For detailed timetable parsing (you'll need to adapt this)
def parse_detailed_timetable(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # You'll need to inspect your college's timetable page structure
    # and adjust these selectors accordingly
    timetable_table = soup.find('table', {'class': 'timetable'})
    
    if not timetable_table:
        return None
    
    # Parse logic here based on actual HTML structure
    days = []
    periods = []
    
    # Example parsing (adjust based on actual structure)
    header_row = timetable_table.find('tr')
    day_headers = header_row.find_all('th')[1:]  # Skip time column
    days = [header.text.strip() for header in day_headers]
    
    time_rows = timetable_table.find_all('tr')[1:]
    for row in time_rows:
        cells = row.find_all('td')
        if cells:
            time_slot = cells[0].text.strip()
            subjects = [cell.text.strip() for cell in cells[1:]]
            
            periods.append({
                'time': time_slot,
                'subjects': subjects
            })
    
    return {
        'days': days,
        'periods': periods
    }
