# -*- coding: utf-8 -*-
"""whatsapp_analysis.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1tYiklY0Q65s1F-blLJGpdey-qZKg-naU
"""

import streamlit as st
import pandas as pd
import re
from datetime import datetime
import matplotlib.pyplot as plt
from collections import Counter
import nltk
from nltk.corpus import stopwords
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from umap import UMAP
from sklearn.cluster import AgglomerativeClustering

# Configurar stopwords
nltk.download('stopwords')
stop_words = set(stopwords.words('portuguese'))
additional_stopwords = {'kkkk', 'kkkkk', 'kkkkkk', 'kkkkkkk', 'kkkkkkkk', 'kkkkkkkkk', 'kkkkkkkkkk',
                        'vai', 'vou', 'cara', 'vou', 'eae', 'eai', 'vc','pra','aí','tá','lá', 'nao',
                        'q','então','pq','n','ta', 'sim', 'aqui', 'pro', 'mto', 'eh', '@5561996886412',
                        '@5561998118003','@5561998660927','@5561999011118', '@5561998669648','@5561983404441',
                        '@5561998172241','@5561981154414','@5561991074343', 'acho', 'boa', 'qm', 'tbm'}
stop_words.update(additional_stopwords)

# Função para analisar cada linha do arquivo de chat
def parse_line(line):
    match = re.match(r'\[(\d{2}/\d{2}/\d{2}), (\d{2}:\d{2}:\d{2})\] (.*?): (.*)', line)
    if match:
        date, time, user, message = match.groups()
        datetime_str = date + ' ' + time
        datetime_obj = datetime.strptime(datetime_str, '%d/%m/%y %H:%M:%S')
        return datetime_obj, user, message
    else:
        return None, None, line

# Função para preprocessar o texto e remover stopwords
def preprocess_text(text):
    text = re.sub(r'\W', ' ', str(text))  # Remove caracteres não alfanuméricos
    text = re.sub(r'\s+', ' ', text, flags=re.I)  # Remove múltiplos espaços
    text = text.lower()  # Converte para minúsculas
    words = text.split()
    words = [word for word in words if word not in stop_words and not word.startswith('5561') and not word.startswith('https')]  # Remove stopwords
    return ' '.join(words)

# Configurar a interface do Streamlit
st.title("Análise de Chat do WhatsApp")
uploaded_file = st.file_uploader("Escolha um arquivo .txt", type="txt")

