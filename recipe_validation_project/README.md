# Recipe Validation Project

This project aims to scrape recipes, clean the data, and train a model to validate recipes. 
The validation model is exposed via a FastAPI.

## Project Structure

- `scraper/`: Contains scripts for scraping recipes from websites.
  - `scrape_allrecipes.py`: Script to scrape recipes from allrecipes.com.
- `data/`:
  - `raw/`: Stores raw, unprocessed scraped data (e.g., JSON files from scraper).
  - `processed/`: Stores cleaned and preprocessed data ready for modeling.
- `model/`:
  - `model.py`: Contains the recipe validation model logic.
  - `main.py`: FastAPI application to serve the validation model.
  - `__init__.py`: Makes `model` a Python package.
- `data_processing.py`: Scripts for cleaning and transforming raw recipe data.
- `requirements.txt`: Python dependencies for the project.
- `README.md`: This file.

## Setup

1.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Running the Project Components

### 1. Scraping Recipes

- Navigate to the `scraper` directory or modify paths in `scrape_allrecipes.py`.
- Run the scraper script:
  ```bash
  python scraper/scrape_allrecipes.py
  ```
- This will save an example scraped recipe to `data/allrecipes_example.json` (relative to where the script is run from, so ensure `data` dir exists at the project root or adjust path in script). For actual scraping, you'll need to manage output to `data/raw/`.

### 2. Processing Data

- After scraping, place your raw data files (e.g., JSONs) into the `data/raw/` directory.
- Run the data processing script from the project root:
  ```bash
  python data_processing.py
  ```
- Cleaned data will be saved to `data/processed/`.

### 3. Running the Recipe Validation API

- Ensure your model (`model/model.py`) is developed and any necessary files are in place.
- From the project root directory (`recipe_validation_project`):
  ```bash
  uvicorn model.main:app --reload
  ```
- The API will be available at `http://127.0.0.1:8000`.
- Access the API documentation (Swagger UI) at `http://127.0.0.1:8000/docs`.

## Development Notes

- **Scraper:** 
    - Implement robust URL discovery and iteration for `allrecipes.com` (or other sites).
    - Add error handling, logging, and respectful scraping practices (delays, `robots.txt`).
    - Decide on a storage strategy for thousands of recipes (e.g., one JSON per recipe in `data/raw/`, or a database).
- **Data Processing:**
    - Implement detailed cleaning logic in `data_processing.py` specific to the fields you need for your model.
    - Consider using libraries like Pandas for data manipulation if the dataset becomes large or complex.
- **Model:**
    - Develop the `RecipeValidator` in `model/model.py`. This could be rule-based or a machine learning model.
    - If using ML, you'll need to add steps for training, evaluation, and saving/loading the model.
- **API:**
    - Adjust the `RecipeInput` Pydantic model in `model/main.py` to match the final structure of your recipe data. 