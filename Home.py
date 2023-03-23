import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModel
from sklearn.metrics.pairwise import cosine_similarity
from recsys import *

st.set_page_config(
    page_title='Умный поиск книг',
    page_icon= ":book:",
    layout='wide')

model = AutoModel.from_pretrained('rubert_tiny2')
tokenizer = AutoTokenizer.from_pretrained('tokenizer_rubert_tiny2')
vec_df = pd.read_csv('vec_df.csv', index_col=0)
df = pd.read_csv('database.csv', index_col=0)

st.title("Умный поиск книг")
st.write('### Поиск книг на сайте [Библио-глобус](https://www.biblio-globus.ru/category?cid=182&pagenumber=1) по описанию сюжета или содержания')
st.write('''Наш поисковик не ищет по ключевым словам. Он устроен другим образом. 
         Когда вы вводите запрос, происходит анализ его смыслового содержания и на ваш выбор
         предлагаются книги с наиболее подходящим описанием.
         ''')

prompt = st.text_input(label='Введите запрос', value='', placeholder='Пользовательский запрос')


#st.markdown(output)

ret = st.button("Найти",
                           ("\n"))

top_n = 3

if ret:
    output, ind = recommend(prompt, top_n, model, tokenizer, vec_df, df)
    for i in range(top_n):
        col1, col2 = st.columns([1,5])
        with col1:
            st.image(output['image_url'][ind[i]])
    
        with col2:
            st.subheader(f'''**{output['title'][ind[i]]}**''')
            st.caption(output['author'][ind[i]])
            st.markdown(output['annotation'][ind[i]])
