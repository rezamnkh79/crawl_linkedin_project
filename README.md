# LinkedIn Scraper

This project is a LinkedIn scraper that uses Selenium with Stealth to bypass bot detection and scrape profile information from LinkedIn. It supports storing session cookies in Redis to avoid logging in repeatedly and utilizes threading for concurrent scraping.

## Features

- **Stealth Mode:** Uses `selenium-stealth` to avoid detection by LinkedIn.
- **Session Management:** Stores session cookies in Redis to reuse sessions.
- **Profile Scraping:** Scrapes LinkedIn profiles for information such as name, headline, location, and posts.
- **CSV Export:** Saves scraped profile data into a CSV file.
- **Connection Requests:** Automatically sends connection requests to new people on LinkedIn.

## Requirements

- Python 3.6+
- Redis server
- Chrome WebDriver
- Google Chrome browser

## Installation

1. **Clone the repository:**

    ```bash
    git clone https://github.com/your-username/linkedin-scraper.git
    cd linkedin-scraper
    ```

2. **Install the required Python packages:**

    ```bash
    pip install -r requirements.txt
    ```

3. **Install Redis server:**

    Follow the instructions [here](https://redis.io/download) to install Redis on your machine.

4. **Download Chrome WebDriver:**

    Download the Chrome WebDriver from [here](https://sites.google.com/a/chromium.org/chromedriver/downloads) and ensure it is in your system's PATH.

## Configuration

Update the `username_str` and `password_str` variables in `linkedin_scraper.py` with your LinkedIn login credentials.

## Usage

1. **Run the scraper:**

    ```bash
    python linkedin_scraper.py
    ```

    This will start the LinkedIn scraper, log in using the provided credentials, and begin scraping profiles.

## Code Overview

### LinkedInScraper Class

- **`__init__(self, username, password, redis_client)`**: Initializes the scraper with LinkedIn credentials and Redis client.
- **`setup_driver(self)`**: Sets up the Chrome WebDriver with stealth mode.
- **`load_session(self)`**: Loads the session from Redis.
- **`check_login(self)`**: Checks if the user is already logged in.
- **`login(self)`**: Logs in to LinkedIn.
- **`scrape_profiles(self)`**: Scrapes profile information.
- **`scrape_profile(self, profile_url)`**: Scrapes individual profile data.
- **`write_profile_to_csv(self, profile_data)`**: Writes profile data to a CSV file.
- **`connect_to_new_people(self)`**: Sends connection requests to new people.

### Functions

- **`run_scraper(username, password, redis_client)`**: Creates and runs a LinkedIn scraper instance.

## Example

```python
if __name__ == '__main__':
    username_str = "your-email@example.com"
    password_str = "yourpassword"
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    num_threads = 1

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        for i in range(num_threads):
            futures.append(executor.submit(run_scraper, username_str, password_str, redis_client))

        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"An error occurred: {e}")
