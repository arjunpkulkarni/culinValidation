# This file will contain your recipe validation model.
# This is a placeholder and will need to be developed based on your specific approach.

# Example: A very simple rule-based validation model
# You'll likely want to replace this with a more sophisticated model (e.g., ML-based).

class RecipeValidator:
    def __init__(self):
        # Load any necessary model files, pre-trained weights, etc.
        # For a simple model, this might not be needed.
        pass

    def validate_recipe(self, recipe_data):
        """
        Validates a recipe based on a set of rules or a trained model.

        Args:
            recipe_data (dict): A dictionary containing the cleaned recipe data.
                                  Expected keys might include 'ingredients', 'instructions',
                                  'title', 'nutrients', etc.

        Returns:
            dict: A dictionary containing validation results.
                  Example: {"is_valid": True, "issues": []}
                           {"is_valid": False, "issues": ["Missing instructions", "No ingredients listed"]}
        """
        issues = []
        is_valid = True

        # Rule 1: Check for presence of title
        if not recipe_data.get("title", "").strip():
            issues.append("Recipe title is missing or empty.")
            is_valid = False

        # Rule 2: Check for presence of ingredients
        ingredients = recipe_data.get("ingredients", [])
        if not ingredients or not isinstance(ingredients, list) or len(ingredients) == 0:
            issues.append("Recipe ingredients are missing or empty.")
            is_valid = False
        else:
            # Rule 2a: Check if each ingredient is a non-empty string (simplistic check)
            for i, ing in enumerate(ingredients):
                if not isinstance(ing, str) or not ing.strip():
                    issues.append(f"Ingredient at index {i} is invalid (empty or not a string).")
                    is_valid = False

        # Rule 3: Check for presence of instructions
        instructions = recipe_data.get("instructions", "").strip()
        if not instructions:
            issues.append("Recipe instructions are missing or empty.")
            is_valid = False
        
        # Rule 4: (Optional) Check for basic nutrition info if expected
        # nutrients = recipe_data.get("nutrients", {})
        # if not nutrients.get("calories"):
        #     issues.append("Calories information is missing.")
            # Depending on strictness, this might not make the recipe invalid

        # TODO: 
        # 1. Define more sophisticated validation rules.
        # 2. If using an ML model:
        #    - Load your trained model here.
        #    - Preprocess `recipe_data` to match the model's input format.
        #    - Get predictions from the model.
        #    - Interpret predictions to determine validity and issues.
        # 3. Consider what constitutes a "valid" recipe for your use case.
        #    Is it about completeness, healthiness, clarity, potential success?

        return {"is_valid": is_valid, "issues": issues}

# Example usage (for testing locally):
def get_sample_valid_recipe():
    return {
        "title": "Valid Test Recipe",
        "ingredients": ["1 cup sugar", "2 eggs", "1/2 tsp salt"],
        "instructions": "1. Mix all ingredients. 2. Bake at 350F for 30 minutes.",
        "nutrients": {"calories": "300 kcal"}
    }

def get_sample_invalid_recipe():
    return {
        "title": "", # Invalid: Missing title
        "ingredients": [], # Invalid: Missing ingredients
        "instructions": "Mix it."
    }

if __name__ == "__main__":
    validator = RecipeValidator()

    print("Validating a sample valid recipe:")
    valid_recipe_data = get_sample_valid_recipe()
    validation_result = validator.validate_recipe(valid_recipe_data)
    print(validation_result)

    print("\nValidating a sample invalid recipe:")
    invalid_recipe_data = get_sample_invalid_recipe()
    validation_result = validator.validate_recipe(invalid_recipe_data)
    print(validation_result)

    print("\nValidating a recipe with malformed ingredients:")
    bad_ingredients_recipe = {
        "title": "Bad Ingredients Recipe",
        "ingredients": ["1 cup flour", None, ""], # Invalid ingredients
        "instructions": "Bake it."
    }
    validation_result = validator.validate_recipe(bad_ingredients_recipe)
    print(validation_result) 