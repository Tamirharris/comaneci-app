# Comaneci Video Generator

A web application that generates videos from images using the Replicate API and the kwaivgi/kling-v1.6-standard model.

## Features

- Multiple image upload support
- Batch video generation
- Customizable aspect ratios
- Folder organization system
- Video preview capabilities

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the root directory and add your Replicate API key:
```
REPLICATE_API_TOKEN=your_api_key_here
```

3. Run the application:
```bash
python app.py
```

## Usage

1. Upload Images: Select multiple images to process
2. Configure Settings: Choose aspect ratio and duration
3. Generate Videos: Click generate to create videos from all uploaded images
4. Manage Files: Use the folder management system to organize your videos
