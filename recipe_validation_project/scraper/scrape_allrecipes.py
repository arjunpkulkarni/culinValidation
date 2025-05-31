from recipe_scrapers import scrape_me
import json
import requests
from bs4 import BeautifulSoup
import time
import os
import google.generativeai as genai

# --- Gemini API Configuration ---
# GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") # User wants to hardcode
GOOGLE_API_KEY = "AIzaSyAR0UBnG0HHWhBxbW1BFenkK40cZbyFtp8" # Hardcoded API Key

if not GOOGLE_API_KEY: # This check will now always be false unless key is empty string
    print("Error: GOOGLE_API_KEY environment variable not set. Please set it to your Gemini API key.")
    # exit() # You might want to exit if the key isn't set, or handle it differently.
    # For now, we'll let it proceed, but API calls will fail.
else:
    genai.configure(api_key=GOOGLE_API_KEY) # Use the hardcoded key

# Model Configuration (Consider making this configurable)
GEMINI_MODEL_NAME = "gemini-2.0-flash" # Or "gemini-1.0-pro", "gemini-1.5-flash-latest" etc.
generation_config = {
    "temperature": 0.7,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 4096, # Increased for potentially larger recipe outputs
}
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

gemini_model = None
if GOOGLE_API_KEY:
    try:
        gemini_model = genai.GenerativeModel(model_name=GEMINI_MODEL_NAME,
                                         generation_config=generation_config,
                                         safety_settings=safety_settings)
        print(f"Gemini model '{GEMINI_MODEL_NAME}' initialized successfully.")
    except Exception as e:
        print(f"Error initializing Gemini model: {e}")
        gemini_model = None # Ensure it's None if initialization fails
else:
    print("Gemini model not initialized because GOOGLE_API_KEY is not set.")


def construct_gemini_prompt(recipe_data):
    """Constructs the prompt for the Gemini API to clean recipe data."""
    title = recipe_data.get("title", "N/A")
    # Ensure ingredients are a list of strings before joining
    ingredients_list = recipe_data.get("ingredients", [])
    if isinstance(ingredients_list, list):
        ingredients_str = "\n".join(ingredients_list)
    else:
        ingredients_str = str(ingredients_list) # Fallback if it's not a list

    # Ensure instructions are a string
    instructions_data = recipe_data.get("instructions", "N/A")
    if isinstance(instructions_data, list): # common if instructions_list() was used
        instructions_str = "\n".join(instructions_data)
    else:
        instructions_str = str(instructions_data)


    total_time = recipe_data.get("total_time", "N/A")
    yields = recipe_data.get("yields", "N/A")
    image = recipe_data.get("image", "N/A")
    host = recipe_data.get("host", "N/A")
    nutrients = recipe_data.get("nutrients", {}) # Nutrients usually a dict

    # Basic prompt, can be greatly expanded
    prompt = f"""
You are an expert culinary assistant tasked with cleaning and structuring recipe data for a machine learning dataset.
The goal is to extract key information accurately for recipe validation and enable tracking of ingredient usage through recipe steps.

From the provided recipe data:
1.  **Validate and Clean Title**: Provide the original title. Store in "cleaned_title".
2.  **Clean Ingredients List**:
    *   Parse each ingredient into quantity, unit, and name.
    *   Standardize units (e.g., 'tbsp' to 'tablespoon', 'g' to 'gram', 'tsp' to 'teaspoon', 'c' to 'cup').
    *   Output as a list of JSON objects, each with 'quantity', 'unit', 'name', and 'original_text'.
    *   Example: {{"quantity": "1", "unit": "cup", "name": "all-purpose flour", "original_text": "1 cup all-purpose flour"}}
    *   If quantity/unit are not explicit (e.g., "salt to taste"), use appropriate placeholders like "to taste" for quantity and null/empty for unit.
    *   Store this list in "cleaned_ingredients".
3.  **Clean Instructions and Track Ingredient Usage**:
    *   Break down into clear, sequential steps.
    *   For each step, identify the ingredients (using their 'name' from the "cleaned_ingredients" list) that are actively used, combined, or manipulated in that specific step.
    *   Output as a list of JSON objects. Each object should have:
        *   'step_number': An integer representing the order of the step (starting from 1).
        *   'step_text': The original, clear textual instruction for the step.
        *   'ingredients_used_in_step': A list of strings, where each string is the standardized 'name' of an ingredient used in this step. If no specific ingredient from the list is used (e.g., "Preheat oven"), this list can be empty.
    *   Example for "cleaned_instructions":
        ```json
        [
          {{
            "step_number": 1,
            "step_text": "Preheat oven to 350 degrees F (175 degrees C).",
            "ingredients_used_in_step": []
          }},
          {{
            "step_number": 2,
            "step_text": "In a medium bowl, whisk together the flour, baking powder, and salt.",
            "ingredients_used_in_step": ["all-purpose flour", "baking powder", "salt"]
          }}
        ]
        ```
    *   Store this list of step objects in "cleaned_instructions".
4.  **Extract Key Information**:
    *   Total Time (as provided or standardized, e.g., "PT1H30M" -> "1 hour 30 minutes"). Store in "total_time_str".
    *   Yields (as provided). Store in "yields_str".
    *   Image URL (as provided). Store in "image_url".
    *   Host (as provided). Store in "host_str".
    *   Nutrients (as provided, keep as a dictionary). Store in "nutrients_obj".

Please return the structured data as a single, valid JSON object with the following keys:
"cleaned_title", "cleaned_ingredients", "cleaned_instructions", "total_time_str", "yields_str", "image_url", "host_str", "nutrients_obj", "original_url".

If a field cannot be determined or is not applicable from the input, use null or an empty list/dictionary as appropriate for its type. Ensure ingredient names in 'ingredients_used_in_step' match those derived in 'cleaned_ingredients'.

Recipe Data:
---
Title: {title}
Ingredients:
{ingredients_str}
Instructions:
{instructions_str}
Total Time: {total_time}
Yields: {yields}
Image: {image}
Host: {host}
Nutrients: {json.dumps(nutrients)}
Original URL: {recipe_data.get("canonical_url", "N/A")}
---
Return ONLY the JSON object.
"""
    return prompt

