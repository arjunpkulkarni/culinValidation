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
The goal is to extract key information accurately for recipe validation.

From the provided recipe data:
1.  **Validate and Clean Title**: Provide the original title.
2.  **Clean Ingredients List**:
    *   Parse each ingredient into quantity, unit, and name.
    *   Standardize units (e.g., 'tbsp' to 'tablespoon', 'g' to 'gram', 'tsp' to 'teaspoon', 'c' to 'cup').
    *   Output as a list of JSON objects, each with 'quantity', 'unit', 'name', and 'original_text'.
    *   Example: {{"quantity": "1", "unit": "cup", "name": "all-purpose flour", "original_text": "1 cup all-purpose flour"}}
    *   If quantity/unit are not explicit (e.g., "salt to taste"), use appropriate placeholders like "to taste" for quantity and null/empty for unit.
3.  **Clean Instructions**:
    *   Break down into clear, sequential steps as a list of strings.
    *   Ensure each step is a complete action.
4.  **Extract Key Information**:
    *   Total Time (as provided or standardized, e.g., "PT1H30M" -> "1 hour 30 minutes").
    *   Yields (as provided).
    *   Image URL (as provided).
    *   Host (as provided).
    *   Nutrients (as provided, keep as a dictionary).

Please return the structured data as a single, valid JSON object with the following keys:
"cleaned_title", "cleaned_ingredients", "cleaned_instructions", "total_time_str", "yields_str", "image_url", "host_str", "nutrients_obj", "original_url".

If a field cannot be determined or is not applicable from the input, use null or an empty list/dictionary as appropriate for its type.

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

# Example: Scraping a single recipe from allrecipes.com
# You will need to expand this to scrape multiple recipes
# and handle pagination, errors, etc.

