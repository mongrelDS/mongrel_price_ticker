# @title CV Code

import pandas as pd
import numpy as np
import tensorflow as tf
import requests
from io import BytesIO
from PIL import Image
from tensorflow.keras.applications.vgg16 import VGG16, preprocess_input
from tensorflow.keras.preprocessing import image
from scipy.spatial.distance import cosine
import time
from concurrent.futures import ThreadPoolExecutor
import os

# Disable TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

def load_image_from_url(url, target_size=(224, 224)):
    """
    Download and process an image from a URL.
    Returns a preprocessed image ready for feature extraction.
    """
    try:
        # Download the image
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise exception for HTTP errors

        # Open the image using PIL
        img = Image.open(BytesIO(response.content))

        # Convert to RGB (in case it's RGBA or another format)
        img = img.convert('RGB')

        # Resize to target size
        img = img.resize(target_size)

        # Convert to array and preprocess for the model
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array = preprocess_input(img_array)

        return img_array

    except Exception as e:
        print(f"Error loading image from {url}: {str(e)}")
        return None

def extract_features(model, img_array):
    """
    Extract features from an image using the provided model.
    """
    if img_array is None:
        return None

    features = model.predict(img_array, verbose=0)
    return features.flatten()

def calculate_similarity(features1, features2):
    """
    Calculate cosine similarity between two feature vectors.
    Returns a value between 0 and 1, where 1 means identical.
    """
    if features1 is None or features2 is None:
        return 0.0

    # Calculate cosine similarity (1 - cosine distance)
    similarity = 1 - cosine(features1, features2)

    # Handle NaN values
    if np.isnan(similarity):
        return 0.0

    return float(similarity)

def process_image_pair(row, model):
    """
    Process a single row from the DataFrame.
    Downloads both images, extracts features, and calculates similarity.
    """
    # Get image URLs
    img_url_x = row['imgurl_x']
    img_url_y = row['imgurl_y']

    # Load and preprocess images
    img_array_x = load_image_from_url(img_url_x)
    img_array_y = load_image_from_url(img_url_y)

    # Extract features
    features_x = extract_features(model, img_array_x)
    features_y = extract_features(model, img_array_y)

    # Calculate similarity
    similarity = calculate_similarity(features_x, features_y)

    return similarity

def calculate_similarity_scores(df_cv, batch_size: int = 10, max_workers: int = 4, save_intermediate: bool = False, intermediate_path: str = "cv_scores_temp.csv"):
    """
    Calculate similarity scores for image pairs in the DataFrame
    and add them as a new column 'cv_score'.

    Args:
        df_cv (pandas.DataFrame): DataFrame with imgurl_x and imgurl_y columns

    Returns:
        pandas.DataFrame: Updated DataFrame with cv_score column
    """
    # Print info about the DataFrame
    print(f"Processing DataFrame with {len(df_cv)} rows")

    # Load pre-trained model
    print("Loading TensorFlow model...")
    model = VGG16(weights='imagenet', include_top=False, pooling='avg')

    # Process images and calculate similarity scores
    print("Processing images and calculating similarity scores...")
    start_time = time.time()

    # Preallocate similarities array to avoid repeated list growth
    similarities = np.empty(len(df_cv), dtype=np.float32)

    # Use ThreadPoolExecutor for parallel processing
    import gc
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Process in batches to show progress
        for i in range(0, len(df_cv), batch_size):
            end_idx = min(i + batch_size, len(df_cv))
            print(f"Processing batch {i//batch_size + 1}/{(len(df_cv)-1)//batch_size + 1} (rows {i} to {end_idx-1})...")

            # Submit batch to executor using index-based processing to avoid row copies
            batch_indices = list(range(i, end_idx))
            batch_results = list(executor.map(
                lambda idx: process_image_pair(df_cv.iloc[idx], model),
                batch_indices
            ))

            # Assign results directly into preallocated array by index
            for local_pos, idx in enumerate(batch_indices):
                similarities[idx] = batch_results[local_pos]

            # Encourage early memory release
            del batch_indices
            del batch_results
            gc.collect()

            # Optional: save intermediate progress
            if save_intermediate:
                temp_df = df_cv.iloc[:end_idx].copy()
                temp_df['cv_score'] = similarities[:end_idx]
                try:
                    temp_df.to_csv(intermediate_path, index=False)
                except Exception:
                    pass

    # Add similarity scores to DataFrame
    df_cv['cv_score'] = similarities

    # Print statistics
    elapsed_time = time.time() - start_time
    print(f"\nProcessing completed in {elapsed_time:.2f} seconds")
    print(f"Average similarity score: {np.mean(similarities):.4f}")
    print(f"Min similarity score: {min(similarities):.4f}")
    print(f"Max similarity score: {max(similarities):.4f}")

    return df_cv

def main():
    # Assuming df_cv already exists
    # This is just a placeholder to show how the function would be called
    try:
        # If you want to test with a CSV file, uncomment these lines:
        # df_cv = pd.read_csv('match_df_cv.csv')
        # df_cv = calculate_similarity_scores(df_cv)
        # df_cv.to_csv('match_df_with_cv_scores.csv', index=False)

        print("To use this module, import and call calculate_similarity_scores(df_cv)")
        print("Example:")
        print("  from image_similarity import calculate_similarity_scores")
        print("  df_cv = calculate_similarity_scores(df_cv)")
    except NameError:
        print("This script is designed to be imported and used with an existing DataFrame.")
        print("Example usage:")
        print("  from image_similarity import calculate_similarity_scores")
        print("  df_cv = calculate_similarity_scores(df_cv)")

# Function to be called from outside when df_cv already exists
def add_cv_scores(df_cv):
    """
    Main function to be called when DataFrame already exists.
    Takes an existing DataFrame with image URLs and adds cv_score column.

    Args:
        df_cv (pandas.DataFrame): DataFrame with imgurl_x and imgurl_y columns

    Returns:
        pandas.DataFrame: Same DataFrame with added cv_score column
    """
    return calculate_similarity_scores(df_cv)

if __name__ == "__main__":
    main()