# Global set to keep track of visited collection URLs to avoid redundant fetching and potential loops
visited_collection_urls = set()

def get_recipe_urls_from_category(category_url, depth=0, max_depth=1):
    """
    Fetches a category or collection page and extracts all unique direct recipe URLs.
    If depth < max_depth, it will also try to find collection-like pages and fetch recipes from them.
    """
    global visited_collection_urls
    print(f"Fetching URLs from: {category_url} (Depth: {depth})")

    if category_url in visited_collection_urls and depth > 0: # Don't skip the initial page
        print(f"Already visited collection page: {category_url}. Skipping.")
        return set() # Return a set for consistency

    # Add to visited set when we process it as a collection page link
    # For the very first call (depth 0), it's the main category, not a "collection link" we followed.
    if depth > 0:
        visited_collection_urls.add(category_url)

    direct_recipe_urls_found = set()
    potential_collection_page_urls = set()
    link_elements_collector = []

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Add a small delay before fetching any category/collection page
        time.sleep(0.5) # Respectful delay
        response = requests.get(category_url, headers=headers, timeout=25) # Slightly increased timeout
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # --- Strategies for finding <a> elements ---
        # Strategy 0: User-provided high-priority container
        high_priority_container_selector = '.comp.tax-sc__recirc-list.card-list.mntl-universal-card-list.mntl-document-card-list.mntl-card-list.mntl-block'
        high_priority_containers = soup.select(high_priority_container_selector)
        if high_priority_containers:
            # print(f"Strategy 0 (High-Priority Container): Found {len(high_priority_containers)} containers with selector '{high_priority_container_selector}'. Searching links within...")
            for container in high_priority_containers:
                link_elements_collector.extend(container.select('a[href]')) # Get all links with href first
        # else:
            # print(f"Strategy 0 (High-Priority Container): No containers found with selector '{high_priority_container_selector}'.")

        # --- Strategy 1: Primary selector for direct recipe links (or collection links)
        primary_links_selector = 'a.mntl-card-list-items[data-doc-id][href]' # Broadened to get href
        primary_links = soup.select(primary_links_selector)
        if primary_links:
            link_elements_collector.extend(primary_links)
            # print(f"Strategy 1 (Direct/Collection Links): Found {len(primary_links)} links with '{primary_links_selector}'.")
        
        # --- Strategy 2: User-provided specific group container class
        group_container_selector = '.comp.mntl-taxonomysc-article-list-group.mntl-block'
        group_containers = soup.select(group_container_selector)
        if group_containers:
            for container in group_containers:
                link_elements_collector.extend(container.select('a[href]'))
            # print(f"Strategy 2 (Group Container): Found links within {len(group_containers)} group containers.")

        # --- Strategy 3: Fallback for various card-like structures
        card_selectors = [
            '.comp.mntl-card-list-items.mntl-universal-card.mntl-document-card.mntl-card.card.card--no-image[href]',
            'article.mntl-card-list-items a[href]', '.card.mntl-card-list-items a[href]',
            '.fixed-recipe-card a[href]', '.comp.mntl-card-list-items[href]', # If the item itself is <a>
            'li.mntl-block a[href]',
            '.recipe-card-group__item a[href]'
        ]
        for selector in card_selectors:
            links_from_cards_or_lists = soup.select(selector)
            if links_from_cards_or_lists:
                link_elements_collector.extend(links_from_cards_or_lists)
        # print(f"Strategy 3 (Cards/Lists): Added potential links from various card/list selectors.")

        # --- Strategy 4: General fallback (use sparingly or if others yield little) ---
        if not link_elements_collector or len(link_elements_collector) < 10 : # Only if very few links found
            # print(f"Few links found by specific selectors. Trying general 'a[href]' fallback...")
            general_links = soup.select('main a[href]') # Search within main content area
            if not general_links:
                general_links = soup.select('body a[href]') # Broader if main yields nothing
            link_elements_collector.extend(general_links)
            # print(f"Strategy 4 (General Fallback): Added {len(general_links)} general links.")
        
        # --- Process collected link elements ---
        processed_hrefs_for_this_page = set()
        
        for link_element in link_elements_collector:
            href = link_element.get('href')
            if not href or href in processed_hrefs_for_this_page:
                continue
            processed_hrefs_for_this_page.add(href)

            full_url = href
            if href.startswith('/'): # Relative URL
                parsed_origin_url = requests.utils.urlparse(category_url)
                full_url = f"{parsed_origin_url.scheme}://{parsed_origin_url.netloc}{href}"

            if not full_url.startswith('https://www.allrecipes.com/'):
                continue # Skip non-allrecipes links

            if '/recipe/' in full_url:
                # Ensure it looks like a valid recipe URL (e.g., ends with number or string, not /recipes/)
                if full_url.split('/recipe/')[-1] and not full_url.endswith('/recipe/') and not full_url.endswith('/recipes/'):
                    direct_recipe_urls_found.add(full_url)
            elif depth < max_depth:
                # This is a potential collection page if it doesn't contain /recipe/
                # and meets criteria (e.g., has data-doc-id or specific classes like the example)
                # For simplicity now, we'll consider any non-recipe allrecipes link from a card a potential collection.
                # More specific checks could be link_element.get('data-doc-id') or class checks
                if link_element.get('data-doc-id') or any(cls in link_element.get('class', []) for cls in ['mntl-card-list-items', 'card--no-image']):
                     # Avoid adding common non-collection links like /profile/, /account/, /newsletters/, etc.
                    if not any(kw in full_url for kw in ['/profile/', '/account/', '/newsletter', '/video/', '/gallery/', '.jpg', '.png', '/reviews/', '/photos/', '/submit/', '/survey/', '/print/']):
                        potential_collection_page_urls.add(full_url)

    except requests.RequestException as e:
        print(f"Error fetching page {category_url}: {e}")
        return direct_recipe_urls_found # Return what we have so far

    print(f"Found {len(direct_recipe_urls_found)} direct recipe URLs and {len(potential_collection_page_urls)} potential collection URLs on {category_url}.")

    # If depth allows, explore collection pages
    if depth < max_depth:
        for collection_url in potential_collection_page_urls:
            if collection_url not in visited_collection_urls: # Check again before recursive call
                # print(f"  Recursively fetching from collection: {collection_url} (Depth: {depth + 1})")
                recipes_from_collection = get_recipe_urls_from_category(collection_url, depth + 1, max_depth)
                direct_recipe_urls_found.update(recipes_from_collection)
            # else:
                # print(f"  Skipping already visited collection (checked before recursion): {collection_url}")


    return direct_recipe_urls_found

