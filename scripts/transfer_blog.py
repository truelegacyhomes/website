#!/usr/bin/env python3
"""
Transfer WordPress Estate Sales posts to TLH Markdown site
"""
import json
import os
import re
import html
import urllib.request
import urllib.error
from datetime import datetime
from urllib.parse import urlparse
import ssl

# Config
WP_API = "https://www.truelegacyhomes.com/wp-json/wp/v2"
OUTPUT_DIR = "/Users/admin/.openclaw/workspace/tlh-rebuild/blog"
IMAGES_DIR = f"{OUTPUT_DIR}/images"

# SSL context
ssl_context = ssl.create_default_context()

# Ensure directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

def fetch_url(url):
    """Fetch URL and return response data"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30, context=ssl_context) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return None

def fetch_binary(url):
    """Fetch binary data from URL"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30, context=ssl_context) as response:
            return response.read()
    except Exception as e:
        print(f"  Error fetching binary {url}: {e}")
        return None

def fetch_posts():
    """Fetch all Estate Sales posts (category 5)"""
    posts = []
    page = 1
    while True:
        url = f"{WP_API}/posts?categories=5&per_page=100&page={page}&_fields=id,title,slug,date,content,excerpt,featured_media"
        data = fetch_url(url)
        if not data:
            break
        parsed = json.loads(data)
        if not parsed:
            break
        posts.extend(parsed)
        page += 1
    return posts

def fetch_media_url(media_id):
    """Fetch featured image URL from media ID"""
    if not media_id:
        return None
    url = f"{WP_API}/media/{media_id}?_fields=source_url"
    data = fetch_url(url)
    if data:
        try:
            return json.loads(data).get('source_url')
        except:
            pass
    return None

def download_image(url, slug):
    """Download image and save locally"""
    if not url:
        return None
    try:
        ext = os.path.splitext(urlparse(url).path)[1] or '.jpg'
        filename = f"{slug}{ext}"
        filepath = f"{IMAGES_DIR}/{filename}"
        
        if os.path.exists(filepath):
            return f"images/{filename}"
        
        data = fetch_binary(url)
        if data:
            with open(filepath, 'wb') as f:
                f.write(data)
            return f"images/{filename}"
    except Exception as e:
        print(f"  Warning: Could not download image for {slug}: {e}")
    return None

