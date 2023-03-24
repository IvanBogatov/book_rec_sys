import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModel

tokenizer = AutoTokenizer.from_pretrained("cointegrated/rubert-tiny2")
model = AutoModel.from_pretrained("cointegrated/rubert-tiny2")

df = pd.read_csv('data_collection/data/database.csv')
df = df.fillna('-')
tokenized = df['annotation'].apply(lambda x: tokenizer(x, padding=True, truncation=True, return_tensors='pt'))

vector_list = []
with torch.inference_mode():
    for i in range(tokenized.shape[0]):
        model_output = model(**{k: v for k, v in tokenized[i].items()})
        
        embeddings = model_output.last_hidden_state[:, 0, :]
        vector = torch.nn.functional.normalize(embeddings)[0].cpu().numpy()
        vector_list.append(vector)
       
vec_df = pd.DataFrame(vector_list)
vec_df.to_csv('vec_df.csv')