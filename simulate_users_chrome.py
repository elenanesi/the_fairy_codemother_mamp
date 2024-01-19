from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from multiprocessing import Process
import time
import datetime
import warnings
import random
import sched
import sys


from elena_util import *

# Suppress all warnings for logs
warnings.filterwarnings("ignore")

# --- GLOBAL VARS ---- #

# page category options
page_categories = ["home", "category", "product"]
# product category options
product_categories = ["apples", "kiwis", "oranges"]
# path options
path_functions = ["bounce","engaged", "product", "add_to_cart"]
# run headless by default
HEADLESS = 1
# number of users and sessions to run at every execution of the script
NR_USERS = 50
#location of the chrome driver
CHROME_DRIVER = '/Users/elenanesi/Desktop/Workspace/web-drivers/chromedriver' #using Canary driver
# Base URL for navigation, my localhost website
base_url = "http://www.thefairycodemother.com/demo_project/"
# get info from demo_input.json file to get the necessary input for paths (CVR and distribution)
os.chdir('/Users/elenanesi/Workspace/user-simulation/')
if os.path.exists("demo_input.json"):
    with open("demo_input.json", 'r') as file:
        demo_input = json.load(file)
else:
    print ("demo_input.json is missing!!")
    with open("/Users/elenanesi/Workspace/user-simulation/logfile.log", "a") as log_file:
        log_file.write(f"Script failed because demo_input.json is missing. Executed on {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")

def random_choice_based_on_distribution(distribution_dict):
    """
    Selects an item based on a distribution of probabilities.

    :param distribution_dict: A dictionary where keys are items to choose from and values are their corresponding probabilities.
    :return: A randomly selected key based on the distribution.
    """
    items = list(distribution_dict.keys())
    weights = list(distribution_dict.values())
    return random.choices(items, weights=weights, k=1)[0]

def consent(driver, page):
    consent_distribution = {
        'allow-all-button': 70,
        'deny-all-button': 30
    }

    click_class = random_choice_based_on_distribution(consent_distribution)

    try: 
        WebDriverWait(driver, 10).until(lambda d: d.execute_script('return document.readyState') == 'complete')
    except TimeoutException:
        print("Timed out waiting for page to load")
        return;

    try:
        # Wait up to 10 seconds before throwing a TimeoutException unless it finds the element
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "allow-all-button"))
            )
        link = driver.find_element(By.CLASS_NAME, click_class)
        link.click()
        print(f"consent was given successfully as: {click_class}")
    # Now you can interact with the element since it's loaded
    except TimeoutException:
        print("Timed out waiting for cookie banner to appear");
        return;
    
def save_user_id (driver):
    # Retrieve "_ga" cookie value
    ga_cookie = driver.get_cookie("_ga")
    if ga_cookie:
        ga_value = ga_cookie['value']
        # Load existing client IDs from file, if it exists
        client_ids_file = 'client_ids.json'
        if os.path.exists(client_ids_file):
            with open(client_ids_file, 'r') as file:
                client_ids = json.load(file)
        else:
            client_ids = []

        # Add the new client ID
        client_ids.append(ga_value)

        # Save the updated list to the file
        with open(client_ids_file, 'w') as file:
            json.dump(client_ids, file)

def get_landing_page(driver, source):
    # Setup of landing page
    utm_parameters = ""
    if (source != "direct"):
        if "organic" in source:
            utm_parameters="?utm_source=" + demo_input[source]['source'] + "&utm_medium=" + demo_input[source]['medium']
        else:
            utm_parameters="?utm_source=" + demo_input[source]['source'] + "&utm_medium=" + demo_input[source]['medium'] + "&utm_campaign=" + demo_input[source].get('campaign', '')
    print(f"Selected utms: {utm_parameters}")
    page = random.choice(page_categories)  # Choosing a random page category
    

    # Assign a random landing page
    if page == "product":
        # Choose a random category for the product
        category = random.choice(product_categories)
        # Generate a random product ID between 1 and 10
        product_id = str(random.randint(1, 3))
        # Construct and navigate to the product URL
        url = f"{base_url}{category}/{product_id}.php{utm_parameters}"
        driver.get(url)
        return url

    elif page == "category":
        # Choose a random category
        category = random.choice(product_categories)
        # Navigate to the category URL
        url = f"{base_url}{category}.php{utm_parameters}"
        driver.get(url)
        return url

    else:
        # Navigate to a generic page URL
        url = f"{base_url}{page}.php{utm_parameters}"
        driver.get(url)
        return url

def add_to_cart(driver):
    category = random.choice(product_categories)
    product_id = str(random.randint(1, 3))
    url = f"{base_url}{category}/{product_id}.php"
    purchase_prm = f"?cat={category}&prod={product_id}"
    driver.get(url)
    try: 
        WebDriverWait(driver, 10).until(lambda d: d.execute_script('return document.readyState') == 'complete')
        print("got to product page")
        try:
            link = driver.find_element(By.CLASS_NAME, "cart")
            link.click()
            print("Added to cart.")
            time.sleep(5)
            return purchase_prm
        except Exception as e:
            print(f"An error occurred w add to cart click on {url}: {e}")
            return purchase_prm

    except TimeoutException:
        print("product page did not load")
        return purchase_prm

