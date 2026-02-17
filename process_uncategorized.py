#!/usr/bin/env python3
"""
Process WordPress Uncategorized posts and convert to TLH Markdown site HTML files
"""
import json
import re
import os
import requests
from html import unescape
from datetime import datetime

# Brand color
BRAND_COLOR = "#38b5ad"

# Category mapping keywords
CATEGORY_KEYWORDS = {
    "Real Estate": ["realtor", "home buying", "selling home", "real estate", "property", "cash offer", "home sale"],
    "Renovation": ["renovation", "repair", "remodel", "update", "fix", "contractor", "construction"],
    "Senior Moving": ["senior", "assisted living", "downsizing", "elder", "aging", "retirement", "care placement"],
    "Antique Collectibles": ["antique", "collectible", "vintage", "mid-century", "modern furniture", "barbie", "kitchenware", "pottery", "fine art", "rare"],
    "News": ["announcement", "news", "update", "company"],
    "Estate Sales": ["estate sale", "sale at", "pricing", "selling items", "treasure", "shopper"]  # default fallback
}

def categorize_post(title, content):
    """Determine category based on title and content"""
    text = (title + " " + content).lower()
    
    # Strip HTML tags from content for analysis
    text = re.sub(r'<[^>]+>', ' ', text)
    
    # Check each category
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in text:
                return category
    
    # Default to Estate Sales
    return "Estate Sales"

def clean_html_content(html):
    """Clean WordPress HTML content"""
    # Remove script and style tags
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Remove noscript
    html = re.sub(r'<noscript[^>]*>.*?</noscript>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Remove inline styles
    html = re.sub(r'\s*style="[^"]*"', '', html)
    # Remove data attributes
    html = re.sub(r'\s*data-[a-z-]+="[^"]*"', '', html)
    # Remove class attributes with complex names
    html = re.sub(r'\s*class="[^"]*"', '', html)
    # Clean up multiple spaces
    html = re.sub(r'\s+', ' ', html)
    # Fix common entities
    html = unescape(html)
    return html.strip()

def extract_text_content(html):
    """Extract plain text from HTML for excerpt"""
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)
    text = unescape(text)
    return text.strip()[:300] + "..." if len(text) > 300 else text.strip()

def get_featured_image_url(media_id):
    """Get featured image URL from WordPress media API"""
    if not media_id or media_id == 0:
        return None
    try:
        resp = requests.get(f"https://www.truelegacyhomes.com/wp-json/wp/v2/media/{media_id}", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('source_url')
    except Exception as e:
        print(f"  Warning: Could not fetch media {media_id}: {e}")
    return None

def download_image(url, local_path):
    """Download image to local path"""
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, 'wb') as f:
                f.write(resp.content)
            return True
    except Exception as e:
        print(f"  Warning: Could not download {url}: {e}")
    return False