if uploaded_file is not None:
    # Leitura da base
    chat_data = uploaded_file.readlines()
    chat_data = [line.decode("utf-8") for line in chat_data]

    # Analise os dados do chat
    parsed_data = [parse_line(line) for line in chat_data]
    parsed_data = [data for data in parsed_data if data[0] is not None]

    # Crie um DataFrame
    chat_df = pd.DataFrame(parsed_data, columns=['datetime', 'user', 'message'])

    # Exiba as primeiras linhas do DataFrame
    st.write(chat_df.head())

    # Reamostre os dados para obter o número de mensagens por dia
    chat_df['datetime'] = pd.to_datetime(chat_df['datetime'])
    chat_df.reset_index(inplace=True)
    messages_per_day = chat_df.resample('D', on='datetime').size()

    # Plote o número de mensagens por dia
    st.write("Número de Mensagens por Dia")
    st.line_chart(messages_per_day)

    # Conte o número de mensagens enviadas por cada usuário
    user_message_counts = chat_df['user'].value_counts()

    # Plote o número de mensagens enviadas por cada usuário
    st.write("Número de Mensagens por Usuário")
    st.bar_chart(user_message_counts)

    # Categorize as mensagens
    def categorize_message(message):
        if 'sticker omitted' in message:
            return 'Sticker'
        elif 'image omitted' in message:
            return 'Imagem'
        elif 'GIF omitted' in message:
            return 'GIF'
        elif 'video omitted' in message:
            return 'Vídeo'
        elif 'audio omitted' in message:
            return 'Áudio'
        elif 'document omitted' in message:
            return 'Documento'
        else:
            return 'Texto'

    # Aplique a função para categorizar cada mensagem
    chat_df['message_type'] = chat_df['message'].apply(categorize_message)

    # Conte o número de cada tipo de mensagem
    message_type_counts = chat_df['message_type'].value_counts()

    # Plote a distribuição dos tipos de mensagens
    st.write("Distribuição dos Tipos de Mensagens")
    st.bar_chart(message_type_counts)

    # Preprocessar o texto e remover stopwords
    chat_df['cleaned_message'] = chat_df['message'].apply(preprocess_text)

    # Filtrar grupos com mais de 100 palavras
    chat_df['word_count'] = chat_df['cleaned_message'].apply(lambda x: len(x.split()))
    filtered_df = chat_df[chat_df['word_count'] > 50]

    # Concatenar todas as mensagens para análise de frequência
    all_words = ' '.join(filtered_df['cleaned_message']).split()

    # Contar a frequência das palavras
    word_freq = Counter(all_words)

    # Converter para DataFrame para visualização
    word_freq_df = pd.DataFrame(word_freq.items(), columns=['word', 'frequency']).sort_values(by='frequency', ascending=False)

    # Mostrar as 20 palavras mais frequentes
    top_words = word_freq_df.head(20)
    st.write("Top 20 Palavras Mais Frequentes")
    st.write(top_words)

    # Plotar as 20 palavras mais frequentes
    st.write("Top 20 Palavras Mais Frequentes")
    st.bar_chart(top_words.set_index('word'))

    # Verificar o número de grupos após o filtro
    st.write(f"Número de grupos com mais de 100 palavras: {filtered_df.shape[0]}")
    st.write(f"Número de grupos totais: {chat_df.shape[0]}")

    # Utilizar modelo de linguagem pré-treinado para gerar embeddings
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    embeddings = model.encode(filtered_df['cleaned_message'], show_progress_bar=True)

    # Reduzir a dimensionalidade dos embeddings com UMAP
    umap_model = UMAP(n_neighbors=15, n_components=5, metric='cosine')
    umap_embeddings = umap_model.fit_transform(embeddings)

    # Ajustar parâmetros do BERTopic
    topic_model = BERTopic(
        nr_topics=15,
        language="portuguese",
        min_topic_size=5,
        n_gram_range=(1, 3),
        calculate_probabilities=True
    )

    topics, probabilities = topic_model.fit_transform(filtered_df['cleaned_message'], umap_embeddings)

    # Adicionar a classificação dos tópicos ao DataFrame
    filtered_df['topic'] = topics

    # Visualizar os tópicos
    topic_info = topic_model.get_topic_info()
    st.write("Tópicos mais discutidos no grupo")
    st.write(topic_info)

    # Visualizar as palavras-chave de cada tópico
    for topic in range(len(topic_model.get_topics())):
        if topic == -1:  # Outliers
            continue
        st.write(f"Tópico {topic}:")
        st.write(topic_model.get_topic(topic))

    # Obter embeddings dos tópicos
    topic_embeddings = topic_model.topic_embeddings_

    # Agrupar tópicos utilizando clustering hierárquico
    clustering_model = AgglomerativeClustering(n_clusters=5)
    topic_labels = clustering_model.fit_predict(topic_embeddings)

    # Adicionar os rótulos de cluster aos tópicos
    topic_info['cluster'] = topic_labels

    # Visualizar os clusters de tópicos
    st.write("Clusters dos tópicos")
    st.write(topic_info)

    # Visualizar os tópicos em um gráfico interativo (opcional)
    st.write(topic_model.visualize_topics())
    st.write(topic_model.visualize_distribution(probabilities[0]))

    # Salvar o DataFrame resultante em um novo CSV
    filtered_df.to_csv('filtered_grouped_chat_with_topics.csv', index=False)
    topic_info.to_csv('topic_info_with_clusters.csv', index=False)

    st.write("Análise completa e resultados salvos em CSV.")