def scrape_recipe(url):
    try:
        scraper = scrape_me(url) # wild_mode=True removed as it caused issues
        # Check if essential data is present
        title = scraper.title()
        if not title:
            print(f"Warning: No title found for {url}, skipping.")
            return None

        return {
            "title": title,
            "total_time": scraper.total_time(),
            "yields": scraper.yields(),
            "ingredients": scraper.ingredients(),
            "instructions": scraper.instructions(),
            "image": scraper.image(),
            "host": scraper.host(),
            "links": scraper.links(),
            "nutrients": scraper.nutrients(),
            "canonical_url": scraper.canonical_url(),
            # Add other fields as needed, e.g., ratings if you can find them
        }
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

if __name__ == "__main__":
    start_category_url = "https://www.allrecipes.com/recipes/78/breakfast-and-brunch/"
    output_directory = "data"
    cleaned_output_filename = os.path.join(output_directory, "allrecipes_breakfast_brunch_cleaned.json")

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    if not GOOGLE_API_KEY or not gemini_model:
        print("Error: Gemini API key not set or model not initialized. Cleaned data cannot be produced. Exiting.")
        exit()

    print(f"Starting recursive scrape for category: {start_category_url}")
    # Clear visited collection URLs at the start of a new top-level run
    visited_collection_urls.clear()
    # Initial call to get all recipe URLs, including from one level of collection pages
    recipe_urls_to_scrape_set = get_recipe_urls_from_category(start_category_url, depth=0, max_depth=1)
    recipe_urls_to_scrape = list(recipe_urls_to_scrape_set)
    
    if not recipe_urls_to_scrape:
        print(f"No recipe URLs found from {start_category_url} or its collections. Exiting.")
    else:
        print(f"Found a total of {len(recipe_urls_to_scrape)} unique recipe URLs to scrape.")
        # print("URLs to scrape:", recipe_urls_to_scrape[:20]) # Print some for verification

        scraped_count = 0
        processed_count = 0
        all_cleaned_recipes = []

        for i, recipe_url in enumerate(recipe_urls_to_scrape):
            print(f"Scraping recipe {i+1}/{len(recipe_urls_to_scrape)}: {recipe_url}")
            # Ensure we don't re-scrape if somehow a non-recipe URL slipped through initial filtering
            if "/recipe/" not in recipe_url:
                print(f"Skipping non-recipe URL that was collected: {recipe_url}")
                continue

            recipe_data = scrape_recipe(recipe_url)
            
            if recipe_data:
                print(f"Raw data scraped for: {recipe_data.get('title')}")
                scraped_count += 1

                if GOOGLE_API_KEY and gemini_model: # This check is technically redundant due to exit above but good practice
                    print(f"Processing with Gemini: {recipe_data.get('title')}")
                    prompt = construct_gemini_prompt(recipe_data)
                    try:
                        response = gemini_model.generate_content(prompt)
                        if hasattr(response, 'text') and response.text:
                            cleaned_data_str = response.text.strip()
                            if cleaned_data_str.startswith("```json"):
                                cleaned_data_str = cleaned_data_str[7:]
                            if cleaned_data_str.endswith("```"):
                                cleaned_data_str = cleaned_data_str[:-3]
                            
                            try:
                                cleaned_json = json.loads(cleaned_data_str)
                                if 'original_url' not in cleaned_json and recipe_data.get('canonical_url'):
                                    cleaned_json['original_url'] = recipe_data.get('canonical_url')
                                elif 'original_url' not in cleaned_json: # Fallback if canonical_url was also None
                                     cleaned_json['original_url'] = recipe_url

                                all_cleaned_recipes.append(cleaned_json)
                                print(f"Successfully processed by Gemini: {cleaned_json.get('cleaned_title')}")
                                processed_count +=1
                            except json.JSONDecodeError as json_e:
                                print(f"Error: Gemini API response was not valid JSON for '{recipe_data.get('title')}'. Error: {json_e}")
                                print(f"Gemini response text: {response.text[:500]}...")
                            except Exception as e_parse:
                                print(f"Error parsing Gemini's JSON response for '{recipe_data.get('title')}'. Error: {e_parse}")
                                print(f"Gemini response text: {response.text[:500]}...")
                        else:
                            print(f"Error: Gemini API response was empty or malformed for {recipe_data.get('title')}. Response: {response}")
                            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                                 print(f"Prompt Feedback: {response.prompt_feedback}")
                    except Exception as e_gemini:
                        print(f"Error calling Gemini API for '{recipe_data.get('title')}': {e_gemini}")
                        if hasattr(e_gemini, 'response') and hasattr(e_gemini.response, 'prompt_feedback'):
                            print(f"Prompt Feedback: {e_gemini.response.prompt_feedback}")
            else:
                print(f"Failed to scrape {recipe_url}")
            
            time.sleep(1.5) # Adjusted sleep: 2s if Gemini was used, 1s if not. Now consistent 1.5s. Consider longer if rate limited.
        
        if all_cleaned_recipes: # Check if list is not empty
            with open(cleaned_output_filename, "w") as cleaned_f:
                json.dump(all_cleaned_recipes, cleaned_f, indent=4)
            print(f"Successfully saved {len(all_cleaned_recipes)} cleaned recipes to {cleaned_output_filename}.")
        elif not (GOOGLE_API_KEY and gemini_model): # This case should be caught by the exit() earlier
             print(f"Gemini processing was skipped. No cleaned JSON file produced.")
        elif not all_cleaned_recipes and recipe_urls_to_scrape: # Recipes were found, but none processed.
            print(f"No recipes were successfully processed by Gemini, or no recipe data was usable. Cleaned JSON file not created.")
        else: # No recipes found to scrape to begin with.
            print(f"No recipes processed. Cleaned JSON file not created.")


        print(f"\nScraping complete.")
        print(f"Successfully scraped data for {scraped_count}/{len(recipe_urls_to_scrape)} recipes.")
        if GOOGLE_API_KEY and gemini_model:
            print(f"Successfully processed {processed_count}/{scraped_count} recipes with Gemini.")
        else:
            print(f"Gemini processing was skipped (API key or model not initialized). No cleaned output file produced.")


