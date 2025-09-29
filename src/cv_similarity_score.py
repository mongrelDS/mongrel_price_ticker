#!/usr/bin/env python3
"""
Computer Vision Similarity Score Module using OpenCV

This module provides image similarity scoring using OpenCV for feature extraction
and comparison. It's designed to be lightweight and efficient compared to 
TensorFlow-based solutions.

Features:
- ORB feature detection and matching
- Histogram-based color similarity
- Structural similarity using template matching
- Combined similarity scoring
- Parallel processing support

Author: Mongrel Data Lab
Date: 2024
"""

import pandas as pd
import numpy as np
import cv2
import requests
from io import BytesIO
from PIL import Image
from scipy.spatial.distance import cosine
import time
from concurrent.futures import ThreadPoolExecutor
import os
from typing import Optional, Tuple

def load_image_from_url(url: str, target_size: Tuple[int, int] = (300, 300)) -> Optional[np.ndarray]:
    """
    Download and process an image from a URL using OpenCV.
    
    Args:
        url (str): Image URL
        target_size (tuple): Target size (width, height)
    
    Returns:
        np.ndarray: Processed image array or None if failed
    """
    try:
        # Download the image
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Convert to numpy array
        img_array = np.frombuffer(response.content, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        if img is None:
            return None
            
        # Convert BGR to RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Resize image
        img = cv2.resize(img, target_size)
        
        return img
        
    except Exception as e:
        print(f"Error loading image from {url}: {str(e)}")
        return None

def extract_orb_features(img: np.ndarray, max_features: int = 500) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extract ORB features from an image.
    
    Args:
        img (np.ndarray): Input image
        max_features (int): Maximum number of features to extract
    
    Returns:
        tuple: (keypoints, descriptors)
    """
    if img is None:
        return None, None
        
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    
    # Initialize ORB detector
    orb = cv2.ORB_create(nfeatures=max_features)
    
    # Find keypoints and descriptors
    keypoints, descriptors = orb.detectAndCompute(gray, None)
    
    return keypoints, descriptors

def calculate_orb_similarity(desc1: np.ndarray, desc2: np.ndarray) -> float:
    """
    Calculate similarity based on ORB feature matching.
    
    Args:
        desc1, desc2: ORB descriptors
    
    Returns:
        float: Similarity score between 0 and 1
    """
    if desc1 is None or desc2 is None or len(desc1) == 0 or len(desc2) == 0:
        return 0.0
    
    try:
        # Use BFMatcher for ORB descriptors
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(desc1, desc2)
        
        # Sort matches by distance
        matches = sorted(matches, key=lambda x: x.distance)
        
        # Calculate similarity based on number of good matches
        good_matches = [m for m in matches if m.distance < 50]  # Threshold for good matches
        similarity = len(good_matches) / min(len(desc1), len(desc2))
        
        return min(similarity, 1.0)
        
    except Exception:
        return 0.0

def calculate_histogram_similarity(img1: np.ndarray, img2: np.ndarray) -> float:
    """
    Calculate color histogram similarity between two images.
    
    Args:
        img1, img2: Input images
    
    Returns:
        float: Histogram similarity score between 0 and 1
    """
    if img1 is None or img2 is None:
        return 0.0
    
    try:
        # Calculate histograms for each channel
        hist1 = []
        hist2 = []
        
        for i in range(3):  # RGB channels
            hist1.append(cv2.calcHist([img1], [i], None, [256], [0, 256]))
            hist2.append(cv2.calcHist([img2], [i], None, [256], [0, 256]))
        
        # Calculate correlation for each channel
        correlations = []
        for h1, h2 in zip(hist1, hist2):
            corr = cv2.compareHist(h1, h2, cv2.HISTCMP_CORREL)
            correlations.append(corr)
        
        # Average correlation across channels
        avg_correlation = np.mean(correlations)
        
        # Convert to 0-1 range (correlation is -1 to 1)
        return max(0.0, (avg_correlation + 1) / 2)
        
    except Exception:
        return 0.0

def calculate_structural_similarity(img1: np.ndarray, img2: np.ndarray) -> float:
    """
    Calculate structural similarity using template matching.
    
    Args:
        img1, img2: Input images
    
    Returns:
        float: Structural similarity score between 0 and 1
    """
    if img1 is None or img2 is None:
        return 0.0
    
    try:
        # Convert to grayscale
        gray1 = cv2.cvtColor(img1, cv2.COLOR_RGB2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_RGB2GRAY)
        
        # Resize to same size if different
        if gray1.shape != gray2.shape:
            gray2 = cv2.resize(gray2, (gray1.shape[1], gray1.shape[0]))
        
        # Calculate normalized cross correlation
        result = cv2.matchTemplate(gray1, gray2, cv2.TM_CCOEFF_NORMED)
        similarity = np.max(result)
        
        return max(0.0, similarity)
        
    except Exception:
        return 0.0

def calculate_combined_similarity(img1: np.ndarray, img2: np.ndarray) -> float:
    """
    Calculate combined similarity score using multiple methods.
    
    Args:
        img1, img2: Input images
    
    Returns:
        float: Combined similarity score between 0 and 1
    """
    if img1 is None or img2 is None:
        return 0.0
    
    try:
        # Extract ORB features
        kp1, desc1 = extract_orb_features(img1)
        kp2, desc2 = extract_orb_features(img2)
        
        # Calculate different similarity metrics
        orb_sim = calculate_orb_similarity(desc1, desc2)
        hist_sim = calculate_histogram_similarity(img1, img2)
        struct_sim = calculate_structural_similarity(img1, img2)
        
        # Weighted combination (adjust weights based on your needs)
        weights = [0.4, 0.3, 0.3]  # ORB, Histogram, Structural
        similarities = [orb_sim, hist_sim, struct_sim]
        
        combined_sim = sum(w * s for w, s in zip(weights, similarities))
        
        return min(1.0, max(0.0, combined_sim))
        
    except Exception:
        return 0.0

def process_image_pair(row: pd.Series) -> float:
    """
    Process a single row from the DataFrame.
    Downloads both images and calculates similarity.
    
    Args:
        row: DataFrame row with imgurl_x and imgurl_y columns
    
    Returns:
        float: Similarity score between 0 and 1
    """
    try:
        # Get image URLs
        img_url_x = row['imgurl_x']
        img_url_y = row['imgurl_y']
        
        # Skip if URLs are missing or invalid
        if pd.isna(img_url_x) or pd.isna(img_url_y) or not img_url_x or not img_url_y:
            return 0.0
        
        # Load images
        img1 = load_image_from_url(img_url_x)
        img2 = load_image_from_url(img_url_y)
        
        # Calculate combined similarity
        similarity = calculate_combined_similarity(img1, img2)
        
        return similarity
        
    except Exception as e:
        print(f"Error processing image pair: {str(e)}")
        return 0.0

def calculate_similarity_scores(df_cv: pd.DataFrame, batch_size: int = 10, max_workers: int = 4, 
                               save_intermediate: bool = False, intermediate_path: str = "cv_scores_temp.csv") -> pd.DataFrame:
    """
    Calculate similarity scores for image pairs in the DataFrame
    and add them as a new column 'cv_score'.
    
    Args:
        df_cv (pd.DataFrame): DataFrame with imgurl_x and imgurl_y columns
        batch_size (int): Number of rows to process in each batch
        max_workers (int): Maximum number of worker threads
        save_intermediate (bool): Whether to save intermediate results
        intermediate_path (str): Path for intermediate results
    
    Returns:
        pd.DataFrame: Updated DataFrame with cv_score column
    """
    print(f"Processing DataFrame with {len(df_cv)} rows using OpenCV")
    
    # Validate required columns
    required_cols = ['imgurl_x', 'imgurl_y']
    missing_cols = [col for col in required_cols if col not in df_cv.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Process images and calculate similarity scores
    print("Processing images and calculating similarity scores...")
    start_time = time.time()
    
    # Preallocate similarities array
    similarities = np.empty(len(df_cv), dtype=np.float32)
    
    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Process in batches to show progress
        for i in range(0, len(df_cv), batch_size):
            end_idx = min(i + batch_size, len(df_cv))
            print(f"Processing batch {i//batch_size + 1}/{(len(df_cv)-1)//batch_size + 1} (rows {i} to {end_idx-1})...")
            
            # Submit batch to executor
            batch_indices = list(range(i, end_idx))
            batch_results = list(executor.map(
                lambda idx: process_image_pair(df_cv.iloc[idx]),
                batch_indices
            ))
            
            # Assign results
            for local_pos, idx in enumerate(batch_indices):
                similarities[idx] = batch_results[local_pos]
            
            # Optional: save intermediate progress
            if save_intermediate:
                temp_df = df_cv.iloc[:end_idx].copy()
                temp_df['cv_score'] = similarities[:end_idx]
                try:
                    temp_df.to_csv(intermediate_path, index=False)
                except Exception:
                    pass
    
    # Add similarity scores to DataFrame
    df_cv = df_cv.copy()  # Avoid modifying original
    df_cv['cv_score'] = similarities
    
    # Print statistics
    elapsed_time = time.time() - start_time
    print(f"\nProcessing completed in {elapsed_time:.2f} seconds")
    print(f"Average similarity score: {np.mean(similarities):.4f}")
    print(f"Min similarity score: {np.min(similarities):.4f}")
    print(f"Max similarity score: {np.max(similarities):.4f}")
    
    return df_cv

def add_cv_scores(df_cv: pd.DataFrame) -> pd.DataFrame:
    """
    Main function to be called when DataFrame already exists.
    Takes an existing DataFrame with image URLs and adds cv_score column.
    
    Args:
        df_cv (pd.DataFrame): DataFrame with imgurl_x and imgurl_y columns
    
    Returns:
        pd.DataFrame: Same DataFrame with added cv_score column
    """
    return calculate_similarity_scores(df_cv)

def main():
    """Main function for testing"""
    print("OpenCV-based Computer Vision Similarity Scoring")
    print("To use this module, import and call add_cv_scores(df_cv)")
    print("Example:")
    print("  from cv_similarity_score import add_cv_scores")
    print("  df_cv = add_cv_scores(df_cv)")

if __name__ == "__main__":
    main()