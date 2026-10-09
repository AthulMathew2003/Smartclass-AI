import os
import random
import string
import time
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

    try:
        driver = webdriver.Chrome(options=options)
    except Exception:
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


def test_login_page_renders_elements(driver):
    """Verifies that all core UI elements on login page are present and visible."""
    driver.get(f"{BASE_URL}/login")
    wait = WebDriverWait(driver, 10)

    email_in = wait.until(EC.visibility_of_element_located((By.ID, "email")))
    pwd_in = driver.find_element(By.ID, "password")
    submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")

    assert email_in.is_displayed()
    assert pwd_in.is_displayed()
    assert submit_btn.is_displayed()
    assert "Sign In" in submit_btn.text or "sign in" in submit_btn.text.lower()
    print("[PASS] Login page elements rendered successfully.")


def test_login_password_visibility_toggle(driver):
    """Verifies that clicking the password toggle switches input type between password and text."""
    driver.get(f"{BASE_URL}/login")
    wait = WebDriverWait(driver, 10)
    pwd_in = wait.until(EC.presence_of_element_located((By.ID, "password")))

    assert pwd_in.get_attribute("type") == "password"

    # Toggle to show password
    toggle_btn = driver.find_element(By.XPATH, "//input[@id='password']/following-sibling::button")
    toggle_btn.click()
    time.sleep(0.3)
    assert pwd_in.get_attribute("type") == "text"

    # Toggle back to hide password
    toggle_btn.click()
    time.sleep(0.3)
    assert pwd_in.get_attribute("type") == "password"
    print("[PASS] Password visibility toggle works correctly.")


def test_login_invalid_credentials(driver):
    """Verifies that submitting wrong credentials displays an appropriate error message."""
    driver.get(f"{BASE_URL}/login")
    wait = WebDriverWait(driver, 10)

    email_in = wait.until(EC.presence_of_element_located((By.ID, "email")))
    pwd_in = driver.find_element(By.ID, "password")
    submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")

    set_react_input(driver, email_in, "nonexistent.user.12345@smartclass.ai")
    set_react_input(driver, pwd_in, "WrongPassword!999")
    submit_btn.click()
    time.sleep(1.2)

    body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
    assert "failed" in body_text or "invalid" in body_text or "credentials" in body_text or "error" in body_text or "not found" in body_text
    print("[PASS] Invalid credentials error displayed correctly.")


def test_login_success(driver):
    """Registers a fresh test user and verifies successful login with valid credentials."""
    unique_suffix = get_random_letters(8)
    test_email = f"logintest_{unique_suffix.lower()}@smartclass.ai"
    test_password = "ValidPassword@123"
    full_name = f"Professor Login {unique_suffix}"

    # 1. Register new test user first
    driver.get(f"{BASE_URL}/register")
    wait = WebDriverWait(driver, 20)

    name_in = wait.until(EC.presence_of_element_located((By.ID, "fullName")))
    email_in = driver.find_element(By.ID, "reg-email")
    pwd_in = driver.find_element(By.ID, "reg-password")
    terms_box = driver.find_element(By.ID, "terms")

    set_react_input(driver, name_in, full_name)
    set_react_input(driver, email_in, test_email)
    time.sleep(1.0)
    set_react_input(driver, pwd_in, test_password)
    if not terms_box.is_selected():
        terms_box.click()

    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait.until(lambda d: d.current_url != f"{BASE_URL}/register")

    # 2. Clear session to simulate fresh login
    driver.delete_all_cookies()
    driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")

    # 3. Perform login
    driver.get(f"{BASE_URL}/login")
    login_email = wait.until(EC.presence_of_element_located((By.ID, "email")))
    login_pwd = driver.find_element(By.ID, "password")
    login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")

    set_react_input(driver, login_email, test_email)
    set_react_input(driver, login_pwd, test_password)
    login_btn.click()

    # Wait for navigation to /classroom, /register/complete or /select-org
    wait.until(lambda d: d.current_url != f"{BASE_URL}/login")
    current_url = driver.current_url
    print(f"[PASS] Successfully logged in! Navigated to: {current_url}")
    assert ("/classroom" in current_url or "/register/complete" in current_url or "/select-org" in current_url)


def test_navigation_to_register_page(driver):
    """Verifies that clicking the 'Create Account' link navigates to the registration page."""
    driver.get(f"{BASE_URL}/login")
    wait = WebDriverWait(driver, 10)

    create_acc_link = wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Create Account")))
    create_acc_link.click()

    wait.until(lambda d: "/register" in d.current_url)
    assert "/register" in driver.current_url
    print(f"[PASS] Navigated to registration page: {driver.current_url}")


if __name__ == "__main__":
    drv = get_driver()
    try:
        print("--- RUNNING SELENIUM LOGIN TESTS ---")
        test_login_page_renders_elements(drv)
        test_login_password_visibility_toggle(drv)
        test_login_invalid_credentials(drv)
        test_login_success(drv)
        test_navigation_to_register_page(drv)
        print("\n======================================")
        print(" ALL SELENIUM LOGIN TESTS PASSED! ")
        print("======================================")
    finally:
        drv.quit()
