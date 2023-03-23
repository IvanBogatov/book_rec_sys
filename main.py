import logging
from pathlib import Path

import pandas as pd
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio

from config import GENRE_CID, LOGFILE_PATH, DATA_PATH, INIT

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                    level=logging.INFO,
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename=LOGFILE_PATH,
                    filemode='a')


def get_data_from_url(html: str, is_max_page: bool =False) -> list[str]:
  """
  Recieve html page and give back list of books' id or max pages
  """
  soup = BeautifulSoup(html, 'html.parser')
  data_list = []

  if is_max_page:
    return int(soup.find_all('a', class_='page-link')[-1].get('data-page'))
  else:
    for link in soup.find_all('a', class_='rounded'):
        data_list.append(link.get('href')[9:])

    return data_list

def update_data(html: str, book_url:str, genre_id:int, cid:str):
  genre = GENRE_CID[genre_id]['genre']
  subgenre = GENRE_CID[genre_id]['subgenre'][cid]
  soup = BeautifulSoup(html, 'html.parser')
  imgage_author_title_data = soup.find('img', class_='rounded img-fluid')
  image_url = imgage_author_title_data.get('src')
  author_title = imgage_author_title_data.get('data-caption')
  author = author_title[:author_title.index('|')-1]
  title = author_title[author_title.index('|')+2:]
  annotation = soup.find_all('p', class_='card-text')[3].get_text()
  price = soup.find('div', class_='card-title card-price').get_text().split()[0]
  status = soup.find('span', class_='card-status').get_text()


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

  file_path = Path(DATA_PATH)
  if not file_path.is_file():
    columns=['page_url', 'image_url',	'author', 'title', 'annotation', 'price', 'status', 'genre', 'subgenre', 'dttm_updated']
    df = pd.DataFrame(columns=columns)
    df.to_csv(file_path, index=False)
  
  df = pd.read_csv(file_path)
  df = pd.concat([df, pd.DataFrame(new_line)], ignore_index=True)
  df = df.drop_duplicates().reset_index(drop=True)
  df.to_csv(file_path, index=False)

def initial_params() -> tuple[int, str, int, int]:
  file_path = Path(INIT)
  if not file_path.is_file():
    genre_id, cid, page_num, max_pages = 0, list(GENRE_CID[0]['subgenre'].keys())[0], 1, 1
    update_initial_params(genre_id, cid, page_num, max_pages)
  else:
    data = open(INIT, "r").read().split(', ')
    if len(data) == 1:
      file_path.unlink()
      genre_id, cid, page_num, max_pages = initial_params()
    else:
      genre_id, cid, page_num, max_pages = data
  return int(genre_id), cid, int(page_num), int(max_pages)

def update_initial_params(genre_id, cid, page_num, max_pages):
  text_file = open(INIT, "w")
  text_file.write(f'{genre_id}, {cid}, {page_num}, {max_pages}')
  text_file.close()

async def main():
  async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    page = await browser.new_page()
    logging.info('Start scrapping.')

    init_genre_id, init_cid, page_num, max_pages = initial_params()

    genre_id = init_genre_id
    cids = list(GENRE_CID[init_genre_id]['subgenre'].keys())
    init_cid_idx = cids.index(init_cid)
    for cid in cids[init_cid_idx:]:
      while page_num < max_pages+1:
        url = f'https://www.biblio-globus.ru/category?cid={cid}&pagenumber={str(page_num)}'
        await page.goto(url)
        logging.info(f"Go to {url=}.")

        html = await page.inner_html('*')
        book_id_list = get_data_from_url(html)

        if page_num == 1:
          max_pages = get_data_from_url(html, is_max_page=True)
          
        for book_id in book_id_list:
          book_url = f'https://www.biblio-globus.ru/product/{book_id}'
          await page.goto(book_url)
          logging.info(f"Go to {book_url=}.")

          book_html = await page.inner_html('*')
          update_data(book_html, book_url, genre_id, cid)
          update_initial_params(genre_id, cid, page_num, max_pages)
          logging.info(f"Data added for {book_id=}.")
        
        page_num+=1

    await browser.close()

if __name__ == '__main__':
  asyncio.run(main())
  print('Done')



# text_file = open("sample.txt", "w")
# n = text_file.write(string)
# text_file.close()