# Canvas Course and Teacher Data Processor

This Python script fetches course and teacher data from the Canvas API, processes the information, and saves it to a CSV file. It handles paginated API responses, retries failed requests, and processes multiple courses concurrently.

## Example Output
'''
First Name,Last Name,Login ID,Course Segment,SIS ID,Term ID
Ethan,Turner,ethan.turner,,123456789,1
Sophia,Ramirez,sophia.ramirez,,223456789,1
'''

## Features

- Fetches all courses from a Canvas instance.
- Retrieves teacher enrollments for each course.
- Extracts and cleans SIS IDs to ensure accuracy.
- Saves progress to a JSON file to resume processing if interrupted.
- Exports teacher data to a CSV file.
- Utilizes concurrent requests to speed up data retrieval.

## Requirements

- Python 3.x
- `requests` library
- `concurrent.futures` library (part of Python's standard library)

## Configuration

1. **DOMAIN**: Canvas domain (e.g., `calstatela.instructure.com`).
2. **TOKEN**: API token for authentication. You can generate this from your Canvas account.
3. **COURSE_ROLE**: The role type to filter enrollments (e.g., `TeacherEnrollment`).
4. **MAX_RETRIES**: Number of retries for failed requests.
5. **BACKOFF_FACTOR**: Backoff factor for retries.
6. **CONCURRENT_REQUESTS**: Number of concurrent requests to make.
7. **PROGRESS_FILE**: File name to save progress (e.g., `canvas_progress.json`).
8. **PROGRESS_UPDATE_INTERVAL**: Interval to update progress.
