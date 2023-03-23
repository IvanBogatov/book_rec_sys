import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModel
from sklearn.metrics.pairwise import cosine_similarity


def embed_bert_cls(text, model, tokenizer):
    t = tokenizer(text, padding=True, truncation=True, return_tensors='pt')
    with torch.no_grad():
        model_output = model(**{k: v.to(model.device) for k, v in t.items()})
    embeddings = model_output.last_hidden_state[:, 0, :]
    embeddings = torch.nn.functional.normalize(embeddings)
    return embeddings[0].cpu().numpy()


def recommend(user_query, top_n, model, tokenizer, vec_df, df):
    test_vec = embed_bert_cls(user_query, model, tokenizer)
    ret=cosine_similarity(vec_df, pd.DataFrame(test_vec).transpose())
    ret_df = pd.DataFrame(ret)
    ret_index = ret_df.sort_values(by=0, ascending=False).head(top_n).index
    result = df.iloc[ret_index].copy().to_dict()
    return result, ret_index.to_list()