def get_recipe_urls_from_category(category_url):
    """
    Fetches a category page and extracts all unique recipe URLs.
    """
    recipe_urls = set()
    try:
        # Consider adding a User-Agent header
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(category_url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Primary selector based on observed structure (e.g., from user-provided HTML)
        # These are <a> tags that are themselves the "cards" or list items.
        link_elements = soup.select('a.mntl-card-list-items[data-doc-id]')

        if not link_elements:
            # Fallback: Try to find links within common list item or card container structures
            # This was the previous primary strategy, now a fallback.
            print("Primary selector 'a.mntl-card-list-items[data-doc-id]' found no links. Trying fallback selectors...")
            possible_card_selectors = ['article.fixed-recipe-card', '.card', '.recipe-card', '.card-list__item'] # Added .card-list__item
            for selector in possible_card_selectors:
                cards = soup.select(selector)
                for card in cards:
                    # If the card itself is an 'a' tag with a recipe link
                    if card.name == 'a' and card.get('href') and '/recipe/' in card.get('href'):
                        link_elements.append(card)
                    else: # Otherwise, look for 'a' tags within the card
                        links_in_card = card.select('a[href*="/recipe/"]')
                        link_elements.extend(links_in_card)
                if link_elements:
                    print(f"Found links using fallback selector: {selector}")
                    break
        
        if not link_elements: # Second Fallback to a more general search if specific cards not found
            print("Fallback selectors found no links. Trying general 'a[href*=\"/recipe/\"]' selector...")
            link_elements = soup.select('a[href*="/recipe/"]')

        if not link_elements:
            print(f"No recipe links found on {category_url} with any attempted selectors.")


        for link_element in link_elements:
            href = link_element.get('href')
            if href:
                # Ensure it's a full URL, Allrecipes recipe link, and not a fragment or different domain
                if href.startswith("https://www.allrecipes.com/recipe/"):
                    recipe_urls.add(href)
                elif href.startswith("/recipe/"):
                    # Check for base URL to avoid issues if category_url is not from www.allrecipes.com (though it should be)
                    base_url = "https://www.allrecipes.com"
                    if "allrecipes.com" in category_url: # Basic check
                         parsed_category_url = requests.utils.urlparse(category_url)
                         base_url = f"{parsed_category_url.scheme}://{parsed_category_url.netloc}"
                    recipe_urls.add(f"{base_url}{href}")
                # else:
                    # print(f"Skipping non-recipe or non-Allrecipes link: {href}")


    except requests.RequestException as e:
        print(f"Error fetching category page {category_url}: {e}")
    return list(recipe_urls)

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
    # Changed output filename for cleaned data
    raw_output_filename = os.path.join(output_directory, "allrecipes_breakfast_brunch_raw.jsonl")
    cleaned_output_filename = os.path.join(output_directory, "allrecipes_breakfast_brunch_cleaned.jsonl")


    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    if not GOOGLE_API_KEY or not gemini_model:
        print("Warning: Gemini API key not set or model not initialized. Will only save raw scraped data.")
        # Fallback to only saving raw data if Gemini isn't set up
        cleaned_output_filename = raw_output_filename


    print(f"Starting scrape for category: {start_category_url}")
    recipe_urls_to_scrape = get_recipe_urls_from_category(start_category_url)
    
    if not recipe_urls_to_scrape:
        print(f"No recipe URLs found on {start_category_url}. Exiting.")
    else:
        print(f"Found {len(recipe_urls_to_scrape)} recipe URLs to scrape.")

        scraped_count = 0
        processed_count = 0
        # Open two files: one for raw, one for cleaned if Gemini is available
        with open(raw_output_filename, "a") as raw_f, \
             (open(cleaned_output_filename, "a") if GOOGLE_API_KEY and gemini_model else open(os.devnull, 'w')) as cleaned_f:

            for i, recipe_url in enumerate(recipe_urls_to_scrape):
                print(f"Scraping recipe {i+1}/{len(recipe_urls_to_scrape)}: {recipe_url}")
                recipe_data = scrape_recipe(recipe_url)
                
                if recipe_data:
                    # Save raw data
                    json.dump(recipe_data, raw_f)
                    raw_f.write("\n")
                    print(f"Successfully scraped raw data: {recipe_data.get('title')}")
                    scraped_count += 1

                    # Process with Gemini if available
                    if GOOGLE_API_KEY and gemini_model:
                        print(f"Processing with Gemini: {recipe_data.get('title')}")
                        prompt = construct_gemini_prompt(recipe_data)
                        try:
                            response = gemini_model.generate_content(prompt)
                            # Basic check if response.text exists
                            if hasattr(response, 'text') and response.text:
                                cleaned_data_str = response.text.strip()
                                # Gemini might return markdown ```json ... ```, try to extract
                                if cleaned_data_str.startswith("```json"):
                                    cleaned_data_str = cleaned_data_str[7:]
                                if cleaned_data_str.endswith("```"):
                                    cleaned_data_str = cleaned_data_str[:-3]
                                
                                try:
                                    cleaned_json = json.loads(cleaned_data_str)
                                    # Add original URL if not already in the cleaned data by Gemini
                                    if 'original_url' not in cleaned_json:
                                        cleaned_json['original_url'] = recipe_data.get('canonical_url')
                                    
                                    json.dump(cleaned_json, cleaned_f)
                                    cleaned_f.write("\n")
                                    print(f"Successfully processed by Gemini and saved: {cleaned_json.get('cleaned_title')}")
                                    processed_count +=1
                                except json.JSONDecodeError as json_e:
                                    print(f"Error: Gemini API response was not valid JSON for '{recipe_data.get('title')}'. Error: {json_e}")
                                    print(f"Gemini response text: {response.text[:500]}...") # Log part of the response
                                except Exception as e_parse:
                                    print(f"Error parsing Gemini's JSON response for '{recipe_data.get('title')}'. Error: {e_parse}")
                                    print(f"Gemini response text: {response.text[:500]}...")
                            else: # Handle cases where response.text might be empty or missing
                                print(f"Error: Gemini API response was empty or malformed for {recipe_data.get('title')}. Response: {response}")
                                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                                     print(f"Prompt Feedback: {response.prompt_feedback}")


                        except Exception as e_gemini:
                            print(f"Error calling Gemini API for '{recipe_data.get('title')}': {e_gemini}")
                            if hasattr(e_gemini, 'response') and hasattr(e_gemini.response, 'prompt_feedback'):
                                print(f"Prompt Feedback: {e_gemini.response.prompt_feedback}")

                    elif not (GOOGLE_API_KEY and gemini_model):
                        # If not using Gemini, we just write the raw data to the "cleaned" file as well,
                        # or simply don't process further if cleaned_output_filename was set to raw_output_filename.
                        # For clarity, if Gemini isn't setup, cleaned_output_filename is raw_output_filename,
                        # so no extra write needed here.
                        pass


                else:
                    print(f"Failed to scrape {recipe_url}")
                
                # Be respectful: wait a bit between requests
                # Increase delay if making API calls per recipe
                time.sleep(2 if GOOGLE_API_KEY and gemini_model else 1) 
        
        print(f"\nScraping complete.")
        print(f"Successfully scraped {scraped_count}/{len(recipe_urls_to_scrape)} raw recipes to {raw_output_filename}.")
        if GOOGLE_API_KEY and gemini_model:
            print(f"Successfully processed {processed_count}/{scraped_count} recipes with Gemini to {cleaned_output_filename}.")
        else:
            print(f"Gemini processing was skipped (API key or model not initialized). Raw data only in {raw_output_filename}.")


# TODO:
# 1. Implement logic to find and scrape thousands of recipes from allrecipes.com.
#    This might involve finding sitemap.xml, category pages, or other navigation patterns.
#    Robust pagination handling for category pages is needed.
# 2. Add robust error handling and retries (e.g., for network issues, API rate limits).
# 3. Consider how to store the scraped data (e.g., multiple JSON files, a database). (JSONL is a good start)
# 4. Implement logging using the `logging` module for better tracking.
# 5. Be respectful of the website's terms of service and robots.txt.
#    Implement delays between requests to avoid overwhelming their servers. (Basic delay added, increased if using Gemini)
# 6. The CSS selectors in `get_recipe_urls_from_category` might need refinement
#    if the website structure changes or for different category page layouts.
# 7. Add user-agent to requests. (Added)
# 8. Securely manage API Key for Gemini (using environment variable is a good start).
# 9. Refine Gemini prompt for better accuracy and desired output structure.
#10. Handle Gemini API rate limits more gracefully (e.g., exponential backoff).

# 1. Implement logic to find and scrape thousands of recipes from allrecipes.com.
#    This might involve finding sitemap.xml, category pages, or other navigation patterns.
#    Robust pagination handling for category pages is needed.
# 2. Add robust error handling and retries (e.g., for network issues).
# 3. Consider how to store the scraped data (e.g., multiple JSON files, a database). (JSONL is a good start)
# 4. Implement logging using the `logging` module for better tracking.
# 5. Be respectful of the website's terms of service and robots.txt.
#    Implement delays between requests to avoid overwhelming their servers. (Basic delay added)
# 6. The CSS selectors in `get_recipe_urls_from_category` might need refinement
#    if the website structure changes or for different category page layouts.
# 7. Add user-agent to requests. 