# Cloudflare R2 Setup for Blog Images

## Overview
Blog images are hosted on Cloudflare R2 to keep the main site under the 25MB Pages limit.

- **Pages**: HTML, CSS, site assets (~10MB)
- **R2**: Blog featured images (~30MB, 87 images)

## Setup Steps

### 1. Create R2 Bucket
1. Go to Cloudflare Dashboard → R2
2. Create bucket: `tlh-blog-images`
3. Enable public access (Settings → Public Access → Allow)

### 2. Set Up Custom Domain (Optional but recommended)
1. In bucket settings → Custom Domains
2. Add: `images.truelegacyhomes.com`
3. Cloudflare will auto-configure DNS

Or use the default R2.dev URL: `https://pub-xxxxx.r2.dev`

### 3. Install Wrangler CLI
```bash
npm install -g wrangler
wrangler login
```

### 4. Upload Existing Images
```bash
cd tlh-rebuild/blog/images
for img in *.jpg; do
  wrangler r2 object put tlh-blog-images/"$img" --file="$img"
done
```

### 5. Update Blog HTML
Replace image paths in blog posts:
- FROM: `images/article-name.jpg`
- TO: `https://images.truelegacyhomes.com/article-name.jpg`

### 6. For New Articles
Use the upload script:
```bash
./scripts/upload-blog-image.sh ~/Desktop/new-article-hero.png new-article-name
```

## Cost Estimate
- Storage: ~30MB = ~$0.0045/month
- Requests: Free egress (no bandwidth charges!)
- Total: Essentially free

## Script Config
Update `scripts/upload-blog-image.sh` with your:
- R2_ACCOUNT_ID (from Cloudflare dashboard)
- R2_PUBLIC_URL (your custom domain or R2.dev URL)
