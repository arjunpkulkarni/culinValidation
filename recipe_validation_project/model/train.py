import pandas as pd
from datasets import Dataset, DatasetDict
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer
import torch
import os
import numpy as np
from sklearn.metrics import accuracy_score

def compute_metrics(eval_pred):
    """Computes accuracy score for evaluation."""
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    return {"accuracy": accuracy_score(labels, predictions)}

def main():
    """Main function to train the model."""
    print("Starting model training...")

    # --- 1. Load and Prepare Dataset ---
    print("Loading prepared dataset...")
    
    # Construct the path to the data file relative to this script's location
    script_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(script_dir, '..'))
    data_file_path = os.path.join(project_root, 'data', 'processed', 'recipe_validation_dataset_raw.csv')

    # Load the full dataset from the CSV file
    full_df = pd.read_csv(data_file_path)
    
    # For demonstration and faster training, let's sample the data.
    # You can comment this out to use the full dataset.
    # Sample 10% of the data while maintaining label distribution
    # print("Subsampling data for faster training demonstration...")
    # df_sampled = full_df.groupby('label').apply(lambda x: x.sample(frac=0.1)).reset_index(drop=True)
    # dataset = Dataset.from_pandas(df_sampled)
    
    # Using the full dataset
    dataset = Dataset.from_pandas(full_df)

    # Split the dataset into training and testing sets (90/10 split)
    print("Splitting dataset into train and test sets...")
    train_test_split = dataset.train_test_split(test_size=0.1)
    dataset_dict = DatasetDict({
        'train': train_test_split['train'],
        'test': train_test_split['test']
    })
    
    print(f"Train dataset size: {len(dataset_dict['train'])}")
    print(f"Test dataset size: {len(dataset_dict['test'])}")

    # --- 2. Tokenization ---
    model_name = "distilroberta-base"
    print(f"Loading tokenizer for '{model_name}'...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    def tokenize_function(examples):
        return tokenizer(examples["text"], padding="max_length", truncation=True, max_length=512)

    print("Tokenizing datasets...")
    tokenized_datasets = dataset_dict.map(tokenize_function, batched=True)

    # Remove the original text column to save memory
    tokenized_datasets = tokenized_datasets.remove_columns(["text"])
    # Rename 'label' to 'labels' as expected by the model
    tokenized_datasets = tokenized_datasets.rename_column("label", "labels")
    # Set the format to PyTorch tensors
    tokenized_datasets.set_format("torch")

    # --- 3. Model Training ---
    print(f"Loading model '{model_name}' for sequence classification...")
    model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=2)

    # Define output directory for model and training artifacts
    output_dir = os.path.join(project_root, 'model', 'saved_model')

    # Check for available device
    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Training will use device: {device}")
    
    # For MPS, some operations might need to be explicitly handled on CPU
    # No specific changes needed here for standard Trainer, but good to be aware.

    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=1,  # Start with 1 epoch for a quick baseline
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        warmup_steps=500,
        weight_decay=0.01,
        logging_dir=os.path.join(project_root, 'logs'),
        logging_steps=100,
        evaluation_strategy="steps",
        eval_steps=500,
        save_strategy="steps",
        save_steps=500,
        load_best_model_at_end=True,
        metric_for_best_model="accuracy", # You can also use "loss", "f1", etc.
        greater_is_better=True,
    )
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_datasets["train"],
        eval_dataset=tokenized_datasets["test"],
        compute_metrics=compute_metrics,
    )

    print("Starting training...")
    trainer.train()

    # --- 4. Save Final Model ---
    print(f"Saving the fine-tuned model and tokenizer to {output_dir}...")
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    print("Training complete!")

if __name__ == "__main__":
    main() 