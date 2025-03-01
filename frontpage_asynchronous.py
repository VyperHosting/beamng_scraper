import asyncio
import aiohttp
from bs4 import BeautifulSoup
from functools import lru_cache
import mysql.connector
import os
from dotenv import load_dotenv

# Init MySQL client
load_dotenv()
mydb = mysql.connector.connect(
    host=os.environ["DB_HOST"],
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    database="beamng"
)

mycursor = mydb.cursor()

# Async function to fetch a page
async def fetch_page(session, url):
    headers = {"User-Agent": "Mozilla/5.0"}
    async with session.get(url, headers=headers) as response:
        return await response.text()

# Use an async function for getting download links
@lru_cache(maxsize=100)
async def get_download_link_from_mod_page(url: str):
    async with aiohttp.ClientSession() as session:
        html = await fetch_page(session, url)
        soup = BeautifulSoup(html, 'html.parser')
        primary_links = soup.find_all("ul", class_="primaryLinks")

        for link in primary_links:
            download_buttons = link.find_all("label", class_="downloadButton")
            for button in download_buttons:
                download_a_tag = button.find("a", class_="inner")
                if download_a_tag:
                    link = download_a_tag["href"]
                    if "download" in link:
                        return f"https://www.beamng.com/{link}"  # Return the full URL
    return None


@lru_cache(maxsize=100)
async def extract_versions(url):
    """Extract version details from the resource history table."""

    versions = []
    async with aiohttp.ClientSession() as session:
        html = await fetch_page(session, url)
        soup = BeautifulSoup(html, 'html.parser')

        table = soup.find("table", class_="dataTable resourceHistory")
        if table:
            rows = table.find_all("tr", class_="dataRow")
            for row in rows:
                version = None
                state = None
                releaseDate = None
                downloads = None
                download_url = None

                version_tag = row.find("td", class_="version")
                if version_tag:
                    version = version_tag.get_text(strip=True)

                state_tag = row.find("td", class_="state")
                if state_tag:
                    state = state_tag.get_text(strip=True)

                releaseDate_wrapper = row.find("td", class_="releaseDate")
                if releaseDate_wrapper:
                    releaseDate_tag = releaseDate_wrapper.find("span", class_="DateTime")
                    if releaseDate_tag:
                        releaseDate = releaseDate_tag.get_text(strip=True)

                downloads_tag = row.find("td", class_="downloads")
                if downloads_tag:
                    downloads = downloads_tag.get_text(strip=True)

                download_wrapper = row.find("td", class_="dataOptions download")
                if download_wrapper:
                    download_tag = download_wrapper.find("a", class_="secondaryContent")
                    if download_tag:
                        download = download_tag["href"]
                        download_url = f"https://www.beamng.com{download}"

                mod_version = {
                    "version": version if version else "N/A",
                    "state": state if state else "N/A",
                    "release_date": releaseDate if releaseDate else "N/A",
                    "downloads": downloads if downloads else "N/A",
                    "download_url": download_url if download_url else "N/A"
                }

                versions.append(mod_version)

    return versions


