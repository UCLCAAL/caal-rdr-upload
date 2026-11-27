"""
Upload selected CAAL articles from RDSS to UCL RDR as a draft (#14).

Steps:
    1. Read the archive CSV.
    2. Find an article folder on RDSS that has a row in the CSV (the first one
       by default, or the one at the index given on the command line).
       Use the bulk_upload flag to select more than one to upload.
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

import argparse
import csv
import os
import sys
import time
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

TITLE_FIELDS = ["English Title", "Original Title", "Caal id"]
DESCRIPTION_FIELDS = [
    "Copyright Holder Name",
    "Number and Type of Original Material",
    "Size and Dimensions of Original Material",
    "Dates of Original Material",
    "Author of the Original Material",
]


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


def find_article_folders(
    rdss_path: Path, records: dict, index: int = 0, num_articles: int = 1
) -> list[Path]:
    """
    Return article folders that have a CSV row, in name order, from index on.

    NOTE: We are using the record_keys (that should (?) match to record folder names),
    rather than the "Digital Folder Name" column in the archive CSV, because there are
    over 3,000 mismatches due to issues with the paths listed in the CSV (see #26).
    """
    folders = []
    for dirpath, dirnames, _ in os.walk(rdss_path):
        dirnames.sort()
        folder = Path(dirpath)
        if folder.name in records:
            folders.append(folder)
            if len(folders) == index + num_articles:
                return folders[index:]
    sys.exit(f"Only {len(folders)} article folders with a CSV row found in {rdss_path}")


def main() -> None:
    """Upload the first CAAL article as a draft."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--start_index",
        type=int,
        default=0,
        help="index of first row to start with in archive csv (default = 0)",
    )
    parser.add_argument(
        "-b",
        "--bulk_upload",
        type=int,
        default=1,
        help="number of articles to upload (default = 1)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    index = args.start_index  # which article; 0 = first
    num_articles = args.bulk_upload  # number of articles to upload
    max_files = 3
    time_start = time.perf_counter()

    # 1. Read the CSV. "Digital Folder Name" is the folder's path on RDSS, e.g.
    #    KG/KG_AS/KG_AS_IHDSS/KG_AS_IHDSS-AB/KG_AS_IHDSS-AB_000031, so each row
    #    is stored under the last part of that path. (The "Caal id" column,
    #    e.g. Ar_KG_AS-000102, does not appear in folder names.)
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as fh:
        records = {
            row["Digital Folder Name"].strip().split("/")[-1]: row
            for row in csv.DictReader(fh)
        }

    # Only keep a subset of records, selected by Caal id.
    caal_ids = {
        "Ar_KG_AS-000147",
        "Ar_KG_AS-000140",
        "Ar_KG_AS-000129",
    }
    records = {
        key: row for key, row in records.items() if row["Caal id"].strip() in caal_ids
    }

    if index > len(records)-1:
        sys.exit(f"There are only {len(records)} records, please choose a different starting index.")

    if num_articles > len(records)-index:
        print(f"Specified number of articles is too high; decreasing to {len(records)-index}.")
        num_articles = len(records)-index

    # 2. Find the article folder and its files.
    folder_paths = find_article_folders(RDSS_PATH, records, index, num_articles)
    rows = [records[f.name] for f in folder_paths]
    files = [
        sorted(
            path
            for path in f.iterdir()
            if path.suffix.lower() in {".pdf", ".tif", ".tiff"}
        )
        for f in folder_paths
    ]

    print(f"Folders:  {[f.name for f in folder_paths]}")
    print(f"CAAL ids: {[row['Caal id'] for row in rows]}")
    print(
        f"Files: {len(files)} in folder,",
        f"uploading {len([f[:max_files] for f in files])}",
    )
    files = [f[:max_files] for f in files]  # files[:None] keeps them all

    # 3. Create the draft article.
    # NOTE: later use autotranslated "Original Title" instead of English Title
    metadata = [
        {
            "title": f"{r[TITLE_FIELDS[0]].strip()} / {r[TITLE_FIELDS[1]].strip()} " \
                     f"[CAAL_ID: {r[TITLE_FIELDS[2]]}]",
            # change "Copyright Holder Name" to "Owner" but retain all other description field names
            "description": f"{''.join([f'<i>{d if d != DESCRIPTION_FIELDS[0] else "Owner"}</i><br>{r[d].strip()}<br><br>'
                                       if r[d] else '' for d in DESCRIPTION_FIELDS])}",
            "authors": [{"name": "CAAL UCL"}],
            # NOTE: if you are adding group and your account doesn't have access to
            # Institute of Archaeology (21660), you can try ARC RSDG (59983) instead
            # "group_id": 21660,  # "Institute of Archaeology"
            "defined_type": "dataset",
            "categories": [27274,   # "Archaeology not elsewhere classified"
                           24907],  # "Architectural heritage and conservation"
            "keywords": ["Central Asian Archaeological Landscapes", "Central Asian History",
                         "Archaeology", "Architectural Heritage and Conservation"],
            # NOTE: use license 12 for CC BY-NC-ND 4.0
            "license": 11, # "CC BY-NC-SA 4.0"
        }
        for r in rows
    ]
    created = [figshare("POST", "/account/articles", json=m) for m in metadata]
    article_ids = [int(c["location"].split("/")[-1]) for c in created]
    print(f"Created draft articles {article_ids}")

    # 4. Upload the files.
    for i in range(len(files)):
        f = files[i]
        for path in f:
            if args.verbose:
                print(f"Uploading {path.name}")
            upload_file(article_ids[i], path)

    # 5. Fetch the article and show what was uploaded.
    articles = [figshare("GET", f"/account/articles/{i}") for i in article_ids]
    print(f"\n{len(articles)} articles on Figshare, {len(article_ids)} expected")
    print(f"{round((time.perf_counter() - time_start) / 60, 2)} minutes elapsed")
    if args.verbose:
        for i in range(len(articles)):
            print(f"\nArticle ID: {article_ids[i]}")
            print(f"Title:      {articles[i]['title']}")
            print(f"Status:     {articles[i]['status']}")
            print(
                f"Files:      {len(articles[i]['files'])} on Figshare,",
                f" {len(files[i])} expected",
            )
            print(f"URL:        {articles[i]['url_private_html']}")


if __name__ == "__main__":
    main()
