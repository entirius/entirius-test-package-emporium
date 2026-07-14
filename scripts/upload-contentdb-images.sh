#!/bin/bash
#
# upload-contentdb-images.sh — Upload placeholder images to ContentDB gallery
# and patch Content records with proper images_set structure.
#
# Runs INSIDE the volkanos container after fixtures are loaded.
# Uses Django ORM directly (no API auth needed).
#
# Usage: ./upload-contentdb-images.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMAGES_DIR="${SCRIPT_DIR}/../images"

echo "ContentDB Image Upload"
echo "======================"

# Check local images exist
if [ ! -d "$IMAGES_DIR" ] || [ -z "$(ls "$IMAGES_DIR"/*.png 2>/dev/null)" ]; then
    echo "WARNING: No images found in ${IMAGES_DIR}/"
    echo "Skipping image upload."
    exit 0
fi

# Everything via Django ORM — no API auth needed
python3 - "$IMAGES_DIR" << 'PYTHON_SCRIPT'
import sys, os, copy

images_dir = sys.argv[1]

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')
import django
django.setup()

from django.core.files.base import ContentFile
from django_contentdb.models import Content, Image


def save_image(filepath, alt_text):
    """Create an Image record directly via Django ORM."""
    filename = os.path.basename(filepath)

    with open(filepath, 'rb') as f:
        file_data = f.read()

    img = Image(meta={'alt': alt_text, 'fileName': filename})
    img.image.save(filename, ContentFile(file_data), save=True)
    return img


def build_image_ref(img):
    """Build images_set entry from an Image instance."""
    image_url = img.image.url if img.image else ''
    thumb_set = []
    for thumb in img.thumbnails.all():
        thumb_set.append({
            'width': thumb.width,
            'height': thumb.height,
            'source': thumb.image.url if thumb.image else '',
        })
    if not thumb_set:
        thumb_set.append({
            'width': img.width,
            'height': img.height,
            'source': image_url,
        })

    return {
        'uid': str(img.uid),
        'image': image_url,
        'width': img.width,
        'height': img.height,
        'meta': img.meta,
        'tags': [],
        'set': thumb_set,
        'created_at': img.created_at.isoformat() if img.created_at else None,
        'updated_at': img.updated_at.isoformat() if img.updated_at else None,
    }


# Upload placeholder images
image_files = {
    'hero-desktop': 'Entirius hero desktop placeholder',
    'hero-mobile': 'Entirius hero mobile placeholder',
    'blog-cover': 'Entirius blog cover placeholder',
    'content-800x600': 'Entirius content placeholder',
}

print('')
print(f'Uploading images from {images_dir}/...')
uploaded = {}
for name, alt in image_files.items():
    filepath = os.path.join(images_dir, f'{name}.png')
    if not os.path.exists(filepath):
        print(f'  Skipping {name}.png (not found)')
        continue

    try:
        img = save_image(filepath, alt)
        ref = build_image_ref(img)
        uploaded[name] = ref
        print(f'  Uploaded: {name}.png -> uid={img.uid}')
    except Exception as e:
        print(f'  Failed: {name}.png ({e})')

if not uploaded:
    print('No images uploaded successfully. Skipping content patching.')
    sys.exit(0)

hero_desktop = uploaded.get('hero-desktop')
hero_mobile = uploaded.get('hero-mobile')
blog_cover = uploaded.get('blog-cover')
content_img = uploaded.get('content-800x600')

# Patch Content records
print('')
print('Patching content records...')
patched = 0

for record in Content.objects.all():
    data = record.content
    changed = False

    # Patch tiles with images_set
    if data and 'tiles' in data:
        for tile_uid, tile_data in data['tiles'].items():
            core_type = tile_data.get('core_type', '')

            if core_type == 'tile-hero' and hero_desktop:
                images_set = {'desktop': hero_desktop}
                if hero_mobile:
                    images_set['mobile'] = hero_mobile
                tile_data['images_set'] = images_set
                changed = True

            elif core_type in ('tile-image', 'tile-img-btn') and content_img:
                tile_data['images_set'] = {
                    'desktop': content_img,
                    'mobile': content_img,
                }
                changed = True

    # Patch blog extension images_set
    ext = record.extension
    if ext and isinstance(ext, dict) and 'images_set' in ext and blog_cover:
        record.extension['images_set'] = {
            'desktop': blog_cover,
            'mobile': blog_cover,
        }
        changed = True

    if changed:
        record.content = copy.deepcopy(data)
        record.save(update_fields=['content', 'extension'])
        patched += 1
        print(f'  Patched Content pk={record.pk}')

print(f'  Total: {patched} content records patched')

# Generate thumbnails for uploaded images
print('')
print('Generating thumbnails...')
from django_contentdb.tasks import optimize_image as _optimize
for name, ref in uploaded.items():
    try:
        img_obj = Image.objects.get(uid=ref['uid'])
        _optimize(img_obj.pk)
        print(f'  Optimized: {name}')
    except Exception as e:
        print(f'  Failed to optimize {name}: {e}')

print('')
print('Image upload complete.')
PYTHON_SCRIPT