# Async function for scraping the resources page
async def frontpages(query):

    ### Use AIOHTTP for concurrent HTTP Requests ###
    async with aiohttp.ClientSession() as session:
        html = await fetch_page(session, query)
        soup = BeautifulSoup(html, 'html.parser')

        posts = soup.find_all("li", class_="resourceListItem visible")

        for post in posts:
            # Get Icon and Avatar
            icons_container = post.find("div", class_="listBlockInner")
            if icons_container:

                ### Define variables ###
                icon_src = None
                avatar_src = None

                ### Get Mod Icon ###
                icon_tag = icons_container.find("a", class_="resourceIcon")
                if icon_tag:
                    icon_img_tag = icon_tag.find("img")
                    if icon_img_tag:
                        icon_src = icon_img_tag["src"]

                ### Get Mod Avatar ###
                avatar_tag = icons_container.find("a", class_="avatar Av117332s creatorMini")
                if avatar_tag:
                    avatar_img_tag = avatar_tag.find("img")
                    if avatar_img_tag:
                        avatar_src = avatar_img_tag["src"]

            ### Get Title, Mod Link, Download Link, Tags ###
            title_container = post.find("h3", class_="title")
            if title_container:
                title_tags = title_container.find_all("a")
        
                ### Get Tags ###
                prefix_text = None
                prefix_tag = next((tag for tag in title_tags if "prefixLink" in tag.get("class", [])), None)
                if prefix_tag:
                    prefix_text = prefix_tag.get_text(strip=True)

                ### Get Mod ###
                mod_page_tag = next((tag for tag in title_tags if "prefixLink" not in tag.get("class", [])), None) # FIlter past tags to get the title
                if mod_page_tag:
                    # Get title
                    title = mod_page_tag.get_text(strip=True)

                    # Get mod page link and download link
                    mod_page_link = mod_page_tag["href"]
                    if mod_page_link:
                        download_link = await get_download_link_from_mod_page(f"https://www.beamng.com/{mod_page_link}")

            ### Get mod author ###
            metadata_container = post.find("div", class_="resourceDetails muted")
            author_name = "Unknown"
            author_link = "N/A"
            if metadata_container:
                author_tag = post.find("a", href=lambda href: href and "resources/authors/" in href)
                if author_tag:
                    author_name = author_tag.get_text(strip=True)
                    author_link = f"https://www.beamng.com/{author_tag['href']}"

            ### Get mod's description ###
            description_tag = post.find("div", class_="tagLine")
            if description_tag:
                description = description_tag.get_text(strip=True)

            # Get Stats
            stats = post.find("div", class_="listBlock resourceStats")
            if stats:

                ### Get Number of Stars ###
                rating_tag = stats.find("span", class_="ratings")
                if rating_tag:
                    rating = rating_tag["title"]

                ### Get number of ratings ###
                num_of_ratings_tag = stats.find("span", class_="Hint")
                if num_of_ratings_tag:
                    number_of_ratings = num_of_ratings_tag.get_text(strip=True)

                pairs = stats.find("div", class_="pairsJustified")
                if pairs:
                    multi_tags = pairs.find_all("dl", class_="resourceDownloads")

                    ### Get the number of subscriptions and downloads on the mod ###
                    downloads = 0
                    subscriptions = 0

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

                    ### Get Last Updated ### 
                    updated_tag = pairs.find("dl", class_="resourceUpdated")
                    if updated_tag:
                        last_updated_tag = updated_tag.find("abbr", class_="DateTime")
                        if last_updated_tag:
                            last_updated_a = last_updated_tag.get_text(strip=True)
                        else:
                            last_updated_a = None
                    else:
                        last_updated_a = None

            print(f"\nTitle: {title}")
            print(f"Avatar: https://www.beamng.com/{avatar_src}")
            print(f"Icon: https://www.beamng.com/{icon_src}")
            print(f"Author: {author_name}")
            print(f"Author Link: https://www.beamng.com/{author_link}")
            print(f"Description: {description}")
            print(f"Tags: {prefix_text}")
            print(f"Mod Page Link: https://www.beamng.com/{mod_page_link}")
            print(f"Download Link: {download_link}")
            print("Stats:")
            print(f"    - Stars: {rating}")
            print(f"    - Number of Ratings: {number_of_ratings}")
            print(f"    - Number of Downloads: {downloads}")
            print(f"    - Number of Subscriptions: {subscriptions}")
            print(f"    - Last Updated: {last_updated_a}\n")

            try:
                sql = """INSERT INTO mods (`id`, `title`, `icon`, `author`, `author_link`, `description`, 
                    `tags`, `mod_link`, `download_link`, `rating`, `reviews`, `downloads`, `last_updated`) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE 
                    `title` = %s, `icon` = %s, `author` = %s, `author_link` = %s, 
                    `description` = %s, `tags` = %s, `mod_link` = %s, `download_link` = %s, 
                    `rating` = %s, `reviews` = %s, `downloads` = %s, `last_updated` = %s""".replace("\n", "")
                
                val = (
                    int(mod_page_link.split(".")[len(mod_page_link.split(".")) - 1].replace("/", "")), 

                    # Initial values
                    title, 
                    f"https://www.beamng.com/{icon_src}",
                    author_name,
                    author_link,
                    description,
                    prefix_text,
                    f"https://www.beamng.com/{mod_page_link}",
                    download_link,
                    float(rating.replace(",", "")),
                    int(number_of_ratings.replace(",", "").replace(" ratings", "").replace(" rating", "")),
                    int(downloads.replace(",", "")),
                    last_updated_a,
                    
                    # Update values
                    title, 
                    f"https://www.beamng.com/{icon_src}",
                    author_name,
                    author_link,
                    description,
                    prefix_text,
                    f"https://www.beamng.com/{mod_page_link}",
                    download_link,
                    float(rating.replace(",", "")),
                    int(number_of_ratings.replace(",", "").replace(" ratings", "").replace(" rating", "")),
                    int(downloads.replace(",", "")),
                    last_updated_a,
                )

                mycursor.execute(sql, val)
                mydb.commit()
            except:
                print("Failed to insert")

# Run the async loop
async def main():
    PAGE_NUMBER = 1

    LAST_UPDATED_PAGE = f"https://www.beamng.com/resources/?page={PAGE_NUMBER}"
    SUBMISSION_DATE_PAGE = f"https://www.beamng.com/resources/?page={PAGE_NUMBER}&order=resource_date"
    RATING_PAGE = f"https://www.beamng.com/resources/?page={PAGE_NUMBER}&order=rating_weighted"
    DOWNLOADS_PAGE = f"https://www.beamng.com/resources/?page={PAGE_NUMBER}&order=download_count"
    TITLE_PAGE = f"https://www.beamng.com/resources/?page={PAGE_NUMBER}&order=title"
    
    await frontpages(LAST_UPDATED_PAGE)

# Start scraping
results = asyncio.run(main())
