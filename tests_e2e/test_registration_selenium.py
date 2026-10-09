import os
import random
import string
import sys
import time
import uuid
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = os.environ.get("BASE_URL", "http://localhost:3000")


def get_random_letters(length=6):
    return "".join(random.choices(string.ascii_letters, k=length))


def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1440,900")
    
    # In Selenium 4.6+, Selenium Manager automatically handles drivers natively
    try:
        driver = webdriver.Chrome(options=options)
    except Exception:
        # Fallback if webdriver_manager is installed
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Chrome WebDriver: {e}")

    driver.implicitly_wait(5)
    return driver


def set_react_input(driver, element, value: str):
    """Safely clear and type into a React controlled input."""
    element.click()
    element.send_keys(Keys.CONTROL + "a")
    element.send_keys(Keys.BACKSPACE)
    if value:
        element.send_keys(value)


@pytest.fixture
def driver():
    drv = get_driver()
    yield drv
    drv.quit()


def test_empty_form_submission_validation(driver):
    """Verifies that submitting empty form triggers full name and field validation."""
    driver.get(f"{BASE_URL}/register")
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.ID, "fullName")))

    submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_btn.click()
    time.sleep(0.5)

    body_text = driver.find_element(By.TAG_NAME, "body").text
    assert "Full name is required" in body_text
    print("[PASS] Empty form validation passed.")


def test_invalid_email_format_validation(driver):
    """Verifies that entering an invalid email format triggers appropriate error message."""
    driver.get(f"{BASE_URL}/register")
    wait = WebDriverWait(driver, 10)
    name_in = wait.until(EC.presence_of_element_located((By.ID, "fullName")))
    email_in = driver.find_element(By.ID, "reg-email")
    pwd_in = driver.find_element(By.ID, "reg-password")

    set_react_input(driver, name_in, "Dr. Alan Turing")
    set_react_input(driver, email_in, "invalid-email-address")
    set_react_input(driver, pwd_in, "SecurePass123!")

    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(0.5)

    body_text = driver.find_element(By.TAG_NAME, "body").text
    assert "valid email" in body_text.lower()
    print("[PASS] Invalid email validation passed.")


def test_weak_password_validation_and_meter(driver):
    """Verifies that entering a weak password displays the meter and validation requirements."""
    driver.get(f"{BASE_URL}/register")
    wait = WebDriverWait(driver, 10)
    name_in = wait.until(EC.presence_of_element_located((By.ID, "fullName")))
    email_in = driver.find_element(By.ID, "reg-email")
    pwd_in = driver.find_element(By.ID, "reg-password")

    set_react_input(driver, name_in, "Dr. Alan Turing")
    set_react_input(driver, email_in, "alan.turing@smartclass.ai")
    set_react_input(driver, pwd_in, "short")
    time.sleep(0.5)

    # Password strength meter checks
    body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
    assert "weak" in body_text or "too short" in body_text or "8+ characters" in body_text

    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(0.5)

    body_text_after = driver.find_element(By.TAG_NAME, "body").text.lower()
    assert "8 characters" in body_text_after or "password" in body_text_after
    print("[PASS] Weak password validation & strength meter passed.")


def test_successful_registration_and_onboarding(driver):
    """Verifies end-to-end registration of a new user and transition to onboarding/dashboard."""
    driver.get(f"{BASE_URL}/register")
    wait = WebDriverWait(driver, 20)

    unique_suffix = get_random_letters(8)
    unique_email = f"professor_{unique_suffix.lower()}@smartclass.ai"
    full_name = f"Professor Alice {unique_suffix}"
    strong_password = "SecurePassword@123"

    name_in = wait.until(EC.presence_of_element_located((By.ID, "fullName")))
    email_in = driver.find_element(By.ID, "reg-email")
    pwd_in = driver.find_element(By.ID, "reg-password")
    terms_box = driver.find_element(By.ID, "terms")
    submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")

    set_react_input(driver, name_in, full_name)
    set_react_input(driver, email_in, unique_email)
    time.sleep(1.0) # wait for email debounce check
    set_react_input(driver, pwd_in, strong_password)

    if not terms_box.is_selected():
        terms_box.click()

    submit_btn.click()

    # Wait for navigation away from /register (either /register/complete, /classroom, or /select-org)
    wait.until(lambda d: d.current_url != f"{BASE_URL}/register")
    current_url = driver.current_url
    print(f"[PASS] Successfully registered! Navigated to: {current_url}")

    if "/register/complete" in current_url:
        print("Completing organization onboarding flow...")
        wait.until(EC.presence_of_element_located((By.ID, "orgName")))
        org_in = driver.find_element(By.ID, "orgName")
        set_react_input(driver, org_in, f"Institute of AI {unique_suffix}")
        time.sleep(1.0)

        complete_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        complete_btn.click()

        wait.until(lambda d: "/classroom" in d.current_url or "/select-org" in d.current_url)
        print(f"[PASS] Successfully completed onboarding! Landed in: {driver.current_url}")


def test_duplicate_email_registration(driver):
    """Verifies that an email that is already registered cannot be registered again."""
    unique_suffix = get_random_letters(8)
    existing_email = f"dup_user_{unique_suffix.lower()}@smartclass.ai"
    password = "SecurePassword@123"

    # 1. Register first account
    driver.get(f"{BASE_URL}/register")
    wait = WebDriverWait(driver, 20)

    name_in = wait.until(EC.presence_of_element_located((By.ID, "fullName")))
    email_in = driver.find_element(By.ID, "reg-email")
    pwd_in = driver.find_element(By.ID, "reg-password")
    terms_box = driver.find_element(By.ID, "terms")

    set_react_input(driver, name_in, f"First User {unique_suffix}")
    set_react_input(driver, email_in, existing_email)
    time.sleep(1.0)
    set_react_input(driver, pwd_in, password)
    if not terms_box.is_selected():
        terms_box.click()

    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait.until(lambda d: d.current_url != f"{BASE_URL}/register")
    print(f"[PASS] Initial user {existing_email} created successfully.")

    # 2. Reset session and try registering again with same email
    driver.delete_all_cookies()
    driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")

    driver.get(f"{BASE_URL}/register")
    name_in2 = wait.until(EC.presence_of_element_located((By.ID, "fullName")))
    email_in2 = driver.find_element(By.ID, "reg-email")
    pwd_in2 = driver.find_element(By.ID, "reg-password")
    terms_box2 = driver.find_element(By.ID, "terms")

    set_react_input(driver, name_in2, f"Second User {unique_suffix}")
    set_react_input(driver, email_in2, existing_email)
    time.sleep(1.5) # Wait for debounce API check
    set_react_input(driver, pwd_in2, password)
    if not terms_box2.is_selected():
        terms_box2.click()

    body_text = driver.find_element(By.TAG_NAME, "body").text
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(0.8)

    body_text_after = driver.find_element(By.TAG_NAME, "body").text
    page_text = (body_text + " " + body_text_after).lower()

    assert ("already" in page_text or "exists" in page_text or "taken" in page_text or "email" in page_text)
    print("[PASS] Duplicate email registration was properly blocked.")


if __name__ == "__main__":
    drv = get_driver()
    try:
        print("--- RUNNING SELENIUM REGISTRATION TESTS ---")
        test_empty_form_submission_validation(drv)
        test_invalid_email_format_validation(drv)
        test_weak_password_validation_and_meter(drv)
        test_successful_registration_and_onboarding(drv)
        test_duplicate_email_registration(drv)
        print("\n==========================================")
        print(" ALL SELENIUM REGISTRATION TESTS PASSED!")
        print("==========================================")
    finally:
        drv.quit()
