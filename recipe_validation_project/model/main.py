from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# Import your RecipeValidator
# Ensure model.py is in the same directory or adjust Python path
from .model import RecipeValidator 

app = FastAPI(
    title="Recipe Validation API",
    description="API to validate recipe data based on a predefined model.",
    version="0.1.0"
)

# Initialize your validator
# This might involve loading a trained model, so it's good to do it at startup
recipe_validator = RecipeValidator()

# Define the request body model using Pydantic
# This should match the structure of the recipe data your validator expects
class RecipeInput(BaseModel):
    title: Optional[str] = Field(None, description="Title of the recipe")
    ingredients: Optional[List[str]] = Field(None, description="List of ingredients")
    instructions: Optional[str] = Field(None, description="Cooking instructions")
    total_time: Optional[int] = Field(None, description="Total cooking time in minutes") # Example field
    yields: Optional[str] = Field(None, description="Recipe yield (e.g., '4 servings')") # Example field
    nutrients: Optional[Dict[str, Any]] = Field(None, description="Nutritional information")
    # Add any other fields that your `RecipeValidator` uses or that you want to pass through
    # Make sure the types match what `recipe_scrapers` provides or how you clean them

# Define the response body model
class ValidationResponse(BaseModel):
    is_valid: bool
    issues: List[str]
    # You could add the original recipe data or a processed version here if needed
    # original_recipe: Optional[RecipeInput]

@app.post("/validate-recipe/", response_model=ValidationResponse)
async def validate_recipe_endpoint(recipe: RecipeInput):
    """
    Receives recipe data, validates it using the `RecipeValidator`,
    and returns the validation result.
    """
    # Convert Pydantic model to dict for the validator, if necessary
    # The validator might expect a plain dict
    recipe_data_dict = recipe.dict(exclude_none=True) # exclude_none to remove fields not provided
    
    validation_result = recipe_validator.validate_recipe(recipe_data_dict)
    
    return ValidationResponse(
        is_valid=validation_result["is_valid"],
        issues=validation_result["issues"]
    )

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Recipe Validation API. Use the /docs endpoint for API documentation."}

# To run this API:
# 1. Ensure you are in the `recipe_validation_project` directory (the parent of `model` directory).
# 2. Run the command: uvicorn model.main:app --reload
#    (This assumes `model` is a Python package, so you might need an __init__.py in the model folder)
# 3. Open your browser to http://127.0.0.1:8000/docs to see the API documentation.

# For the `uvicorn model.main:app --reload` command to work correctly when you are in 
# the `recipe_validation_project` directory, you will need an `__init__.py` file in the `model` directory.
# This makes `model` a Python package, allowing `from .model import RecipeValidator` to work. 