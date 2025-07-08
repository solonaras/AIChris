"""
Script to remove the background from AIChris avatar images and save them with transparent backgrounds.
This uses a simple color-based approach to make the background transparent.
"""
from PIL import Image
import numpy as np
import os

def remove_background(input_path, output_path, threshold=30):
    """
    Remove the background from an image and save it with a transparent background.
    
    Args:
        input_path: Path to the input image
        output_path: Path to save the output image
        threshold: Color difference threshold for background detection
    """
    # Open the image
    img = Image.open(input_path)
    img = img.convert("RGBA")
    
    # Convert to numpy array for faster processing
    data = np.array(img)
    
    # Get the background color (assume top-left pixel is background)
    bg_color = data[0, 0, :3]
    
    # Create a mask where True means the pixel is close to the background color
    r, g, b = data[:, :, 0], data[:, :, 1], data[:, :, 2]
    color_distance = np.sqrt(
        (r - bg_color[0]) ** 2 + 
        (g - bg_color[1]) ** 2 + 
        (b - bg_color[2]) ** 2
    )
    mask = color_distance < threshold
    
    # Set alpha channel to 0 (transparent) where mask is True
    data[:, :, 3] = np.where(mask, 0, 255)
    
    # Convert back to PIL Image and save
    result = Image.fromarray(data)
    result.save(output_path)
    print(f"Saved image with transparent background to {output_path}")

def main():
    # Paths to the avatar images
    closed_path = "C:/Users/User/Desktop/AiChris 3.0/chris avatar cropped.png"
    open_path = "C:/Users/User/Desktop/AiChris 3.0/Aichrisopenmouth.png"
    
    # Output paths
    closed_output = "C:/Users/User/Desktop/AiChris 3.0/chris_avatar_transparent.png"
    open_output = "C:/Users/User/Desktop/AiChris 3.0/Aichrisopenmouth_transparent.png"
    
    # Remove backgrounds
    print(f"Processing closed mouth avatar: {closed_path}")
    remove_background(closed_path, closed_output)
    
    print(f"Processing open mouth avatar: {open_path}")
    remove_background(open_path, open_output)
    
    # Update the avatar paths in avatar.py
    update_avatar_paths(closed_output, open_output)
    
    print("Done! The avatar images now have transparent backgrounds.")
    print("The avatar.py file has been updated to use the new images.")

def update_avatar_paths(closed_path, open_path):
    """Update the avatar paths in avatar.py"""
    with open("avatar.py", "r") as f:
        content = f.read()
    
    # Replace the paths
    content = content.replace(
        'AVATAR_CLOSED_PATH = "C:/Users/User/Desktop/AiChris 3.0/chris avatar cropped.png"',
        f'AVATAR_CLOSED_PATH = "{closed_path}"'
    )
    content = content.replace(
        'AVATAR_OPEN_PATH = "C:/Users/User/Desktop/AiChris 3.0/Aichrisopenmouth.png"',
        f'AVATAR_OPEN_PATH = "{open_path}"'
    )
    
    # Write the updated content back
    with open("avatar.py", "w") as f:
        f.write(content)
    
    print("Updated avatar.py with new image paths")

if __name__ == "__main__":
    main() 