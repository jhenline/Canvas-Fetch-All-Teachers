import requests
import time
import re
import csv
import logging
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.exceptions import RequestException
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter


# Configuration Variables
DOMAIN = 'calstatela.instructure.com'  # Canvas domain
TOKEN = '123abc'  # API token for authentication
COURSE_ROLE = 'TeacherEnrollment'  # Role type to filter enrollments
MAX_RETRIES = 5  # Maximum number of retries for failed requests
BACKOFF_FACTOR = 0.3  # Backoff factor for retries
CONCURRENT_REQUESTS = 5  # Number of concurrent requests
PROGRESS_FILE = 'canvas_progress.json'  # File to save progress
PROGRESS_UPDATE_INTERVAL = 500  # Interval to update progress

# URL and Headers
BASE_URL = f"https://{DOMAIN}/api/v1"  # Base URL for API requests
HEADERS = {
    'Authorization': f"Bearer {TOKEN}"  # Authorization header with API token
}

# Set up logging to output information about script execution
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set up a session with retry logic to handle transient errors
session = requests.Session()
retries = Retry(total=MAX_RETRIES,
                backoff_factor=BACKOFF_FACTOR,
                status_forcelist=[429, 500, 502, 503, 504])  # Retry for specific HTTP status codes
session.mount('https://', HTTPAdapter(max_retries=retries))


def extract_course_segment(course_str):
    """
    Extract the course segment (e.g., 'MATH') from the course string.
    Assumes format: 'COURSE_SEGMENT 2024-01'
    """
    match = re.search(r'(\b[A-Z]+\b) \d{4}-\d{2}', course_str)
    return match.group(1) if match else ''


def fetch_paginated_results(endpoint):
    """
    Fetch all results from a paginated API endpoint.
    Continues to fetch until there are no more pages.
    """
    current_page = endpoint
    results = []
    while current_page:
        try:
            response = session.get(current_page, headers=HEADERS, timeout=30)
            response.raise_for_status()
            results.extend(response.json())  # Add results to the list
            links = response.links
            current_page = links['next']['url'] if 'next' in links else None  # Get next page URL
        except RequestException as e:
            logging.error(f"Error fetching data from {current_page}: {str(e)}")
            raise
    return results


def clean_sis_id(sis_id):
    """
    Remove the '_e' suffix from SIS ID if it exists.
    """
    return sis_id[:-2] if sis_id.endswith('_e') else sis_id


def fetch_all_courses():
    """
    Fetch all courses from the API.
    """
    logging.info("Fetching all courses")
    courses_endpoint = f"{BASE_URL}/accounts/1/courses?per_page=100"
    return fetch_paginated_results(courses_endpoint)


def process_course(course):
    """
    Process a single course to extract teacher information.
    Returns a dictionary of teacher details.
    """
    course_id = course['id']
    course_code = course['course_code']
    term_id = course.get('enrollment_term_id', 'Unknown')
    logging.info(f"Processing course {course_id}")

    users_endpoint = f"{BASE_URL}/courses/{course_id}/enrollments?type[]={COURSE_ROLE}&per_page=100"
    users = fetch_paginated_results(users_endpoint)

    course_teachers = {}
    for user in users:
        login_id = user['user']['login_id']
        full_name = user['user']['name']
        first_name, last_name = full_name.split(' ', 1)
        course_segment = extract_course_segment(course_code)
        sis_id = clean_sis_id(user['user'].get('sis_user_id', ''))

        # Map teacher information to their login ID
        course_teachers[login_id] = (first_name, last_name, course_segment, sis_id, term_id)

    return course_teachers


def save_progress(processed_courses, all_teacher_courses):
    """
    Save the progress of processed courses and teachers to a JSON file.
    """
    with open(PROGRESS_FILE, 'w') as f:
        json.dump({
            'processed_courses': list(processed_courses),
            'all_teacher_courses': {k: list(v) for k, v in all_teacher_courses.items()}
        }, f)


def load_progress():
    """
    Load progress from a JSON file if it exists.
    Returns a set of processed courses and a dictionary of all teacher courses.
    """
    try:
        with open(PROGRESS_FILE, 'r') as f:
            data = json.load(f)
            return set(data['processed_courses']), {k: tuple(v) for k, v in data['all_teacher_courses'].items()}
    except FileNotFoundError:
        return set(), {}


def main():
    """
    Main function to coordinate fetching and processing of courses.
    """
    start_time = time.time()

    # Load previously processed courses and teacher data
    processed_courses, all_teacher_courses = load_progress()
    all_courses = fetch_all_courses()  # Fetch all courses
    courses_to_process = [course for course in all_courses if str(course['id']) not in processed_courses]

    total_courses = len(all_courses)
    courses_processed = len(processed_courses)

    logging.info(f"Total courses: {total_courses}, Courses to process: {len(courses_to_process)}")
    print(f"Starting processing. Courses completed: {courses_processed}/{total_courses}")

    # Process courses concurrently
    with ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as executor:
        future_to_course = {executor.submit(process_course, course): course for course in courses_to_process}

        for future in as_completed(future_to_course):
            course = future_to_course[future]
            try:
                course_results = future.result()
                all_teacher_courses.update(course_results)
                processed_courses.add(str(course['id']))
                courses_processed += 1

                # Print progress and save
                if courses_processed % PROGRESS_UPDATE_INTERVAL == 0:
                    print(f"Courses completed: {courses_processed}/{total_courses}")

                save_progress(processed_courses, all_teacher_courses)
            except Exception as exc:
                logging.error(f'Course {course["id"]} generated an exception: {exc}')

    # Save all teacher data to a CSV file
    with open("all_teachers.csv", "w", newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["First Name", "Last Name", "Login ID", "Course Segment", "SIS ID", "Term ID"])
        for login_id, (first_name, last_name, course_segment, sis_id, term_id) in all_teacher_courses.items():
            writer.writerow([first_name, last_name, login_id, course_segment, sis_id, term_id])

    elapsed_time = time.time() - start_time
    print(f"\nAll courses processed. Total courses completed: {courses_processed}/{total_courses}")
    logging.info(f"Script executed in {elapsed_time:.2f} seconds.")


if __name__ == "__main__":
    main()
