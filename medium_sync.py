#pathlib makes the file/folder handling easier
#datetime handles the article dates
#re (regex) is for cleaning up titles into filenames (slugs)
import os, re, sys, pathlib, datetime, json
from urllib.parse import urlparse
#requests library fetches the feed from medium
import requests
#parses RSS feeds into structured data
import feedparser

#Create an articles folder that will store the posts
ARTICLES_DIR = pathlib.Path("articles")
ARTICLES_DIR.mkdir(exist_ok=True)

#Pulls the medium feed URL from an environment variable (set in the Action)
FEED_URL = os.environ.get("MEDIUM_FEED_URL")
if not FEED_URL:
  print("ERROR: MEDIUM_FEED_URL not set")
  sys.exit(1)

#Helper function - converts "My Great Post!" to "my-great-post"
def slugify(title: str) -> str:
  s = title.lower()
  s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
  return s[:80] or "post"

#helper function - figures out the publication date (published -> updated -> today as fallback)
def parse_date(entry):
  #prefer published, then updated; fall back to today
  for key in ("published_parsed", "updated_parsed"):
    if getattr(entry, key, None):
      t = getattr(entry, key)
      return datetime.date(t.tm_year, t.tm_mon, t.tm_mday)
  return datetime.date.today()

#
def get_content_html(entry):
  #Prefer content:encoded, then summary
  if "content" in entry and entry.content:
    return entry.content[0].value
  return entry.get("summary", "")

def write_article_file(date, slug, title, canonical_url, content_html):
  filename: f"{date.isoformat()}-{slug}.html"
  path = ARTICLES_DIR / filename
  if path.exists():
      return None #if already imported
    
  html = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="canonical" href="{canonical_url}" />
  <style>
    body {{ max-width: 760px; margin: 2rem auto; padding: 0 1rem; font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; line-height: 1.6; }}
    header, footer {{ color: #666; font-size: 0.9rem; }}
    img {{ max-width: 100%; height: auto; }}
    pre {{ overflow: auto; }}
    a {{ text-decoration: none; }}
  </style>
</head>
<body>
  <header>
    <p><a href="/index.html">Home</a> · <a href="/articles/index.html">Articles</a></p>
  </header>
  <article>
    <h1>{title}</h1>
    <p><em>Mirrored from <a href="{canonical_url}" target="_blank" rel="noopener">Medium</a>. Published {date.isoformat()}.</em></p>
    {content_html}
  </article>
  <footer>
    <p>© {datetime.date.today().year} · Canonical version on Medium: <a href="{canonical_url}">{canonical_url}</a></p>
  </footer>
</body>
</html>
"""

    path.write_text(html, encoding="utf-8")
    return path.name

def build_index():
  #Build/refresh a simple index for page for /articles/
  files = sorted(ARTICLES_DIR).glob("*.html"), reverse=True)
  items = []
  for f in files: 
    #extract title from the file's <title> tag
    try: 
      text = f.read_text(encoding="utf-8", errors="ignore")
      m = re.search(r"<title>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
      title = m.group(1).strip() if m else f.name
    except Exception:
      title = f.name
    items.append((f.name, title))

  index_html = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Articles</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body { max-width: 760px; margin: 2rem auto; padding: 0 1rem; font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; line-height: 1.6; }
    h1 { margin-bottom: 1rem; }
    li { margin: 0.5rem 0; }
  </style>
</head>
<body>
  <p><a href="/index.html">← Back to Home</a></p>
  <h1>Articles</h1>
  <ul>
    {}
  </ul>
</body>
</html>""".format(
        "\n    ".join(f'<li><a href="/articles/{name}">{title}</a></li>' for name, title in items)
    )
    (ARTICLES_DIR / "index.html").write_text(index_html, encoding="utf-8")

#Fetch feed (use custom UA to avoid 403s)
headers = {"User-Agent": "GithubActions-MediumSync/1.0 (https://github.com)"}
resp = requests.get(FEED_URL, headers=headers, timeout=30)
resp.raise_for_status()
feed = feedparser.parse(resp.content)

added = []
for entry in feed.entries:
  title = entry.get("title", "Untitled")
  link = entry.get("link", "")
  date = parse_date(entry)
  content_html = get_content_html(entry)
  slug = slugify(title)
  created = write_article_file(date, slug, title, content_html)
  if created: 
    added.append(created)

build_index()

print(f"Imported {len(added)} new article(s).")
if added:
  print("New files:\n" + "\n".join(f"-articles/{x}" for x in added))
