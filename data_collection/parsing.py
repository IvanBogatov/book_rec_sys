from pathlib import Path
import pandas as pd

import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

from config import GENRE_CID, LOGFILE_PATH, DATA_PATH, INIT

import logging
logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                    level=logging.INFO,
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename=LOGFILE_PATH,
                    filemode='a')


def get_data_from_url(html:str, is_max_page:bool = False):
  """
  Recieve html page and give back list of books' id or max pages.

  input:
    html:str - html code of the page
    is_max_page:bool - if True the function will give back last page number in the catalog, 
                        if False (default) the function will give back list of books' ids
  
  output:
    last page number or list of books' ids
  """

  soup = BeautifulSoup(html, 'html.parser')

  if is_max_page:
    return int(soup.find_all('a', class_='page-link')[-1].get('data-page'))
  else:
    data_list = []
    for link in soup.find_all('a', class_='rounded'):
        data_list.append(link.get('href')[9:])
    return data_list

def collect_data(html:str, book_url:str, genre_idx:int, cid:str):
  """
  Function collect data from html file.

  input:
    html:str - html code of the page
    book_url:str - book page url
    genre_idx:int - genre index from config file
    cid:str - subgenre id
  """

  # Parse html page and collect necessary data
  genre = GENRE_CID[genre_idx]['genre']
  subgenre = GENRE_CID[genre_idx]['subgenre'][cid]
  soup = BeautifulSoup(html, 'html.parser')
  imgage_author_title_data = soup.find('img', class_='rounded img-fluid')
  image_url = imgage_author_title_data.get('src')
  author_title = imgage_author_title_data.get('data-caption')
  author = author_title[author_title.index('|')+2:]
  title = author_title[:author_title.index('|')-1]
  annotation = soup.find_all('p', class_='card-text')[3].get_text()
  price = soup.find('div', class_='card-title card-price').get_text().split()[0]
  try:
    status = soup.find('span', class_='card-status').get_text()
  except:
    status = soup.find('span', class_='card-status-out-of-stock').get_text()


  new_line = {
    'page_url': [book_url],
    'image_url': [image_url],
    'author': [author],
    'title': [title],
    'annotation': [annotation],
    'price': [price],
    'status': [status],
    'genre': [genre],
    'subgenre': [subgenre],
    'dttm_updated': [pd.Timestamp.now()]
  }
  return pd.DataFrame(new_line)

def update_data(data:list):
  """
  Procedure update data in database.csv file by appending new data.

  input:
    data:list - list of 20 books' information
  """

  # Check file existence, if no - create
  file_path = Path(DATA_PATH)
  if not file_path.is_file():
    Path('data/').mkdir(parents=True, exist_ok=True)
    columns=['page_url', 'image_url',	'author', 'title', 'annotation', 'price', 'status', 'genre', 'subgenre', 'dttm_updated']
    df = pd.DataFrame(columns=columns)
    df.to_csv(file_path, index=False)
  
  # Update data
  df = pd.read_csv(file_path)
  temp_df = pd.concat(data, ignore_index=True)
  df = pd.concat([df, temp_df], ignore_index=True)
  df = df.drop_duplicates().reset_index(drop=True)
  df.to_csv(file_path, index=False)

def initial_params() -> tuple[int, str, int, int]:
  """
  Function gives back initial parameters.

  output:
    genre_idx:int - saved genre index from config file
    cid:str - saved subgenre id
    page_num:int - saved current catalog page number of certain genre_idx and cid
    max_pages:int - saved max catalog page number of certain genre_idx and cid
  """

  # Check init file existence, if no - create
  file_path = Path(INIT)
  if not file_path.is_file():
    genre_idx, cid, page_num, max_pages = 0, list(GENRE_CID[0]['subgenre'].keys())[0], 1, 1
    update_initial_params(genre_idx, cid, page_num, max_pages)
  else:
    data = open(INIT, "r").read().split(', ')
    if len(data) == 1:
      file_path.unlink()
      genre_idx, cid, page_num, max_pages = initial_params()
    else:
      genre_idx, cid, page_num, max_pages = data
  return int(genre_idx), cid, int(page_num), int(max_pages)

def update_initial_params(genre_id, cid, page_num, max_pages):
  """
  Procedure updates initialising file.
  """
  
  text_file = open(INIT, "w")
  text_file.write(f'{genre_id}, {cid}, {page_num}, {max_pages}')
  text_file.close()

async def goto_url(url:str, page_, tries:int=1, is_book:bool=False):
  """
  The function allows to go to the url and restarts if it fails.

  input:
    url:str - target URL
    page_ - browser page object
    tries:int - number of tries to connect (default: tries=1)
    is_book:bool - the flag whether to connect to book page (True) or to catalog page (False) (default: is_book=False)
  """
  
  if tries == 4:
    logging.info(f"Connection Error. Can't properly connect 3 times. to {url=}")
    return
  try:
    await page_.goto(url)
    selector = '[class="rounded img-fluid"]' if is_book else '[class="page-link"]'
    await page_.wait_for_selector(selector)

  except:
    tries+=1
    logging.info(f'Try to reconnect to {url=}')
    await goto_url(url, page_, tries, is_book=is_book)

async def main():
  async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    page = await browser.new_page()
    logging.info('Start scrapping.')

    # Initialise parameters
    init_genre_idx, init_cid, page_num, max_pages = initial_params()

    # !Could be transformed to 'for loop' in the case of several genres
    genre_idx = init_genre_idx
    cids = list(GENRE_CID[genre_idx]['subgenre'].keys())
    init_cid_idx = cids.index(init_cid)

    for cid in cids[init_cid_idx:]:
      while page_num < max_pages+1:
        # Go to the catalog page
        url = f'https://www.biblio-globus.ru/category?cid={cid}&pagenumber={str(page_num)}'
        logging.info(f"Go to {url=}.")
        await goto_url(url, page)

        # Collect books' ids at the page
        html = await page.inner_html('*')
        book_id_list = get_data_from_url(html)

        # Get last catalog page number at the 1st page
        if page_num == 1:
          max_pages = get_data_from_url(html, is_max_page=True)
        
        # Collect data from each book page and store it to database.csv
        books_data = []
        for book_id in book_id_list:
          book_url = f'https://www.biblio-globus.ru/product/{book_id}'
          logging.info(f"Go to {book_url=}.")
          await goto_url(book_url, page, is_book=True)

          book_html = await page.inner_html('*')
          try:
            books_data.append(collect_data(book_html, book_url, genre_idx, cid))
          except:
            continue
          logging.info(f"Data added for {book_id=}.")
        
        update_data(books_data)
        page_num+=1
        update_initial_params(genre_idx, cid, page_num, max_pages)

      page_num = max_pages = 1

    await browser.close()

if __name__ == '__main__':
  asyncio.run(main())
  logging.info('Done')