def execute_purchase_flow(browser, source, headless):
    global HEADLESS
	## TO ADD: PURCHASE VERSION: NEW/RETURNING CLIENT, FROM BEGINNING OR FROM ADD TO CART OR OTHER?
    print(f"execute_purchase_flow")
    options = ChromeOptions()
    headless = int(headless)
    if (headless==1):
        options.add_argument("--headless")  # Enables headless mode
    service = ChromeService(executable_path=CHROME_DRIVER)  # Update the path
    driver = webdriver.Chrome(service=service, options=options)
    # Setup of landing page
    utm_parameters = ""
    if (source != "direct"):
        if "organic" in source:
            utm_parameters="?utm_source=" + demo_input[source]['source'] + "&utm_medium=" + demo_input[source]['medium']
        else:
            utm_parameters="?utm_source=" + demo_input[source]['source'] + "&utm_medium=" + demo_input[source]['medium'] + "&utm_campaign=" + demo_input[source].get('campaign', '')
    print(f"Selected utms: {utm_parameters}")
    
    # Add navigation actions here

    url = "http://www.thefairycodemother.com/demo_project/home.php"+ utm_parameters
    driver.get(url)  # Your website URL
    consent(driver, url)
    # Scroll to the bottom of the page
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    
    # Stay on the page for 5 seconds and go to the next page
    time.sleep(5)
    purchase_prm = add_to_cart(driver)
    time.sleep(5)  
    driver.get("http://www.thefairycodemother.com/demo_project/checkout.php"+purchase_prm)
    print("begin checkout")
    time.sleep(5)  
    driver.get("http://www.thefairycodemother.com/demo_project/purchase.php"+purchase_prm)
    print("purchase happened")

    driver.quit()

def execute_browsing_flow(browser, source, headless):
    
    ## TO ADD: BROWSING VERSION: BOUNCED, ENGAGED, PURCHASE INTENT?
    print(f"execute_browsing_flow fired")
    # Define browser; fixed for now
    options = ChromeOptions()
    headless = int(headless)
    if (headless==1):
        options.add_argument("--headless")  # Enables headless mode
    service = ChromeService(executable_path=CHROME_DRIVER)  # Update the path
    driver = webdriver.Chrome(service=service, options=options)
    # End of browser setup

    # Choose a random landing page
    landing_page = get_landing_page(driver, source)
    

    # ----------> Navigation section <----------

    # Scroll to the bottom of the page
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    # Stay on the page for 10 seconds
    time.sleep(5)

    # Give/deny consent
    consent(driver, landing_page)

    #determine path
    path = random.choice(path_functions)
    #path = "add_to_cart"

    if path != "bounced":
        # Choose a random category for the product
        # Example: Click on a link with the text "Example Link"
        try:
            time.sleep(5)
            link = driver.find_element(By.LINK_TEXT,"Yes")
            link.click()
            print("Clicked on the link.")
            time.sleep(5)
        except Exception as e:
        	print(f"Elena, an error occurred with click on link with page {landing_page}: {e}")
    else:
    	print("Bounced.")

    if path == "product" or path == "add_to_cart":
        print("product or add to cart")
        #determine product page and go to it
        
        
        category = random.choice(product_categories)
        product_id = str(random.randint(1, 3))
        driver.get(f"{base_url}{category}/{product_id}.php")
        try: 
            WebDriverWait(driver, 10).until(lambda d: d.execute_script('return document.readyState') == 'complete')
            print("got to product page")
        except TimeoutException:
            print("Page did not load")

        if path == "add_to_cart":
            print("add to cart branch.")        
            try:
                link = driver.find_element(By.CLASS_NAME, "cart")
                link.click()
                print("Added to cart.")
                time.sleep(5)
            except Exception as e:
                print(f"An error occurred w add to cart click on {landing_page}: {e}")
    driver.quit()

def simulate_user(headless):
    
    # define a browser to use; using the dedicated demo_input.json file
    browser = random_choice_based_on_distribution(demo_input['browser_distribution'])
    print(f"Selected Browser: {browser}")
    # define an Acquisition source to use; using the dedicated demo_input.json file
    source = random_choice_based_on_distribution(demo_input['source_distribution'])
    print(f"Selected Source: {source}")
    # define path: purchase or not?
    is_purchase = random.random() < demo_input['ctr_by_source'][source]
    if is_purchase:
        execute_purchase_flow(browser, source, headless)
    else:
        execute_browsing_flow(browser, source, headless)	

def log_execution_time(start_time, args):
    end_time = time.time()
    elapsed_time = end_time - start_time
    with open("execution_log.txt", "a") as file:
        file.write(f"Execution time: {elapsed_time:.2f} seconds, Arguments: {args}\n")

    with open("/Users/elenanesi/Workspace/user-simulation/logfile.log", "a") as log_file:
        log_file.write(f"Script executed on {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write(f"Execution time: {execution_time}\n")

def main():
    global HEADLESS
    global NR_USERS
    # List to hold all the Process objects, needed to support multiple fake users visiting at once
    processes = []

    # Create and start a separate process for each user
    for i in range(NR_USERS):  # Change this number to the number of users you want to simulate
        p = Process(target=simulate_user, args=(HEADLESS,)) #target the simulate_user function
        p.start()
        processes.append(p)

    # Wait for all processes to finish
    for p in processes:
        p.join()

    

if __name__ == "__main__":
    start_time = time.time()
    print(f"Hello I am main and I started at {start_time}")
    os.chdir('/Users/elenanesi/Workspace/user-simulation/')
    arguments = []

    if len(sys.argv) > 1:
        HEADLESS = sys.argv[1]
        arguments.append(sys.argv[1])
        print(f"argument {HEADLESS}{sys.argv[1]}")
    if len(sys.argv) > 2:
        NR_USERS = int(sys.argv[2])
        arguments.append(sys.argv[2])
        print(f"argument {sys.argv[2]}")

    main()
    log_execution_time(start_time, arguments)
    
