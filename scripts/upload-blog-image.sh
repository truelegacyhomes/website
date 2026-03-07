#!/bin/bash
# TLH Blog Image Upload Script
# Compresses image and uploads to Cloudflare R2
# Usage: ./upload-blog-image.sh <image-path> [output-name]

set -e

# Config - UPDATE THESE after R2 bucket is created
R2_BUCKET="tlh-blog-images"
R2_ACCOUNT_ID="YOUR_ACCOUNT_ID"  # Get from Cloudflare dashboard
R2_PUBLIC_URL="https://images.truelegacyhomes.com"  # Custom domain or R2.dev URL

# Check args
if [ -z "$1" ]; then
    echo "Usage: $0 <image-path> [output-name]"
    echo "Example: $0 ~/Desktop/my-article.png estate-sale-guide"
    exit 1
fi

INPUT="$1"
OUTPUT_NAME="${2:-$(basename "${INPUT%.*}")}"
OUTPUT_FILE="/tmp/${OUTPUT_NAME}.jpg"

# Check if wrangler is installed
if ! command -v wrangler &> /dev/null; then
    echo "❌ Wrangler CLI not found. Install with: npm install -g wrangler"
    exit 1
fi

echo "📸 Compressing image..."
# Resize to max 1200px width, convert to JPG at 80% quality
sips -Z 1200 -s format jpeg -s formatOptions 80 "$INPUT" --out "$OUTPUT_FILE"

# Get file size
SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
echo "✅ Compressed to $SIZE"

echo "☁️  Uploading to R2..."
wrangler r2 object put "${R2_BUCKET}/${OUTPUT_NAME}.jpg" --file="$OUTPUT_FILE"

# Output the URL
echo ""
echo "✅ Done! Use this URL in your article:"
echo "${R2_PUBLIC_URL}/${OUTPUT_NAME}.jpg"
echo ""
echo "HTML: <img src=\"${R2_PUBLIC_URL}/${OUTPUT_NAME}.jpg\" alt=\"${OUTPUT_NAME}\">"

# Cleanup
rm "$OUTPUT_FILE"
