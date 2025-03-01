import requests
from bs4 import BeautifulSoup
from functools import lru_cache

# Function to fetch a page
def fetch_page(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    return response.text if response.status_code == 200 else None

# Function to get download links from the mod page
@lru_cache(maxsize=100)
def get_download_link_from_mod_page(url: str):
    html = fetch_page(url)
    if not html:
        return None
    
    soup = BeautifulSoup(html, 'html.parser')
    primary_links = soup.find_all("ul", class_="primaryLinks")

    for link in primary_links:
        download_buttons = link.find_all("label", class_="downloadButton")
        for button in download_buttons:
            download_a_tag = button.find("a", class_="inner")
            if download_a_tag:
                link = download_a_tag["href"]
                if "download" in link:
                    return f"https://www.beamng.com{link}"  # Return the full URL
    return None


@lru_cache(maxsize=100)
def extract_versions(url):
    """Extract version details from the resource history table."""

    versions = []
    html = fetch_page(url)
    if not html:
        return versions  # Return empty list if the page doesn't load

    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find("table", class_="dataTable resourceHistory")
    
    if table:
        rows = table.find_all("tr", class_="dataRow")
        for row in rows:
            version_tag = row.find("td", class_="version")
            state_tag = row.find("td", class_="state")
            releaseDate_wrapper = row.find("td", class_="releaseDate")
            downloads_tag = row.find("td", class_="downloads")
            download_wrapper = row.find("td", class_="dataOptions download")

            download_url = None
            if download_wrapper:
                download_tag = download_wrapper.find("a", class_="secondaryContent")
                if download_tag:
                    download_url = f"https://www.beamng.com/{download_tag['href']}"

            mod_version = {
                "version": version_tag.get_text(strip=True) if version_tag else "N/A",
                "state": state_tag.get_text(strip=True) if state_tag else "N/A",
                "release_date": releaseDate_wrapper.find("span", class_="DateTime").get_text(strip=True)
                if releaseDate_wrapper and releaseDate_wrapper.find("span", class_="DateTime") else "N/A",
                "downloads": downloads_tag.get_text(strip=True) if downloads_tag else "N/A",
                "download_url": download_url if download_url else "N/A"
            }

            versions.append(mod_version)

    return versions


# Function for scraping the resources page
def frontpages(query):
    results = []
    html = fetch_page(query)
    if not html:
        return results  # Return empty list if the page doesn't load

    soup = BeautifulSoup(html, 'html.parser')
    posts = soup.find_all("li", class_="resourceListItem visible")

    for post in posts:
        # Get Icon and Avatar
        icons_container = post.find("div", class_="listBlockInner")
        icon_src, avatar_src = None, None

        if icons_container:
            icon_tag = icons_container.find("a", class_="resourceIcon")
            if icon_tag:
                icon_img_tag = icon_tag.find("img")
                if icon_img_tag:
                    icon_src = icon_img_tag["src"]

            avatar_tag = icons_container.find("a", class_="avatar Av117332s creatorMini")
            if avatar_tag:
                avatar_img_tag = avatar_tag.find("img")
                if avatar_img_tag:
                    avatar_src = avatar_img_tag["src"]

        # Get Title, Mod Link, Download Link, Tags
        title_container = post.find("h3", class_="title")
        title, mod_page_link, download_link, prefix_text = None, None, None, None

        if title_container:
            title_tags = title_container.find_all("a")

            prefix_tag = next((tag for tag in title_tags if "prefixLink" in tag.get("class", [])), None)
            if prefix_tag:
                prefix_text = prefix_tag.get_text(strip=True)

            mod_page_tag = next((tag for tag in title_tags if "prefixLink" not in tag.get("class", [])), None)
            if mod_page_tag:
                title = mod_page_tag.get_text(strip=True)
                mod_page_link = mod_page_tag["href"]
                if mod_page_link:
                    download_link = get_download_link_from_mod_page(f"https://www.beamng.com/{mod_page_link}")

        # Get mod author
        author_name, author_link = None, None
        metadata_container = post.find("div", class_="resourceDetails muted")
        if metadata_container:
            author_tag = soup.find("a", href=lambda href: href and "resources/authors/" in href)
            if author_tag:
                author_name = author_tag.get_text(strip=True)
                author_link = author_tag["href"]

        # Get mod's description
        description = None
        description_tag = post.find("div", class_="tagLine")
        if description_tag:
            description = description_tag.get_text(strip=True)

        # Get Stats
        stats = post.find("div", class_="listBlock resourceStats")
        rating, number_of_ratings, downloads, subscriptions, last_updated_a = None, None, 0, 0, None

        if stats:
            rating_tag = stats.find("span", class_="ratings")
            if rating_tag:
                rating = rating_tag["title"]

            num_of_ratings_tag = stats.find("span", class_="Hint")
            if num_of_ratings_tag:
                number_of_ratings = num_of_ratings_tag.get_text(strip=True)

            pairs = stats.find("div", class_="pairsJustified")
            if pairs:
                multi_tags = pairs.find_all("dl", class_="resourceDownloads")
                for section in multi_tags:
                    dt_tag = section.find("dt")
                    dd_tag = section.find("dd")
                    if dt_tag and dd_tag:
                        label = dt_tag.get_text(strip=True)
                        value = dd_tag.get_text(strip=True)
                        if label == "Downloads:":
                            downloads = value
                        elif label == "Subscriptions":
                            subscriptions = value

                updated_tag = pairs.find("dl", class_="resourceUpdated")
                if updated_tag:
                    last_updated_tag = updated_tag.find("abbr", class_="DateTime")
                    if last_updated_tag:
                        last_updated_a = last_updated_tag.get_text(strip=True)

        scrapables = {
            "title": title,
            "avatar": f"https://www.beamng.com/{avatar_src}" if avatar_src else None,
            "icon": f"https://www.beamng.com/{icon_src}" if icon_src else None,
            "author": author_name,
            "author_link": f"https://www.beamng.com/{author_link}" if author_link else None,
            "description": description,
            "tags": prefix_text,
            "mod_link": f"https://www.beamng.com/{mod_page_link}" if mod_page_link else None,
            "download_link": download_link,
            "stars": rating,
            "ratings": number_of_ratings,
            "downloads": downloads,
            "subscriptions": subscriptions,
            "last_updated": last_updated_a,
            "version_downloads": extract_versions(f"https://www.beamng.com/{mod_page_link}/historyImproved") if mod_page_link else []
        }

        results.append(scrapables)

        print(f"\nTitle: {title}")
        print(f"Avatar: https://www.beamng.com/{avatar_src}" if avatar_src else "Avatar: N/A")
        print(f"Icon: https://www.beamng.com/{icon_src}" if icon_src else "Icon: N/A")
        print(f"Author: {author_name}" if author_name else "Author: N/A")
        print(f"Author Link: https://www.beamng.com/{author_link}" if author_link else "Author Link: N/A")
        print(f"Description: {description}" if description else "Description: N/A")
        print(f"Tags: {prefix_text}" if prefix_text else "Tags: N/A")
        print(f"Mod Page Link: https://www.beamng.com/{mod_page_link}" if mod_page_link else "Mod Page Link: N/A")
        print(f"Download Link: {download_link}" if download_link else "Download Link: N/A")
        print(f"Stars: {rating}" if rating else "Stars: N/A")
        print(f"Number of Ratings: {number_of_ratings}" if number_of_ratings else "Number of Ratings: N/A")
        print(f"Number of Downloads: {downloads}" if downloads else "Number of Downloads: N/A")
        print(f"Number of Subscriptions: {subscriptions}" if subscriptions else "Number of Subscriptions: N/A")
        print(f"Last Updated: {last_updated_a}" if last_updated_a else "Last Updated: N/A")

        print("Version Downloads:")
        version_data = extract_versions(f"https://www.beamng.com/{mod_page_link}/historyImproved") if mod_page_link else []
        for version in version_data:
            print(f"    - Version: {version['version']}")
            print(f"      State: {version['state']}")
            print(f"      Release Date: {version['release_date']}")
            print(f"      Downloads: {version['downloads']}")
            print(f"      Download URL: {version['download_url']}")


    return results


# Main function to start scraping
def main():
    PAGE_NUMBER = 1
    RATING_PAGE = f"https://www.beamng.com/resources/?page={PAGE_NUMBER}&order=rating_weighted"
    results = frontpages(RATING_PAGE)
    return results

# Run the scraper
results = main()
for result in results:
    print(f"\nTitle: {result['title']}")
    print(f"Avatar: {result['avatar']}")
    print(f"Icon: {result['icon']}")
    print(f"Author: {result['author']}")
    print(f"Author Link: {result['author_link']}")
    print(f"Description: {result['description']}")
    print(f"Tags: {result['tags']}")
    print(f"Mod Page Link: {result['mod_link']}")
    print(f"Download Link: {result['download_link']}")
    print(f"Stars: {result['stars']}")
    print(f"Number of Ratings: {result['ratings']}")
    print(f"Number of Downloads: {result['downloads']}")
    print(f"Number of Subscriptions: {result['subscriptions']}")
    print(f"Last Updated: {result['last_updated']}")
    
    print("Version Downloads:")
    for version in result["version_downloads"]:
        print(f"    - Version: {version['version']}")
        print(f"      State: {version['state']}")
        print(f"      Release Date: {version['release_date']}")
        print(f"      Downloads: {version['downloads']}")
        print(f"      Download URL: {version['download_url']}")
