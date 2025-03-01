import requests
from bs4 import BeautifulSoup
from functools import lru_cache
from urllib.parse import urlparse, urlunparse, parse_qs
import json

# Function to fetch a page synchronously
def fetch_page(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        print(f"[STEP] Fetching page: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        html = response.text
        print(f"[SUCCESS] Fetched page: {url}")
        return html
    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch page {url}: {e}")
        return ""

# Function to get metadata from a mod page
@lru_cache(maxsize=100)
def get_metadata_from_mod_page(url: str):
    print(f"[STEP] Fetching metadata from mod page: {url}")
    html = fetch_page(url)
    if not html:
        print(f"[ERROR] Skipping metadata fetch for {url} due to failed page fetch.")
        return "N/A", "N/A", "N/A", "N/A", "N/A"  # Return default values if page fetch failed

    soup = BeautifulSoup(html, 'html.parser')
    print(f"[SUCCESS] Parsed HTML for metadata on: {url}")

    # Initialize default values
    number_of_downloads = "N/A"
    rating = "N/A"
    number_of_ratings = "N/A"
    last_update = "N/A"

    secondary_content = soup.find("div", class_="secondaryContent")
    if secondary_content:
        print("[STEP] Extracting download count, rating, and last update information.")
        
        download_count = secondary_content.find("dl", class_="downloadCount")
        if download_count:
            number_of_downloads = download_count.find("dd").get_text(strip=True)

        ratings_tag = secondary_content.find("span", class_="ratings")
        if ratings_tag:
            rating = ratings_tag["title"]

        number_of_ratings_tag = secondary_content.find("span", class_="Hint")
        if number_of_ratings_tag:
            number_of_ratings = number_of_ratings_tag.get_text(strip=True)

        update_tag = secondary_content.find("abbr", class_="DateTime")
        if update_tag:
            last_update = update_tag.get_text(strip=True)

        print(f"[SUCCESS] Extracted metadata: {number_of_downloads} downloads, {rating} rating, {number_of_ratings} ratings, last updated on {last_update}")
    else:
        print("[ERROR] No secondary content found on mod page.")

    primary_links = soup.find_all("ul", class_="primaryLinks")
    download_link = None

    for link in primary_links:
        download_buttons = link.find_all("label", class_="downloadButton")
        for button in download_buttons:
            download_a_tag = button.find("a", class_="inner")
            if download_a_tag:
                link = download_a_tag["href"]
                if "download" in link:
                    download_link = f"https://www.beamng.com{link}"
                    print(f"[SUCCESS] Found download link: {download_link}")
                    break

    return download_link, number_of_downloads, rating, number_of_ratings, last_update

# Function to search for mods synchronously
def search(query: str, page_number: int):
    print(f"[STEP] Starting search for '{query}' on page {page_number}")
    search_url = f"https://www.beamng.com/search/679513590/?page={page_number}?q={query}&t=resource_update&o=date&c[title_only]=1"

    results = []

    html = fetch_page(search_url)
    if not html:
        print(f"[ERROR] Failed to fetch search results for '{query}' on page {page_number}")
        return results

    print(f"[SUCCESS] Fetched search results for '{query}' on page {page_number}")
    soup = BeautifulSoup(html, 'html.parser')

    posts = soup.find_all("li", class_="searchResult resourceUpdate primaryContent")
    print(f"[STEP] Found {len(posts)} posts in search results.")

    for post in posts:
        icon_src = mod_link = download_link = title = version = description = author = "N/A"
        print(f"[STEP] Processing post...")

        # Get Icon
        icon_tag = post.find("a", class_="avatar Av499407s")
        if icon_tag:
            icon_a_tag = icon_tag.find("img")
            if icon_a_tag:
                icon_src = icon_a_tag.get("src")
                print(f"[SUCCESS] Found icon: {icon_src}")

        # Get content type
        content_type_tag = post.find("span", class_="contentType")
        content_type = content_type_tag.get_text(strip=True) if content_type_tag else ""
        print(f"[SUCCESS] Content type: {content_type}")

        # Get title, version, mod link, and prefix (if available)
        post_header_tag = post.find("h3", class_="title")
        if post_header_tag:
            title_tag = post_header_tag.find("a")
            version_tag = post_header_tag.find("span", class_="muted")
            prefix_tag = post_header_tag.find("span", class_="prefix")

            # Default values
            title = version = mod_link = prefix = "N/A"

            if title_tag:
                title = title_tag.get_text(strip=True)
                print(f"[SUCCESS] Found title: {title}")

                mod_link_href = title_tag["href"]
                mod_link = f"https://www.beamng.com/{mod_link_href}"

                # Check if the URL contains an update query parameter
                parsed_url = urlparse(mod_link)
                query_params = parse_qs(parsed_url.query)

                if 'update' in query_params:
                    # If there is an 'update' query, remove it
                    parsed_url = parsed_url._replace(query='')  # Remove all query parameters
                    mod_link = urlunparse(parsed_url)
                    print(f"[SUCCESS] Found mod link (update removed): {mod_link}")
                else:
                    print(f"[SUCCESS] Found mod link: {mod_link}")


            if version_tag:
                version = version_tag.get_text(strip=True)
                print(f"[SUCCESS] Found version: {version}")

            if prefix_tag:
                prefix = prefix_tag.get_text(strip=True)
                print(f"[SUCCESS] Found prefix: {prefix}")

        # Get description
        description_tag = post.find("blockquote", class_="snippet")
        if description_tag:
            atag = description_tag.find("a")
            if atag:
                description = atag.get_text(strip=True)
                print(f"[SUCCESS] Found description: {description}")

        # Get author
        author = post["data-author"]
        print(f"[SUCCESS] Found author: {author}")

        # Fetch metadata if mod link is valid
        if mod_link != "N/A":
            print(f"[STEP] Fetching metadata for mod link: {mod_link}")
            metadata = get_metadata_from_mod_page(mod_link)
            download_link, number_of_downloads, rating, number_of_ratings, last_update = metadata
        else:
            print(f"[ERROR] Skipping mod {title} because the link is invalid: {mod_link}")
            download_link, number_of_downloads, rating, number_of_ratings, last_update = ["N/A"] * 5

        # Store mod info
        mod_info = {
            "title": title,
            "tags": prefix,
            "content": content_type,
            "version": version,
            "author": author,
            "description": description,
            "mod_icon": icon_src,
            "mod_link": mod_link,
            "download_link": download_link,
            "number_of_downloads": number_of_downloads,
            "rating": rating,
            "number_of_ratings": number_of_ratings,
            "last_updated": last_update
        }

        results.append(mod_info)
        print(f"[SUCCESS] Stored mod info for: {title}")

    print(f"[SUCCESS] Search completed for '{query}' on page {page_number}")
    return results

# Main function to run the synchronous scraping
def main():
    query = "mod"
    page_number = 1
    results = search(query, page_number)
    return results

# Start scraping and output the results in JSON format
results = main()

# Print the JSON result
print(f"[RESULTS] Final results: {json.dumps(results, indent=4)}")
