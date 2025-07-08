import os
import whisper

# Set ffmpeg path for Whisper
ffmpeg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg-2025-03-24-git-cbbc927a67-essentials_build", "bin", "ffmpeg.exe")
os.environ["PATH"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg-2025-03-24-git-cbbc927a67-essentials_build", "bin") + os.pathsep + os.environ["PATH"]
os.environ["FFMPEG_PATH"] = ffmpeg_path
print(f"FFMPEG path set to: {ffmpeg_path}")

# Load the model
print("Loading Whisper model...")
model = whisper.load_model("base")
print("Model loaded successfully")

# Try to transcribe a simple audio file if available
try:
    # Create a simple test to see if ffmpeg is accessible via subprocess
    import subprocess
    result = subprocess.run([ffmpeg_path, "-version"], capture_output=True, text=True)
    print("\nFFmpeg version check:")
    print(result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout)
    print(f"Return code: {result.returncode}")
except Exception as e:
    print(f"Error running ffmpeg: {e}")