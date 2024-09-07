import requests
import time
import re

# Configuration Variables
DOMAIN = 'calstatela.instructure.com'
TOKEN = '123abc'
TERM_ID = '337'
COURSE_ROLE = 'TeacherEnrollment'

# URL and Headers
BASE_URL = f"https://{DOMAIN}/api/v1"  # Base URL for the Canvas API
HEADERS = {
    'Authorization': f"Bearer {TOKEN}"  # Authorization header using the API token
}

def extract_course_segment(course_str):
    """
    Extracts the course segment (e.g., 'CS') from a course string (e.g., 'CS 1234-56').

    Args:
        course_str (str): The course string.

    Returns:
        str: The extracted course segment, or an empty string if no match is found.
    """
    match = re.search(r'(\b[A-Z]+\b) \d{4}-\d{2}', course_str)  # Regex to match the course segment
    return match.group(1) if match else ''  # Return the segment or an empty string if not found

def fetch_paginated_results(endpoint, headers):
    """
    Fetches all paginated results from a given API endpoint.

    Args:
        endpoint (str): The API endpoint to fetch data from.
        headers (dict): The headers to include in the request.

    Returns:
        list: A list of all results from the paginated API responses.
    """
    current_page = endpoint
    results = []

    while current_page:
        response = requests.get(current_page, headers=headers)  # Send GET request
        response.raise_for_status()  # Check for HTTP errors
        results.extend(response.json())  # Add results from the current page
        links = response.links  # Pagination links
        current_page = links['next']['url'] if 'next' in links else None  # Move to the next page if available

    return results

def clean_sis_id(sis_id):
    """
    Cleans the SIS ID by removing the '_e' suffix if present.

    Args:
        sis_id (str): The SIS ID to clean.

    Returns:
        str: The cleaned SIS ID.
    """
    if sis_id.endswith('_e'):
        return sis_id[:-2]  # Remove the '_e' suffix
    return sis_id

# Start a timer to measure script execution time
start_time = time.time()

# Get all courses for the specified term
courses_endpoint = f"{BASE_URL}/accounts/1/courses?enrollment_term_id={TERM_ID}&per_page=100"
courses = fetch_paginated_results(courses_endpoint, HEADERS)

# Dictionary to store teacher information
teacher_courses = {}

# Iterate over each course
for course in courses:
    # Endpoint to fetch users with the 'teacher' role for the current course
    users_endpoint = f"{BASE_URL}/courses/{course['id']}/enrollments?type[]={COURSE_ROLE}&per_page=100"
    users = fetch_paginated_results(users_endpoint, HEADERS)

    # Process each user
    for user in users:
        login_id = user['user']['login_id']  # Get the login ID
        full_name = user['user']['name']  # Get the full name
        first_name, last_name = full_name.split(' ', 1)  # Split the name into first and last names
        course_segment = extract_course_segment(course['course_code'])  # Extract course segment
        sis_id = user['user'].get('sis_user_id', '')  # Get SIS ID, default to empty string if not present
        sis_id = clean_sis_id(sis_id)  # Clean the SIS ID

        # Store user information in the dictionary
        if login_id not in teacher_courses:
            teacher_courses[login_id] = (first_name, last_name, course_segment, sis_id)

# Write the results to a CSV file
with open("teachers.csv", "w") as file:
    file.write("First Name,Last Name,Login ID,Course Segment,SIS ID\n")  # Write CSV header
    for login_id, (first_name, last_name, course_segment, sis_id) in teacher_courses.items():
        file.write(f"{first_name},{last_name},{login_id},{course_segment},{sis_id}\n")  # Write user data

# Calculate and print the elapsed time
elapsed_time = time.time() - start_time
print(f"Script executed in {elapsed_time:.2f} seconds.")
