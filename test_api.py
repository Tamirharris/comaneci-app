import os
import replicate
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get token from environment
token = os.environ.get("REPLICATE_API_TOKEN")
if not token:
    raise ValueError("REPLICATE_API_TOKEN not found in environment variables")

# Create client
client = replicate.Client(api_token=token)

# Try to run a simple prediction
try:
    model = client.models.get("stability-ai/stable-diffusion")
    version = model.versions.get("db21e45d3f7023abc2a46ee38a23973f6dce16bb082a930b0c49861f96d1e5bf")
    
    # Run prediction
    prediction = version.predict(prompt="a photo of an astronaut riding a horse")
    print("Prediction successful!")
    print(prediction)
except Exception as e:
    print(f"Error: {e}")