def clean_content(raw_html):
    """Clean WordPress HTML and extract readable content"""
    if not raw_html:
        return ""
    
    # Decode HTML entities
    text = html.unescape(raw_html)
    
    # Remove style tags and their content
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove inline styles
    text = re.sub(r'\s*style="[^"]*"', '', text)
    
    # Remove class and id attributes with avia/av- prefixes
    text = re.sub(r'\s*class="[^"]*avia[^"]*"', '', text)
    text = re.sub(r'\s*class="[^"]*av-[^"]*"', '', text)
    text = re.sub(r'\s*id="[^"]*"', '', text)
    
    # Remove WordPress page builder divs
    text = re.sub(r'<div[^>]*class="[^"]*(?:avia|flex_column|container|template-page|post-entry|entry-content)[^"]*"[^>]*>', '', text, flags=re.IGNORECASE)
    
    # Remove section tags
    text = re.sub(r'<section[^>]*class="[^"]*av_textblock[^"]*"[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</section>', '', text, flags=re.IGNORECASE)
    
    # Remove special heading wrapper divs
    text = re.sub(r'<div[^>]*class="[^"]*av-special-heading[^"]*"[^>]*>.*?</div>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove empty divs
    text = re.sub(r'<div[^>]*>\s*</div>', '', text, flags=re.DOTALL)
    
    # Clean up remaining divs - keep content but simplify
    text = re.sub(r'<div[^>]*>', '', text)
    text = re.sub(r'</div>', '', text)
    
    # Remove main/aside tags
    text = re.sub(r'<main[^>]*>', '', text)
    text = re.sub(r'</main>', '', text)
    
    # Remove comment lines
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    
    # Clean up excessive whitespace
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    text = re.sub(r'^\s+', '', text, flags=re.MULTILINE)
    
    # Fix broken paragraphs - ensure <p> tags are on their own lines
    text = re.sub(r'<p>\s+', '<p>', text)
    text = re.sub(r'\s+</p>', '</p>', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text

def create_excerpt(content, max_length=160):
    """Create a clean excerpt from content"""
    # Strip HTML tags
    text = re.sub(r'<[^>]+>', '', content)
    # Decode entities
    text = html.unescape(text)
    # Clean whitespace
    text = ' '.join(text.split())
    # Truncate
    if len(text) > max_length:
        text = text[:max_length-3].rsplit(' ', 1)[0] + '...'
    return text

def format_date(date_str):
    """Format WordPress date to readable format"""
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime('%B %d, %Y')
    except:
        return date_str

def escape_json(s):
    """Escape string for JSON"""
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')

def generate_blog_html(post, image_path, all_posts):
    """Generate blog post HTML from template"""
    title = html.unescape(post['title']['rendered'])
    slug = post['slug']
    date = format_date(post['date'])
    content = clean_content(post['content']['rendered'])
    excerpt = create_excerpt(content)
    
    # Escape for meta tags
    title_escaped = html.escape(title, quote=True)
    excerpt_escaped = html.escape(excerpt, quote=True)
    title_json = escape_json(title)
    excerpt_json = escape_json(excerpt)
    
    # Default image if none
    if not image_path:
        image_path = "../images/TOP-495x400.png"
    
    # Get related posts (3 random others)
    related = [p for p in all_posts if p['slug'] != slug][:3]
    
    related_html = ""
    for rp in related:
        rp_title = html.unescape(rp['title']['rendered'])
        rp_slug = rp['slug']
        related_html += f'''
        <a href="{rp_slug}.html" class="block bg-white rounded-xl overflow-hidden shadow-sm hover:shadow-lg transition">
          <div class="p-6">
            <h3 class="font-bold mb-2 hover:text-tlh-teal">{html.escape(rp_title)}</h3>
            <span class="text-tlh-teal text-sm font-semibold">Read more →</span>
          </div>
        </a>'''
    
    template = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title_escaped} | True Legacy Homes</title>
  <meta name="description" content="{excerpt_escaped}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://iambarabbas.github.io/tlh-markdown-demo/blog/{slug}.html">
  
  <!-- Open Graph -->
  <meta property="og:type" content="article">
  <meta property="og:title" content="{title_escaped}">
  <meta property="og:description" content="{excerpt_escaped}">
  <meta property="og:image" content="{image_path}">
  <meta property="og:url" content="https://iambarabbas.github.io/tlh-markdown-demo/blog/{slug}.html">
  
  <link rel="icon" href="../images/favicon.png">
  
  <!-- Schema.org Article Markup -->
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "{title_json}",
    "description": "{excerpt_json}",
    "author": {{
      "@type": "Organization",
      "name": "True Legacy Homes"
    }},
    "publisher": {{
      "@type": "Organization",
      "name": "True Legacy Homes",
      "logo": {{
        "@type": "ImageObject",
        "url": "https://www.truelegacyhomes.com/images/tlhLOGO.png"
      }}
    }},
    "datePublished": "{post['date']}",
    "mainEntityOfPage": "https://iambarabbas.github.io/tlh-markdown-demo/blog/{slug}.html"
  }}
  </script>
  
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {{
      theme: {{
        extend: {{
          colors: {{
            'tlh-teal': '#38b5ad',
            'tlh-teal-dark': '#2d9e96',
            'tlh-dark': '#1e293b',
            'tlh-warm': '#fef3e2',
          }}
        }}
      }}
    }}
  </script>
  <style>
    .article-content h2 {{ font-size: 1.75rem; font-weight: 700; margin-top: 2rem; margin-bottom: 1rem; color: #1e293b; }}
    .article-content h3 {{ font-size: 1.5rem; font-weight: 600; margin-top: 1.5rem; margin-bottom: 0.75rem; color: #1e293b; }}
    .article-content p {{ margin-bottom: 1.25rem; line-height: 1.8; }}
    .article-content ul, .article-content ol {{ margin-bottom: 1.25rem; padding-left: 1.5rem; }}
    .article-content li {{ margin-bottom: 0.5rem; line-height: 1.7; }}
    .article-content ul {{ list-style-type: disc; }}
    .article-content ol {{ list-style-type: decimal; }}
    .article-content a {{ color: #38b5ad; text-decoration: underline; }}
    .article-content a:hover {{ color: #2d9e96; }}
    .article-content blockquote {{ border-left: 4px solid #38b5ad; padding-left: 1rem; margin: 1.5rem 0; font-style: italic; color: #64748b; }}
  </style>
</head>
<body class="bg-white text-gray-800 text-base leading-relaxed">

  <!-- Sticky Mobile CTA -->
  <div class="fixed bottom-0 left-0 right-0 bg-white border-t shadow-lg p-3 md:hidden z-40">
    <a href="tel:6194501702" class="block w-full bg-tlh-teal text-white py-3 rounded-lg font-semibold text-center">
      📞 Call (619) 450-1702
    </a>
  </div>

  <!-- Navigation -->
  <nav class="bg-white shadow-sm sticky top-0 z-50">
    <div class="max-w-6xl mx-auto px-4 py-4 flex justify-between items-center">
      <a href="../index.html">
        <img src="../images/logo-teal.png" alt="True Legacy Homes" class="h-10" style="filter: invert(62%) sepia(50%) saturate(450%) hue-rotate(130deg) brightness(95%);">
      </a>
      <div class="hidden md:flex space-x-6">
        <a href="../estate-sales.html" class="hover:text-tlh-teal">Estate Sales</a>
        <a href="../care-placement.html" class="hover:text-tlh-teal">Care Placement</a>
        <a href="../cash-offers.html" class="hover:text-tlh-teal">Cash Offers</a>
        <a href="../about.html" class="hover:text-tlh-teal">About</a>
        <a href="../blog.html" class="text-tlh-teal font-semibold">Blog</a>
        <a href="../contact.html" class="hover:text-tlh-teal">Contact</a>
      </div>
      <a href="tel:6194501702" class="hidden md:flex items-center gap-2 bg-tlh-teal text-white px-4 py-2 rounded-lg hover:bg-tlh-teal-dark">
        <span>📞</span> (619) 450-1702
      </a>
    </div>
  </nav>

  <!-- Article Header -->
  <header class="bg-gradient-to-br from-tlh-warm to-white py-12">
    <div class="max-w-4xl mx-auto px-4">
      <a href="../blog.html" class="text-tlh-teal font-semibold hover:underline mb-4 inline-block">← Back to Blog</a>
      <div class="flex items-center gap-3 mb-4">
        <span class="text-sm bg-tlh-teal text-white px-3 py-1 rounded-full">Estate Sales</span>
        <span class="text-gray-500 text-sm">{date}</span>
      </div>
      <h1 class="text-3xl md:text-4xl lg:text-5xl font-bold text-tlh-dark leading-tight">
        {html.escape(title)}
      </h1>
      <div class="flex items-center gap-3 mt-6">
        <div class="w-10 h-10 bg-tlh-teal rounded-full flex items-center justify-center text-white font-bold">T</div>
        <div>
          <p class="font-semibold text-tlh-dark">True Legacy Homes</p>
          <p class="text-sm text-gray-500">Estate Sale Experts</p>
        </div>
      </div>
    </div>
  </header>

  <!-- Featured Image -->
  <div class="max-w-4xl mx-auto px-4 -mt-4">
    <img src="{image_path}" alt="{title_escaped}" class="w-full h-64 md:h-96 object-cover rounded-xl shadow-lg">
  </div>

  <!-- Article Content -->
  <article class="max-w-4xl mx-auto px-4 py-12">
    <div class="article-content text-gray-700 text-lg">
      {content}
    </div>
  </article>

  <!-- Email Signup CTA -->
  <section class="bg-tlh-warm py-12">
    <div class="max-w-4xl mx-auto px-4 text-center">
      <h2 class="text-2xl font-bold text-tlh-dark mb-4">Get More Estate Sale Tips</h2>
      <p class="text-gray-600 mb-6">Subscribe to our weekly newsletter for expert advice on estate sales, downsizing, and senior care.</p>
      <form action="https://truelegacyhomes.us12.list-manage.com/subscribe/post?u=8fb80e36c3f769c67994988e71&amp;id=eb811b621b" method="post" class="flex flex-col sm:flex-row gap-3 justify-center max-w-md mx-auto">
        <input type="hidden" name="SOURCE" value="blog-{slug}">
        <input type="email" name="EMAIL" placeholder="Enter your email" required class="px-4 py-3 rounded-lg border border-gray-300 flex-1 focus:outline-none focus:border-tlh-teal">
        <button type="submit" class="bg-tlh-teal text-white px-6 py-3 rounded-lg font-semibold hover:bg-tlh-teal-dark whitespace-nowrap">
          Subscribe
        </button>
      </form>
    </div>
  </section>

  <!-- Related Posts -->
  <section class="py-12 bg-gray-50">
    <div class="max-w-4xl mx-auto px-4">
      <h2 class="text-2xl font-bold text-tlh-dark mb-8">Related Articles</h2>
      <div class="grid md:grid-cols-3 gap-6">
        {related_html}
      </div>
    </div>
  </section>

  <!-- Consultation CTA -->
  <section class="bg-tlh-teal text-white py-12">
    <div class="max-w-4xl mx-auto px-4 text-center">
      <h2 class="text-2xl font-bold mb-4">Need Help With Your Estate Sale?</h2>
      <p class="text-lg mb-6 opacity-90">
        Our team is here to guide you through the entire process with care and expertise.
      </p>
      <div class="flex flex-col sm:flex-row gap-4 justify-center">
        <a href="../schedule-consult.html" class="bg-white text-tlh-teal px-8 py-4 rounded-lg text-lg font-semibold hover:bg-gray-100">
          Schedule Free Consultation
        </a>
        <a href="tel:6194501702" class="border-2 border-white text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-white hover:text-tlh-teal">
          Call (619) 450-1702
        </a>
      </div>
    </div>
  </section>

  <!-- Footer -->
  <footer class="bg-tlh-dark text-gray-400 py-12 pb-24 md:pb-12">
    <div class="max-w-6xl mx-auto px-4">
      <div class="grid md:grid-cols-4 gap-8">
        <div>
          <img src="../images/tlhLOGO.png" alt="True Legacy Homes" class="h-10 mb-4 brightness-200">
          <p class="text-sm">Estate Sales with Dignity. Helping Southern California families navigate life's biggest transitions.</p>
        </div>
        <div>
          <h4 class="text-white font-bold mb-4">Services</h4>
          <ul class="space-y-2 text-sm">
            <li><a href="../estate-sales.html" class="hover:text-white">Estate Sales</a></li>
            <li><a href="../care-placement.html" class="hover:text-white">Care Placement</a></li>
            <li><a href="../cash-offers.html" class="hover:text-white">Cash Home Offers</a></li>
          </ul>
        </div>
        <div>
          <h4 class="text-white font-bold mb-4">Resources</h4>
          <ul class="space-y-2 text-sm">
            <li><a href="../blog.html" class="hover:text-white">Blog</a></li>
            <li><a href="../faq.html" class="hover:text-white">FAQ</a></li>
            <li><a href="../testimonials.html" class="hover:text-white">Testimonials</a></li>
          </ul>
        </div>
        <div>
          <h4 class="text-white font-bold mb-4">Contact</h4>
          <ul class="space-y-2 text-sm">
            <li><a href="tel:6194501702" class="hover:text-white">(619) 450-1702</a></li>
            <li><a href="mailto:info@truelegacyhomes.com" class="hover:text-white">info@truelegacyhomes.com</a></li>
            <li>3635 Ruffin Rd, Suite 100<br>San Diego, CA 92123</li>
          </ul>
        </div>
      </div>
      <div class="border-t border-gray-700 mt-8 pt-8 text-center text-sm">
        <p>© 2026 True Legacy Homes. All rights reserved.</p>
      </div>
    </div>
  </footer>

</body>
</html>'''
    return template

def main():
    print("Fetching posts from WordPress...")
    posts = fetch_posts()
    print(f"Found {len(posts)} posts in Estate Sales category")
    
    successful = []
    failed = []
    
    for i, post in enumerate(posts):
        slug = post['slug']
        title = html.unescape(post['title']['rendered'])
        print(f"[{i+1}/{len(posts)}] Processing: {slug}")
        
        try:
            # Fetch featured image
            image_path = None
            if post.get('featured_media'):
                media_url = fetch_media_url(post['featured_media'])
                if media_url:
                    image_path = download_image(media_url, slug)
            
            # Generate HTML
            html_content = generate_blog_html(post, image_path, posts)
            
            # Write file
            filepath = f"{OUTPUT_DIR}/{slug}.html"
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            successful.append({'slug': slug, 'title': title, 'date': post['date']})
            print(f"  ✓ Created: {slug}.html")
            
        except Exception as e:
            failed.append({'slug': slug, 'error': str(e)})
            print(f"  ✗ Failed: {e}")
    
    # Summary
    print("\n" + "="*50)
    print(f"TRANSFER COMPLETE")
    print(f"="*50)
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    
    if failed:
        print("\nFailed posts:")
        for f in failed:
            print(f"  - {f['slug']}: {f['error']}")
    
    # Save manifest
    manifest = {
        'total': len(posts),
        'successful': successful,
        'failed': failed
    }
    with open(f"{OUTPUT_DIR}/manifest.json", 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\nManifest saved to {OUTPUT_DIR}/manifest.json")
    
    # Sample filenames
    print("\nSample filenames created:")
    for s in successful[:5]:
        print(f"  - blog/{s['slug']}.html")
    if len(successful) > 5:
        print(f"  ... and {len(successful) - 5} more")

if __name__ == "__main__":
    main()