# TODO:
# 1. Pagination for categories that list many more recipes than fit on one page.
# 2. More robust error handling and retries (e.g., for network issues, API rate limits).
# 3. Logging module.
# 4. Refine collection page identification if needed.
# 5. Ensure delays are respectful of robots.txt and terms of service. Current sleep is basic.
# 6. Consider making max_depth configurable.
# 7. The selectors in `get_recipe_urls_from_category` might still need refinement for different page layouts.

# 1. Implement logic to find and scrape thousands of recipes from allrecipes.com.
#    This might involve finding sitemap.xml, category pages, or other navigation patterns.
#    Robust pagination handling for category pages is needed.
# 2. Add robust error handling and retries (e.g., for network issues, API rate limits).
# 3. Consider how to store the scraped data (e.g., multiple JSON files, a database). (Single JSON for cleaned)
# 4. Implement logging using the `logging` module for better tracking.
# 5. Be respectful of the website's terms of service and robots.txt.
#    Implement delays between requests to avoid overwhelming their servers. (Basic delay added, increased if using Gemini)
# 6. The CSS selectors in `get_recipe_urls_from_category` might need refinement
#    if the website structure changes or for different category page layouts. (Refined)
# 7. Add user-agent to requests. (Added)
# 8. Securely manage API Key for Gemini (using environment variable is a good start).
# 9. Refine Gemini prompt for better accuracy and desired output structure.
#10. Handle Gemini API rate limits more gracefully (e.g., exponential backoff).

# 1. Implement logic to find and scrape thousands of recipes from allrecipes.com.
#    This might involve finding sitemap.xml, category pages, or other navigation patterns.
#    Robust pagination handling for category pages is needed.
# 2. Add robust error handling and retries (e.g., for network issues).
# 3. Consider how to store the scraped data (e.g., multiple JSON files, a database). (Single JSON for cleaned)
# 4. Implement logging using the `logging` module for better tracking.
# 5. Be respectful of the website's terms of service and robots.txt.
#    Implement delays between requests to avoid overwhelming their servers. (Basic delay added)
# 6. The CSS selectors in `get_recipe_urls_from_category` might need refinement
#    if the website structure changes or for different category page layouts. (Refined)
# 7. Add user-agent to requests. 