import ast

def format_text_for_inference(title: str, ingredients: list, instructions: str) -> str:
    """
    Formats the recipe data into the string format expected by the model.
    """
    ingredients_str = ', '.join(ingredients)
    # The training data joins steps with a space.
    # The API gives instructions as a single string. We'll use it as is.
    steps_str = instructions
    
    return f"Recipe: {title}\nIngredients: {ingredients_str}\nSteps: {steps_str}"

# This function remains for the data preparation script.
def safe_literal_eval(s):
    """Safely evaluate a string that looks like a literal."""
    try:
        return ast.literal_eval(s)
    except (ValueError, SyntaxError, MemoryError):
        return []

def format_recipe_text_from_raw(row):
    """Combine recipe components from RAW_recipes.csv into a single string for training."""
    name = row['name']
    ingredients_list = safe_literal_eval(row['ingredients'])
    ingredients_str = ', '.join(ingredients_list)
    steps_list = safe_literal_eval(row['steps'])
    steps_str = ' '.join(steps_list)
    
    return f"Recipe: {name}\nIngredients: {ingredients_str}\nSteps: {steps_str}" 