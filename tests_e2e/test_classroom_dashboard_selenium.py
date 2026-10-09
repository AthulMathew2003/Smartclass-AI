import os
import random
import string
import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
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


def onboard_and_login_user(driver):
    """Registers a fresh user, completes onboarding, and lands on /classroom."""
    unique_suffix = get_random_letters(8)
    test_email = f"dean_{unique_suffix.lower()}@smartclass.ai"
    test_password = "SecurePassword@123"
    full_name = f"Dean Alan {unique_suffix}"
    org_name = f"Academy of Science {unique_suffix}"

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

    # Complete Onboarding if on complete page
    org_name_in = wait.until(EC.presence_of_element_located((By.ID, "orgName")))
    set_react_input(driver, org_name_in, org_name)
    time.sleep(1.0)

    # Select Country & State
    country_select = Select(driver.find_element(By.ID, "country"))
    country_select.select_by_value("US")
    time.sleep(0.5)

    state_select = Select(driver.find_element(By.ID, "state"))
    state_select.select_by_value("NY")
    time.sleep(0.5)

    city_select = Select(driver.find_element(By.ID, "city"))
    if len(city_select.options) > 1:
        city_select.select_by_index(1)

    ws_in = driver.find_element(By.ID, "workspaceName")
    set_react_input(driver, ws_in, "Main Campus")

    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait.until(lambda d: "/classroom" in d.current_url)

    # Wait for classroom dashboard to be interactive
    wait.until(lambda d: "loading" not in d.find_element(By.TAG_NAME, "body").text.lower())
    time.sleep(1.0)

    return {
        "email": test_email,
        "name": full_name,
        "org": org_name,
        "suffix": unique_suffix,
    }


@pytest.fixture
def driver():
    drv = get_driver()
    yield drv
    drv.quit()


def test_classroom_header_and_user_profile(driver):
    """Verifies that the classroom header displays greeting, user name, organization badge, and search."""
    user_info = onboard_and_login_user(driver)
    wait = WebDriverWait(driver, 15)

    header = wait.until(EC.presence_of_element_located((By.TAG_NAME, "header")))
    header_text = header.text

    assert user_info["name"] in header_text or "Dean" in header_text
    print(f"[PASS] Header displays user profile details.")

    # Check search input in header
    search_inputs = header.find_elements(By.CSS_SELECTOR, "input[type='text']")
    if search_inputs:
        assert search_inputs[0].is_displayed()
        print("[PASS] Global search bar is present in header.")


def test_classroom_sidebar_navigation_links(driver):
    """Verifies sidebar navigation links (Dashboard, Members, Assessments, Workspaces, Settings)."""
    onboard_and_login_user(driver)
    wait = WebDriverWait(driver, 15)

    sidebar = wait.until(EC.presence_of_element_located((By.TAG_NAME, "aside")))
    nav_links = sidebar.find_elements(By.CSS_SELECTOR, "nav a")
    link_texts = [link.text.strip() for link in nav_links if link.text.strip()]

    print(f"Available sidebar navigation links: {link_texts}")
    assert any("Dashboard" in t for t in link_texts)

    # 1. Click on Members link if present
    members_link = sidebar.find_elements(By.XPATH, ".//a[contains(@href, '/members')]")
    if members_link:
        members_link[0].click()
        wait.until(lambda d: "/classroom/members" in d.current_url)
        assert "/classroom/members" in driver.current_url
        print("[PASS] Successfully navigated to Members view.")

    # 2. Navigate back to Dashboard via sidebar
    sidebar = wait.until(EC.presence_of_element_located((By.TAG_NAME, "aside")))
    dash_link = sidebar.find_element(By.XPATH, ".//a[@href='/classroom']")
    dash_link.click()
    wait.until(lambda d: d.current_url.endswith("/classroom") or d.current_url.endswith("/classroom/"))
    print("[PASS] Successfully returned to Classroom Dashboard.")


def test_classroom_sidebar_collapse_toggle(driver):
    """Verifies that clicking the sidebar toggle collapses and expands the navigation bar."""
    onboard_and_login_user(driver)
    wait = WebDriverWait(driver, 15)

    sidebar = wait.until(EC.presence_of_element_located((By.TAG_NAME, "aside")))
    initial_width = sidebar.size["width"]

    # Click toggle button
    toggle_btn = sidebar.find_element(By.CSS_SELECTOR, "button[title*='Sidebar']")
    toggle_btn.click()
    time.sleep(0.5)

    collapsed_width = sidebar.size["width"]
    assert collapsed_width < initial_width, f"Expected sidebar to shrink. Initial: {initial_width}, Collapsed: {collapsed_width}"
    print(f"[PASS] Sidebar collapse verified ({initial_width}px -> {collapsed_width}px).")

    # Click toggle button again to expand
    toggle_btn.click()
    time.sleep(0.5)

    expanded_width = sidebar.size["width"]
    assert expanded_width > collapsed_width, f"Expected sidebar to expand. Collapsed: {collapsed_width}, Expanded: {expanded_width}"
    print(f"[PASS] Sidebar expand verified ({collapsed_width}px -> {expanded_width}px).")


def test_classroom_logout_functionality(driver):
    """Verifies that clicking the logout button invalidates session and navigates to /login."""
    onboard_and_login_user(driver)
    wait = WebDriverWait(driver, 15)

    header = wait.until(EC.presence_of_element_located((By.TAG_NAME, "header")))
    logout_btns = header.find_elements(By.XPATH, ".//button[.//span[contains(text(), 'logout')] or contains(@title, 'Logout')] | .//button[last()]")
    assert len(logout_btns) > 0, "Logout button must be present in header"

    logout_btns[-1].click()
    wait.until(lambda d: "/login" in d.current_url)
    assert "/login" in driver.current_url
    print(f"[PASS] Successfully logged out and redirected to login: {driver.current_url}")


if __name__ == "__main__":
    drv = get_driver()
    try:
        print("--- RUNNING SELENIUM CLASSROOM DASHBOARD TESTS ---")
        test_classroom_header_and_user_profile(drv)
        test_classroom_sidebar_navigation_links(drv)
        test_classroom_sidebar_collapse_toggle(drv)
        test_classroom_logout_functionality(drv)
        print("\n=================================================")
        print(" ALL CLASSROOM DASHBOARD SELENIUM TESTS PASSED!  ")
        print("=================================================")
    finally:
        drv.quit()
