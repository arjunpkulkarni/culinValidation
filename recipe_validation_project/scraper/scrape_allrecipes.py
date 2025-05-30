from recipe_scrapers import scrape_me
import json
import requests
from bs4 import BeautifulSoup
import time
import os

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
            print("Fallback selectors found no links. Trying general 'a[href*="/recipe/"]' selector...")
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
        scraper = scrape_me(url) # wild_mode=True can help with some sites if direct support is flaky
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
    output_filename = os.path.join(output_directory, "allrecipes_breakfast_brunch.jsonl")

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    print(f"Starting scrape for category: {start_category_url}")
    recipe_urls_to_scrape = get_recipe_urls_from_category(start_category_url)
    
    if not recipe_urls_to_scrape:
        print(f"No recipe URLs found on {start_category_url}. Exiting.")
    else:
        print(f"Found {len(recipe_urls_to_scrape)} recipe URLs to scrape.")

        scraped_count = 0
        with open(output_filename, "a") as f: # Append mode
            for i, recipe_url in enumerate(recipe_urls_to_scrape):
                print(f"Scraping recipe {i+1}/{len(recipe_urls_to_scrape)}: {recipe_url}")
                recipe_data = scrape_recipe(recipe_url)
                if recipe_data:
                    json.dump(recipe_data, f)
                    f.write("\n") # Write each JSON object on a new line
                    print(f"Successfully scraped and saved: {recipe_data.get('title')}")
                    scraped_count += 1
                else:
                    print(f"Failed to scrape {recipe_url}")
                
                # Be respectful: wait a bit between requests
                time.sleep(1) # Wait for 1 second
        
        print(f"\nScraping complete. Successfully scraped {scraped_count}/{len(recipe_urls_to_scrape)} recipes.")
        print(f"Data saved to {output_filename}")

# TODO:
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