def create_html_file(post, category, image_filename):
    """Create HTML file for blog post"""
    title = unescape(post['title']['rendered'])
    slug = post['slug']
    date = post['date'][:10]  # YYYY-MM-DD
    content = post['content']['rendered']
    
    # Clean content
    clean_content = clean_html_content(content)
    
    # If content is mostly just images/galleries, create a simple description
    text_content = extract_text_content(content)
    if len(text_content) < 50:
        text_content = f"Estate sale listing at {title}. View photos and details."
    
    # Create formatted date
    date_obj = datetime.strptime(date, '%Y-%m-%d')
    formatted_date = date_obj.strftime('%B %d, %Y')
    
    # Image path
    image_html = ""
    if image_filename:
        image_html = f'<img src="images/{image_filename}" alt="{title}" class="featured-image">'
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | True Legacy Homes</title>
  <meta name="description" content="{text_content[:160]}">
  <link rel="canonical" href="https://iambarabbas.github.io/tlh-markdown-demo/blog/{slug}.html">
  <link rel="icon" href="../images/favicon.png">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
    header {{ background: #104674; color: white; padding: 1rem; }}
    header a {{ color: white; text-decoration: none; }}
    nav {{ display: flex; justify-content: space-between; align-items: center; max-width: 1200px; margin: 0 auto; }}
    nav ul {{ list-style: none; display: flex; gap: 1.5rem; }}
    .container {{ max-width: 800px; margin: 0 auto; padding: 2rem; }}
    .category-badge {{ 
      display: inline-block; 
      background: {BRAND_COLOR}; 
      color: white; 
      padding: 0.25rem 0.75rem; 
      border-radius: 4px; 
      font-size: 0.875rem; 
      font-weight: 600;
      margin-bottom: 0.5rem;
    }}
    .post-meta {{ color: #666; margin-bottom: 1.5rem; }}
    h1 {{ font-size: 2rem; margin: 1rem 0; color: #104674; }}
    .featured-image {{ width: 100%; max-height: 400px; object-fit: cover; border-radius: 8px; margin-bottom: 2rem; }}
    .content {{ line-height: 1.8; }}
    .content p {{ margin-bottom: 1rem; }}
    .content img {{ max-width: 100%; height: auto; border-radius: 8px; margin: 1rem 0; }}
    .back-link {{ display: inline-block; margin-top: 2rem; color: {BRAND_COLOR}; text-decoration: none; }}
    .back-link:hover {{ text-decoration: underline; }}
    footer {{ background: #f5f5f5; padding: 2rem; text-align: center; margin-top: 3rem; }}
    footer a {{ color: {BRAND_COLOR}; }}
  </style>
</head>
<body>
  <header>
    <nav>
      <a href="../index.html"><strong>True Legacy Homes</strong></a>
      <ul>
        <li><a href="../index.html">Home</a></li>
        <li><a href="../estate-sales.html">Estate Sales</a></li>
        <li><a href="../senior-care.html">Senior Care</a></li>
        <li><a href="../contact.html">Contact</a></li>
      </ul>
    </nav>
  </header>
  
  <main class="container">
    <article>
      <span class="category-badge">{category}</span>
      <h1>{title}</h1>
      <p class="post-meta">Published on {formatted_date}</p>
      {image_html}
      <div class="content">
        {clean_content if len(clean_content) > 100 else f"<p>{text_content}</p>"}
      </div>
    </article>
    <a href="../index.html" class="back-link">← Back to Home</a>
  </main>
  
  <footer>
    <p>&copy; 2024 True Legacy Homes | <a href="tel:+16194501702">(619) 450-1702</a> | <a href="mailto:info@truelegacyhomes.com">info@truelegacyhomes.com</a></p>
  </footer>
</body>
</html>'''
    
    return html

def main():
    # Load posts from file
    with open('/tmp/uncategorized-posts.json', 'r') as f:
        posts = json.load(f)
    
    print(f"\n📚 Processing {len(posts)} uncategorized posts...\n")
    
    results = []
    
    for post in posts:
        title = unescape(post['title']['rendered'])
        slug = post['slug']
        content = post['content']['rendered']
        featured_media = post.get('featured_media', 0)
        
        # Categorize
        category = categorize_post(title, content)
        
        print(f"📝 {title}")
        print(f"   → Category: {category}")
        
        # Get and download featured image
        image_filename = None
        if featured_media:
            image_url = get_featured_image_url(featured_media)
            if image_url:
                ext = image_url.split('.')[-1].split('?')[0][:4]
                if ext not in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
                    ext = 'jpg'
                image_filename = f"{slug}.{ext}"
                local_path = f"blog/images/{image_filename}"
                if download_image(image_url, local_path):
                    print(f"   → Image: {image_filename}")
                else:
                    image_filename = None
        
        # Create HTML file
        html_content = create_html_file(post, category, image_filename)
        html_path = f"blog/{slug}.html"
        with open(html_path, 'w') as f:
            f.write(html_content)
        print(f"   → Created: {html_path}")
        
        results.append({
            'title': title,
            'category': category,
            'slug': slug
        })
        print()
    
    # Print summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    print(f"\nTotal posts transferred: {len(results)}")
    
    # Count by category
    category_counts = {}
    for r in results:
        cat = r['category']
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    print("\nPosts by category:")
    for cat, count in sorted(category_counts.items()):
        print(f"  • {cat}: {count}")
    
    print("\n📝 Post categorization:")
    for r in results:
        print(f"  • {r['title'][:50]}... → {r['category']}")
    
    return results

if __name__ == "__main__":
    main()
