# This file will contain your recipe validation model.
# This is a placeholder and will need to be developed based on your specific approach.

# Example: A very simple rule-based validation model
# You'll likely want to replace this with a more sophisticated model (e.g., ML-based).

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import os
from .text_utils import format_text_for_inference

class RecipeValidator:
    def __init__(self):
        """
        Initializes the RecipeValidator by loading the fine-tuned model and tokenizer.
        """
        # Determine the device
        self.device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
        print(f"RecipeValidator using device: {self.device}")

        # Path to the saved model - assuming it's in a 'saved_model' directory
        # relative to this file's location.
        model_dir = os.path.join(os.path.dirname(__file__), 'saved_model')

        if not os.path.exists(model_dir) or not os.listdir(model_dir):
            print(f"Warning: Model directory '{model_dir}' not found or is empty.")
            print("The validator will return all recipes as invalid.")
            self.model = None
            self.tokenizer = None
        else:
            print(f"Loading model from {model_dir}...")
            self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_dir)
            self.model.to(self.device)
            self.model.eval() # Set model to evaluation mode
            print("Model loaded successfully.")


    def validate_recipe(self, recipe_data: dict) -> dict:
        """
        Validates a recipe using the fine-tuned transformer model.

        Args:
            recipe_data (dict): A dictionary containing the recipe data.
                                  Expected keys: 'title', 'ingredients', 'instructions'.

        Returns:
            dict: A dictionary with 'is_valid' (bool) and 'issues' (list).
        """
        if not self.model or not self.tokenizer:
            return {
                "is_valid": False,
                "issues": ["Validator model is not loaded. Please train the model first."]
            }

        # Extract data and handle missing fields gracefully
        title = recipe_data.get("title", "")
        ingredients = recipe_data.get("ingredients", [])
        instructions = recipe_data.get("instructions", "")

        # A basic check for essential content
        if not title or not ingredients or not instructions:
            return {
                "is_valid": False,
                "issues": ["Recipe is missing title, ingredients, or instructions."]
            }

        # Format the text exactly as it was for training
        recipe_text = format_text_for_inference(
            title=title,
            ingredients=ingredients,
            instructions=instructions
        )
        
        # Perform inference
        inputs = self.tokenizer(recipe_text, return_tensors="pt", truncation=True, padding=True, max_length=512)
        inputs = {k: v.to(self.device) for k, v in inputs.items()} # Move inputs to the correct device

        with torch.no_grad():
            logits = self.model(**inputs).logits
        
        prediction = torch.argmax(logits, dim=-1).item()

        is_valid = bool(prediction == 1)
        issues = []
        if not is_valid:
            issues.append("The model classified this recipe as potentially invalid or malformed.")

        return {"is_valid": is_valid, "issues": issues}

# The following is for local testing of the validator class, not used by the API.
def get_sample_valid_recipe_for_inference():
    return {
        "title": "Simple Grilled Chicken",
        "ingredients": ["2 boneless chicken breasts", "1 tbsp olive oil", "1 tsp salt", "1/2 tsp black pepper"],
        "instructions": "1. Preheat grill to medium-high. 2. Brush chicken with olive oil and season with salt and pepper. 3. Grill for 6-8 minutes per side, or until cooked through."
    }

def get_sample_invalid_recipe_for_inference():
    return {
        "title": "bad recipe",
        "ingredients": ["water", "rock"],
        "instructions": "mix"
    }

if __name__ == "__main__":
    # This block will only run when the script is executed directly.
    # It assumes the model has been trained and saved in 'model/saved_model'.
    
    print("--- Testing RecipeValidator ---")
    validator = RecipeValidator()

    if validator.model:
        print("\nTesting a likely valid recipe:")
        valid_recipe = get_sample_valid_recipe_for_inference()
        result = validator.validate_recipe(valid_recipe)
        print(f"Validation result: {result}")

        print("\nTesting a likely invalid recipe:")
        invalid_recipe = get_sample_invalid_recipe_for_inference()
        result = validator.validate_recipe(invalid_recipe)
        print(f"Validation result: {result}")
    else:
        print("\nSkipping tests because model is not loaded.") 