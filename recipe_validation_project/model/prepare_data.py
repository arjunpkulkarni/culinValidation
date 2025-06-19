import pandas as pd
import os
from tqdm import tqdm
from .text_utils import format_recipe_text_from_raw

# Register tqdm with pandas
tqdm.pandas()

def main():
    """Main function to run data preparation."""
    print("Starting data preparation with RAW text data...")

    # Define paths
    data_path = 'scraper/data/files'
    output_dir = 'data/processed'
    output_file = os.path.join(output_dir, 'recipe_validation_dataset_raw.csv')

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # --- Step 1: Load and process interactions data ---
    print("Loading interaction data...")
    interaction_files = ['interactions_train.csv', 'interactions_validation.csv', 'interactions_test.csv']
    # Specify dtypes to avoid mixed-type warnings
    interactions_df = pd.concat([pd.read_csv(os.path.join(data_path, f), dtype={'user_id': str, 'recipe_id': int, 'date': str, 'rating': int, 'review': str}) for f in interaction_files])
    
    print("Processing interaction data...")
    # Filter out ambiguous ratings (3.0)
    interactions_df = interactions_df[interactions_df['rating'] != 3]
    
    # Create weak labels
    interactions_df['label'] = interactions_df['rating'].apply(lambda x: 1 if x >= 4 else 0)
    
    # Keep only necessary columns and handle duplicates
    interactions_df = interactions_df[['recipe_id', 'label']].drop_duplicates(subset=['recipe_id', 'label'], keep='first')

    # --- Step 2: Load and process recipe data ---
    print("Loading RAW recipe data...")
    # RAW_recipes has columns: name,id,minutes,contributor_id,submitted,tags,nutrition,n_steps,steps,description,ingredients,n_ingredients
    recipes_df = pd.read_csv(os.path.join(data_path, 'RAW_recipes.csv'))
    
    print("Constructing recipe text features from raw text...")
    recipes_df_text = recipes_df[['id', 'name', 'ingredients', 'steps']].copy()
    recipes_df_text['text'] = recipes_df_text.progress_apply(format_recipe_text_from_raw, axis=1)

    # --- Step 3: Merge data and save ---
    print("Merging datasets...")
    recipes_df_text.rename(columns={'id': 'recipe_id'}, inplace=True)
    
    merged_df = pd.merge(interactions_df, recipes_df_text[['recipe_id', 'text']], on='recipe_id', how='inner')
    
    # Since a recipe_id can have both a good and a bad rating from different users,
    # we might have duplicates. We need a strategy. Let's take the majority vote,
    # or if tied, consider it ambiguous and drop. Or simpler: just drop duplicates based on recipe_id, keeping one label.
    # Let's check the balance again after merging.
    
    # Let's count labels per recipe
    label_counts = merged_df.groupby('recipe_id')['label'].nunique()
    recipes_with_conflicting_labels = label_counts[label_counts > 1].index
    
    # Filter out recipes that have conflicting labels (both 0 and 1)
    # This is a clean way to handle ambiguity.
    clean_df = merged_df[~merged_df['recipe_id'].isin(recipes_with_conflicting_labels)]
    
    # Now, drop duplicates by recipe_id, as each has a consistent label
    final_df = clean_df.drop_duplicates(subset=['recipe_id']).reset_index(drop=True)
    final_df = final_df[['text', 'label']]
    
    print(f"Saving final dataset to {output_file}...")
    final_df.to_csv(output_file, index=False)
    
    print("Data preparation complete!")
    print(f"Dataset shape: {final_df.shape}")
    print("Label distribution:")
    print(final_df['label'].value_counts(normalize=True))


if __name__ == '__main__':
    main() 