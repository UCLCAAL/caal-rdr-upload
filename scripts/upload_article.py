"""
Upload one CAAL article from RDSS to UCL RDR as a draft (#14).

Steps:
    1. Read the archive CSV.
    2. Find an article folder on RDSS that has a row in the CSV (the first one
       by default, or the one at the index given on the command line).
    3. Create a draft article on Figshare with the title and description.
    4. Upload the folder's PDF and TIF files.
    5. Fetch the article and print what is on Figshare.

The article is only created as a draft; this script never publishes it.
Every run creates a new draft, so delete test drafts you no longer need on RDR.

How to run
----------
Make sure you are connected to the UCL VPN. And have the CAAL RDSS mounted on your
R drive.

1. Create an RDR FIGSHARE token:
   - https://rdr.ucl.ac.uk/account/integrations
   Never commit the token or share it; anyone with it can upload to your account.

2. Connect to the UCL VPN and make sure RDSS is mounted (e.g. as R:). If RDSS
   or the CSV are somewhere else, change RDSS_PATH and CSV_PATH under "Settings" below.

3. Paste your token into the .env file in the repository root (create it if
   it is missing; it is git-ignored, so it is never committed):

       RDR_FIGSHARE_TOKEN=<your token>

4. Run the script:

       python scripts/upload_article.py      # first article (index 0)
       python scripts/upload_article.py 3    # fourth article (index 3)
"""

import csv
import os
import re
import sys
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()  # reads RDR_FIGSHARE_TOKEN from the .env file into the environment

# --- Settings ----------------------------------------------------------------
# Change the paths if RDSS or the CSV are somewhere else. The token is read
# from the .env file (see "How to run" above), so it is never in the code.
RDSS_PATH = Path("R:/KG")  # RDSS folder to search for article folders
CSV_PATH = Path("data/caal_archive_en.csv")  # Marco's archive CSV
TOKEN = os.environ["RDR_FIGSHARE_TOKEN"]  # Figshare personal token
MAX_FILES = None  # how many files to upload per article; None = all of them

FIGSHARE_API = "https://api.figshare.com/v2"


def figshare(method: str, url: str, **kwargs: Any) -> Any:  # noqa: ANN401
    """Send a request to the Figshare API and return the JSON response."""
    # Most calls pass a path like "/account/articles". File uploads go to a different
    # server, so Figshare gives us a full URL for those; use it unchanged.
    if not url.startswith("http"):
        url = FIGSHARE_API + url
    headers = {"Authorization": f"token {TOKEN}"}
    response = requests.request(method, url, headers=headers, timeout=300, **kwargs)
    response.raise_for_status()
    if "json" in response.headers.get("content-type", ""):
        return response.json()
    return None


def upload_file(article_id: int, path: Path) -> None:
    """Upload one file: register it, send it in parts, then mark it complete."""
    files_url = f"/account/articles/{article_id}/files"
    body = {"name": path.name, "size": path.stat().st_size}
    location = figshare("POST", files_url, json=body)
    file_info = figshare("GET", location["location"])
    upload_url = file_info["upload_url"]

    with path.open("rb") as fh:
        for part in figshare("GET", upload_url)["parts"]:
            fh.seek(part["startOffset"])
            data = fh.read(part["endOffset"] - part["startOffset"] + 1)
            figshare("PUT", f"{upload_url}/{part['partNo']}", data=data)

    figshare("POST", f"{files_url}/{file_info['id']}")


def find_article_folder(
    rdss_path: Path, rows_by_folder_name: dict, index: int = 0
) -> Path:
    """
    Return an article folder (named like ..._000031) that has a CSV row.

    Matching folders are counted in name order: index 0 is the first one,
    index 1 the second, and so on.
    """
    count = 0
    for dirpath, dirnames, _ in os.walk(rdss_path):
        # Sorting dirnames in place makes os.walk visit folders in name order,
        # so the same index always gives the same folder.
        dirnames.sort()
        folder = Path(dirpath)
        if re.search(r"_\d{6}$", folder.name) and folder.name in rows_by_folder_name:
            if count == index:
                return folder
            count += 1
    sys.exit(f"Only {count} article folders with a CSV row found in {rdss_path}")


def main() -> None:
    """Upload the first CAAL article as a draft."""
    index = int(sys.argv[1]) if len(sys.argv) > 1 else 0  # which article; 0 = first
    max_files = 1
    # 1. Read the CSV. "Digital Folder Name" is the folder's path on RDSS, e.g.
    #    KG/KG_AS/KG_AS_IHDSS/KG_AS_IHDSS-AB/KG_AS_IHDSS-AB_000031, so each row
    #    is stored under the last part of that path. (The "Caal id" column,
    #    e.g. Ar_KG_AS-000102, does not appear in folder names.)
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as fh:
        rows_by_folder_name = {
            row["Digital Folder Name"].strip().split("/")[-1]: row
            for row in csv.DictReader(fh)
        }

    # 2. Find the article folder and its files.
    folder = find_article_folder(RDSS_PATH, rows_by_folder_name, index)
    row = rows_by_folder_name[folder.name]
    files = sorted(
        path
        for path in folder.iterdir()
        if path.suffix.lower() in {".pdf", ".tif", ".tiff"}
    )
    print(f"Folder:  {folder}")
    print(f"CAAL id: {row['Caal id']}")
    print(f"Files:   {len(files)} in folder, uploading {len(files[:max_files])}")
    files = files[:max_files]  # files[:None] keeps them all

    # 3. Create the draft article.
    metadata = {"title": row["English Title"], "description": row["Description"]}
    created = figshare("POST", "/account/articles", json=metadata)
    article_id = int(created["location"].split("/")[-1])
    print(f"Created draft article {article_id}")

    # 4. Upload the files.
    for path in files:
        print(f"Uploading {path.name}")
        upload_file(article_id, path)

    # 5. Fetch the article and show what was uploaded.
    article = figshare("GET", f"/account/articles/{article_id}")
    print(f"\nArticle ID: {article_id}")
    print(f"Title:      {article['title']}")
    print(f"Status:     {article['status']}")
    print(f"Files:      {len(article['files'])} on Figshare, {len(files)} expected")
    print(f"URL:        {article['url_private_html']}")


if __name__ == "__main__":
    main()
