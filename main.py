import os
import feedparser
import requests
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURAÇÕES DO TELEGRAM E APIs
# ─────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")

RSS_FEEDS = {
    "TechCrunch": "https://techcrunch.com/feed/",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "The Verge":    "https://www.theverge.com/rss/index.xml",
    "dev.to":       "https://dev.to/feed",
    "G1 Tecnologia": "https://g1.globo.com/dynamo/tecnologia/rss2.xml",
    "Canaltech": "https://canaltech.com.br/rss/",
    "Tecnoblog": "https://tecnoblog.net/feed/",
    "Inovação Tecnológica": "https://www.inovacaotecnologica.com.br/boletim/rss.xml",
    "UOL Tecnologia": "https://rss.uol.com.br/feed/tecnologia.xml",
}

def enviar_telegram(mensagem):
    """Envia a mensagem montada para o seu Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": mensagem,
        "parse_mode": "HTML",
        "disable_web_page_preview": True # Evita poluição visual com muitos links
    }
    requests.post(url, json=payload)

# ─────────────────────────────────────────────
# 1. VIA RSS FEED
# ─────────────────────────────────────────────
def buscar_rss(limite=3):
    texto = "<b>=== NOTÍCIAS DO DIA===</b>\n"
    for nome, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)
        texto += f"\n<b>[{nome}]</b>\n"
        for entrada in feed.entries[:limite]:
            titulo = entrada.get("title", "Sem título")
            link   = entrada.get("link",  "#")
            texto += f"• <a href='{link}'>{titulo}</a>\n"
    return texto

# ─────────────────────────────────────────────
# 2. VIA HACKER NEWS
# ─────────────────────────────────────────────
def buscar_hackernews(limite=5):
    texto = "<b>=== HACKER NEWS (Top Stories) ===</b>\n\n"
    url_ids = "https://hacker-news.firebaseio.com/v0/topstories.json"
    ids = requests.get(url_ids).json()[:limite]
    for story_id in ids:
        url_item = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
        item = requests.get(url_item).json()
        titulo = item.get("title", "Sem título")
        link   = item.get("url", f"https://news.ycombinator.com/item?id={story_id}")
        pontos = item.get("score", 0)
        texto += f"• [{pontos} pts] <a href='{link}'>{titulo}</a>\n"
    return texto

# ─────────────────────────────────────────────
# 3. VIA NEWSAPI.ORG
# ─────────────────────────────────────────────
def buscar_newsapi(palavra_chave="technology", limite=5):
    if NEWSAPI_KEY == os.getenv("NEWSAPI_KEY"):
        return "<i>NEWSAPI não configurada.</i>"
    
    texto = f"<b>=== NEWSAPI — '{palavra_chave}' ===</b>\n\n"
    url = (
        "https://newsapi.org/v2/everything"
        f"?q={palavra_chave}&language=pt&sortBy=publishedAt"
        f"&pageSize={limite}&apiKey={NEWSAPI_KEY}"
    )
    dados = requests.get(url).json()
    for artigo in dados.get("articles", []):
        titulo = artigo.get('title', 'Sem título')
        link = artigo.get('url', '#')
        texto += f"• <a href='{link}'>{titulo}</a>\n"
    return texto

# ─────────────────────────────────────────────
# EXECUÇÃO
# ─────────────────────────────────────────────
if __name__ == "__main__":
    cabecalho = f"🚀 <b>Notícias de T.I. — {datetime.now().strftime('%d/%m/%Y %H:%M')}</b>\n"
    
    # Coletando os textos
    msg_rss = buscar_rss(limite=3)
    msg_hn = buscar_hackernews(limite=5)
    msg_api = buscar_newsapi("cybersecurity", limite=5)
    
    # Enviando em blocos separados para evitar o limite de 4096 caracteres do Telegram
    enviar_telegram(cabecalho)
    enviar_telegram(msg_rss)
    enviar_telegram(msg_hn)
    if "não configurada" not in msg_api:
        enviar_telegram(msg_api)
        
    print("Notícias enviadas com sucesso para o Telegram!")