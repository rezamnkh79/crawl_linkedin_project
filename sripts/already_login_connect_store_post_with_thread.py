import csv
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import redis
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class LinkedInScraper:
    def __init__(self, username, password, redis_client):
        self.username = username
        self.password = password
        self.driver = self.setup_driver()
        self.redis_client = redis_client
        self.is_logged_in = False
        self.session_cookie = None

    def setup_driver(self):
        """Set up the Chrome options and WebDriver."""
        options = Options()
        options.headless = False  # Set to True to run in headless mode
        driver = webdriver.Chrome(options=options)  # Ensure you have the ChromeDriver installed and in your PATH
        return driver

    def load_session(self):
        """Load session from Redis."""
        session_key = f"linkedin_session:{self.username}"
        self.session_cookie = self.redis_client.get(session_key)

        if self.session_cookie:
            self.driver.get("https://www.linkedin.com")
            self.driver.add_cookie({
                'name': 'li_at',
                'value': self.session_cookie.decode('utf-8'),
                'domain': '.linkedin.com'
            })
            self.driver.refresh()
            self.check_login()
        else:
            print("No session found in Redis. Proceeding to login.")

    def check_login(self):
        """Check if already logged in by looking for a specific element on the home page."""
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "global-nav-search"))
            )
            self.is_logged_in = True
            print("Already logged in.")
        except Exception:
            print("Not logged in. Proceeding to login.")

    def login(self):
        """Log in to LinkedIn."""
        if self.is_logged_in:
            return

        self.driver.get("https://www.linkedin.com/login")
        username_input = WebDriverWait(self.driver, 500).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        username_input.send_keys(self.username)
        time.sleep(1)

        password_input = self.driver.find_element(By.ID, "password")
        password_input.send_keys(self.password)
        time.sleep(1)

        login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()

        WebDriverWait(self.driver, 500).until(
            EC.presence_of_element_located((By.ID, "global-nav-search"))
        )
        time.sleep(2)

        for cookie in self.driver.get_cookies():
            if cookie['name'] == 'li_at':
                self.session_cookie = cookie['value']
                session_key = f"linkedin_session:{self.username}"
                self.redis_client.set(session_key, self.session_cookie)
                print("Session cookie stored in Redis.")

    def scrape_profiles(self):
        """Navigate to My Network page and scrape profiles."""
        # self.driver.get("https://www.linkedin.com/mynetwork/grow/?skipRedirect=true")
        self.driver.get(
            "https://www.linkedin.com/search/results/people/?keywords=data scientist&origin=SWITCH_SEARCH_VERTICAL&searchId=faf8d963-0e13-4129-b722-41f5f9ffae8c&sid=4Co")
        time.sleep(5)  # Wait for the page to load

        # Find profile links
        profile_links = self.driver.find_elements(By.XPATH, "//a[contains(@class, 'app-aware-link')]")

        # Collect the first 10 profile URLs
        profiles = [link.get_attribute('href') for link in profile_links[7:17]]

        # Scrape profiles concurrently
        with ThreadPoolExecutor(max_workers=1) as executor:
            futures = [executor.submit(self.scrape_profile, url) for url in profiles]
            for future in as_completed(futures):
                try:
                    profile_data = future.result()
                    if profile_data:
                        self.write_profile_to_csv(profile_data)
                except Exception as e:
                    print(f"Error scraping profile: {e}")

    def scrape_profile(self, profile_url):
        """Scrape individual profile data."""
        self.driver.execute_script(f"window.open('{profile_url}', '_blank');")
        self.driver.switch_to.window(self.driver.window_handles[-1])
        time.sleep(3)  # Allow the profile page to load

        # Click "Show all posts" button if available
        button = None
        show_all_posts_buttons = self.driver.find_elements(By.XPATH, "//span[contains(text(), '')]/..")
        for x in show_all_posts_buttons:
            if x.text.__contains__("Show all posts"):
                button = x
        try:
            if button is not None:
                button.click()
                time.sleep(3)  # Wait for posts to load
        except Exception as e:
            print(f"Error clicking 'Show all posts' button: {e}")

        # Parse profile data
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        try:
            name = soup.find('h1').get_text(strip=True) if soup.find('h1') else "N/A"
            headline = soup.find('h2').get_text(strip=True) if soup.find('h2') else "N/A"
            location = soup.find('span', class_='top-card__flavor').get_text(strip=True) if soup.find('span',
                                                                                                      class_='top-card__flavor') else "N/A"

            # Fetch posts
            posts = soup.find_all('li', class_="profile-creator-shared-feed-update__container")
            post_data = []
            for post in posts:
                post_text = post.find('span', class_='break-words').get_text(strip=True) if post.find('span',
                                                                                                      class_='break-words') else "No text"
                post_data.append(post_text)

            profile_data = {
                'name': name,
                'headline': headline,
                'location': location if location else "",
                'profile_link': profile_url,
                'posts': post_data
            }

            self.write_profile_to_csv(profile_data)

        except Exception as e:
            print(f"Error scraping profile: {e}")
        finally:
            self.driver.close()  # Close the profile tab
            self.driver.switch_to.window(self.driver.window_handles[0])  # Switch back to the main tab

    def write_profile_to_csv(self, profile_data):
        """Write profile data to a CSV file."""
        filename = 'profiles.csv'
        with open(filename, mode='a', newline='', encoding='utf-8') as csv_file:
            fieldnames = ['name', 'headline', 'location', 'profile_link', 'posts']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writerow(profile_data)

    def connect_to_new_people(self):
        """Send connection requests to new people."""
        try:
            self.driver.get("https://www.linkedin.com/mynetwork/grow/?skipRedirect=true")
            time.sleep(3)

            connect_buttons = self.driver.find_elements(By.XPATH,
                                                        "//button[contains(@aria-label, 'Invite') and contains(@class, 'mn-person-card__person-btn')]")

            for button in connect_buttons[:50]:
                try:
                    button.click()
                    time.sleep(1)

                    send_button = WebDriverWait(self.driver, 500).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'Send now')]"))
                    )
                    send_button.click()
                    print("Connection request sent.")
                    time.sleep(random.uniform(5, 15))
                except Exception as e:
                    print(f"Could not send connection request: {e}")
        finally:
            self.driver.quit()


def run_scraper(username, password, redis_client):
    """Function to create and run a LinkedIn scraper."""
    scraper = LinkedInScraper(username, password, redis_client)
    scraper.load_session()
    if not scraper.is_logged_in:
        scraper.login()
    scraper.scrape_profiles()  # Use the updated method for scraping profiles
    scraper.connect_to_new_people()


if __name__ == '__main__':
    username_str = "alimardan200095@gmail.com"
    password_str = "42184433"
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
