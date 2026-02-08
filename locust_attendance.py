from locust import HttpUser, task, between
import re

class AttendanceLoadTester(HttpUser):
    wait_time = between(1, 2)
    host = "http://localhost:8000"

    def on_start(self):
        """ Log in before starting tasks """
        self.login()

    def login(self):
        # 1. Get the login page to retrieve the CSRF token
        response = self.client.get("/")
        csrf_token = self.extract_csrf_token(response.text)
        
        # 2. Post login credentials
        # Using the admin user found: admin.yahvi70
        # Password from generate_heavy_data.py is 'password123'
        self.client.post("/", {
            "username": "admin.yahvi70",
            "password": "password123",
            "csrfmiddlewaretoken": csrf_token
        }, headers={"Referer": self.host + "/"})

    def extract_csrf_token(self, html):
        match = re.search(r'name="csrfmiddlewaretoken" value="(.+?)"', html)
        if match:
            return match.group(1)
        return ""

    @task
    def view_attendance_list(self):
        """ Testing the attendance list page specifically """
        with self.client.get("/attendance/list/", catch_response=True) as response:
            if response.status_code == 200:
                if "Attendance History" in response.text or "Attendance List" in response.text:
                    response.success()
                else:
                    response.failure("Logged in but could not see attendance list content")
            else:
                response.failure(f"Failed to load attendance list: {response.status_code}")

    @task(2)
    def view_attendance_with_filters(self):
        """ Simulate a user applying a filter (e.g., searching for a name) """
        # Random search query to simulate load
        self.client.get("/attendance/list/?name=worker&site=&start_date=&end_date=")
