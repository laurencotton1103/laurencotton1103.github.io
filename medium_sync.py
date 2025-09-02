#pathlib makes the file/folder handling easier
#datetime handles the article dates
#re (regex) is for cleaning up titles into filenames (slugs)
import os, re, sys, pathlib, datetime, json
from urllib.parse import urlparse
#requests library fetches the feed from medium
import requests
#parses RSS feeds into structured data
import feedparser
#html cleanup tools
from bs4 import BeautifulSoup

#Create an articles folder that will store the posts
ARTICLES_DIR = pathlib.Path("articles")
ARTICLES_DIR.mkdir(exist_ok=True)

#Pulls the medium feed URL
FEED_URL = "https://medium.com/feed/@laurencotton"
if not FEED_URL:
  print("ERROR: FEED_URL not set")
  sys.exit(1)

#Helper function - converts "My Great Post!" to "my-great-post"
#this will help us to save articles to a folder 
def slugify(title: str) -> str:
  s = title.lower()
  s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
  return s[:80] or "post"

#Define function that will convert txt files to html files
def write_article_file(date, slug, title, content_html, canonical_url):
  filename = f"{date.isoformat()}-{slug}.html"
  html_path = ARTICLES_DIR / filename
  with open(html_path, "w", encoding="utf-8") as f: 
    f.write("<!DOCTYPE html>\n<html><head>\n")
    f.write("<meta charset='utf-8'>\n")
    f.write(f"<title>{title}</title>\n")
    f.write("</head><body>\n")
    # Title
    f.write(f"<h1>{title}</h1>\n")

    # Link back to the original Medium article
    f.write(f"<p><a href='{canonical_url}'>View on Medium</a></p>\n")

    # Full Medium content (keeps original HTML formatting)
    f.write(f"<div>{content_html}</div>\n")

    f.write("</body></html>")

  print(f"Saved: {html_path.name}")

#parse through the medium feed entries to isolate the fields: Title, Subtitle, and Content
def parse_medium_feed(FEED_URL: str):
  feed = feedparser.parse(FEED_URL)

  for entry in feed.entries:
    Title = entry.get("title", "No title")
    raw_content = entry.content[0].value if "content" in entry else entry.get("summary", "")
    content_html = raw_content
    date = datetime.date(*entry.published_parsed[:3])
    canonical_url = entry.get("link", "")

    #generate a safe filename using helper function, file auto-overwrites with new version
    slug = slugify(Title)
    filename = f"{slug}.html"
    path = ARTICLES_DIR / filename

    write_article_file(date, slug, Title, content_html, canonical_url)

parse_medium_feed(FEED_URL)
    
def build_index():
  index_path = ARTICLES_DIR / "index.html"

  with open(index_path, "w", encoding="utf-8") as f: 
    #Start HTML
    f.write("<html><head><meta charset='utf-8'><title>My Medium Articles</title></head><body>")
    f.write("<h1>My Medium Articles</h1>\n<ul>\n")

    #Loop through all HTML article files
    for path in sorted(ARTICLES_DIR.glob("*.html")):
      if path.name =="index.html":
        continue #skip the index itself
      #Extract the <h1> title from the html
      with open(path, "r", encoding="utf-8") as article_file:
        soup = BeautifulSoup(article_file, "html.parser")
        title_tag = soup.find("h1")
        title_text = title_tag.get_text(strip=True) if title_tag else path.stem
      #Write link to index
      f.write(f"<li><a href='{path.name}'>{title_text}</a></li>\n")
    f.write("</ul>\n</body></html>")
  print(f"Index page created: {index_path}")

build_index()

