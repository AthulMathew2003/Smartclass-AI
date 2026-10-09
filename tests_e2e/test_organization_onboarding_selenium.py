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


def register_new_account(driver):
    """Helper to register a new user and navigate into onboarding."""
    unique_suffix = get_random_letters(8)
    test_email = f"orgtest_{unique_suffix.lower()}@smartclass.ai"
    test_password = "SecurePassword@123"
    full_name = f"Dean Alan {unique_suffix}"

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
    return {
        "email": test_email,
        "password": test_password,
        "suffix": unique_suffix,
    }


def complete_onboarding_form(driver, org_name: str):
    """Helper to fill all required fields in /register/complete and submit."""
    wait = WebDriverWait(driver, 20)
    org_name_in = wait.until(EC.presence_of_element_located((By.ID, "orgName")))
    set_react_input(driver, org_name_in, org_name)
    time.sleep(1.0) # wait for availability check

    # Select Country
    country_select = Select(driver.find_element(By.ID, "country"))
    country_select.select_by_value("US")
    time.sleep(0.5)

    # Select State
    state_select = Select(driver.find_element(By.ID, "state"))
    state_select.select_by_value("NY")
    time.sleep(0.5)

    # Select City
    city_select = Select(driver.find_element(By.ID, "city"))
    if len(city_select.options) > 1:
        city_select.select_by_index(1)

    # Workspace Name
    ws_in = driver.find_element(By.ID, "workspaceName")
    set_react_input(driver, ws_in, "Main Workspace")

    submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_btn.click()


@pytest.fixture
def driver():
    drv = get_driver()
    yield drv
    drv.quit()


def test_onboarding_form_slug_generation_and_geo_chaining(driver):
    """Verifies slug auto-generation and geographic dropdown cascades (Country -> State -> City)."""
    user_data = register_new_account(driver)
    wait = WebDriverWait(driver, 20)

    # Wait for /register/complete page to load
    org_name_in = wait.until(EC.presence_of_element_located((By.ID, "orgName")))
    org_slug_in = driver.find_element(By.ID, "orgSlug")

    # 1. Test auto-slugify
    sample_name = f"Stark Tech Institute {user_data['suffix']}"
    set_react_input(driver, org_name_in, sample_name)
    time.sleep(0.5)

    expected_slug_start = "stark-tech-institute"
    actual_slug = org_slug_in.get_attribute("value")
    assert expected_slug_start in actual_slug
    print(f"[PASS] Auto-slug generation verified: '{actual_slug}'")

    # 2. Test Geographic Dropdown Chaining
    country_select = Select(driver.find_element(By.ID, "country"))
    
    country_select.select_by_value("US")
    time.sleep(0.5)

    state_select = Select(driver.find_element(By.ID, "state"))
    assert len(state_select.options) > 1, "US States should be populated"

    # Select California
    state_select.select_by_value("CA")
    time.sleep(0.5)

    city_select = Select(driver.find_element(By.ID, "city"))
    assert len(city_select.options) > 1, "California Cities should be populated"
    print("[PASS] Geographic country -> state -> city chaining verified.")


def test_successful_complete_onboarding_flow(driver):
    """Tests complete onboarding flow including owner details, organization creation, and workspace setup."""
    user_data = register_new_account(driver)
    wait = WebDriverWait(driver, 20)

    complete_onboarding_form(driver, f"Apex Academy {user_data['suffix']}")

    # Should navigate to classroom dashboard
    wait.until(lambda d: "/classroom" in d.current_url)
    print(f"[PASS] Onboarding completed! Landed at: {driver.current_url}")

    # Wait for loading spinner to finish and dashboard content to render
    wait.until(lambda d: "loading" not in d.find_element(By.TAG_NAME, "body").text.lower() or len(d.find_elements(By.TAG_NAME, "h1")) > 0)
    time.sleep(1.0)

    page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
    assert ("classroom" in page_text or "workspace" in page_text or "dashboard" in page_text or "smartclass" in page_text or "overview" in page_text)
    print("[PASS] Classroom dashboard fully rendered for newly onboarded organization.")


def test_select_organization_screen(driver):
    """Verifies that the /select-org page loads memberships and allows organization selection."""
    user_data = register_new_account(driver)
    wait = WebDriverWait(driver, 20)

    # Complete initial onboarding
    complete_onboarding_form(driver, f"Global University {user_data['suffix']}")
    wait.until(lambda d: "/classroom" in d.current_url)

    # Navigate to /select-org
    driver.get(f"{BASE_URL}/select-org")
    wait.until(lambda d: "/select-org" in d.current_url)

    # Wait for heading
    h1_elem = wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[contains(text(), 'Select Organization')]")))
    assert "Select Organization" in h1_elem.text
    print("[PASS] Select Organization screen rendered with organization cards.")

    # Select the organization card
    org_cards = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "button.ds-card")))
    assert len(org_cards) >= 1
    org_cards[0].click()
    
    wait.until(lambda d: "/classroom" in d.current_url)
    assert "/classroom" in driver.current_url
    print(f"[PASS] Successfully selected organization and entered classroom: {driver.current_url}")


if __name__ == "__main__":
    drv = get_driver()
    try:
        print("--- RUNNING SELENIUM ORGANIZATION ONBOARDING TESTS ---")
        test_onboarding_form_slug_generation_and_geo_chaining(drv)
        test_successful_complete_onboarding_flow(drv)
        test_select_organization_screen(drv)
        print("\n=======================================================")
        print(" ALL ORGANIZATION & ONBOARDING SELENIUM TESTS PASSED! ")
        print("=======================================================")
    finally:
        drv.quit()
