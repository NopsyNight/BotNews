import os
import time
import logging
import feedparser
import requests
from datetime import datetime

# 1. Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 2. Configurações e Variáveis de Ambiente
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")

TIMEOUT = 10
MAX_RETRIES = 2
RETRY_DELAY = 2

KEYWORDS_INTERESSE = ["Java", "Spring", "Python", "Backend", "SQL", "API", "Vaga", "I.A", "Anthropic"]

RSS_FEEDS = {
    "TechCrunch": "https://techcrunch.com/feed/",
    "Dev.to": "https://dev.to/feed",
    "Tecnoblog": "https://tecnoblog.net/feed/",
    "Canaltech": "https://canaltech.com.br/rss/",
}

# 3. Funções de Suporte
def formatar_titulo(titulo: str) -> str:
    if not titulo: return "Sem título"
    titulo_safe = titulo.replace('<', '&lt;').replace('>', '&gt;')
    for kw in KEYWORDS_INTERESSE:
        if kw.lower() in titulo.lower():
            return f"🔥 <b>{titulo_safe}</b>"
    return titulo_safe

def enviar_telegram(mensagem: str, retry_count: int = 0) -> bool:
    if not mensagem or not mensagem.strip(): return False
    
    if len(mensagem) > 4096:
        mensagem = mensagem[:4090] + "..."
        
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID, 
        "text": mensagem, 
        "parse_mode": "HTML", 
        "disable_web_page_preview": True
    }
    
    try:
        # Timeout curto para não travar o GitHub Actions
        response = requests.post(url, json=payload, timeout=TIMEOUT)
        response.raise_for_status()
        return True
    except Exception as e:
        if retry_count < MAX_RETRIES:
            time.sleep(RETRY_DELAY)
            return enviar_telegram(mensagem, retry_count + 1)
        logger.error(f"Falha ao enviar: {e}")
        return False

# 4. Buscadores de Notícias
def buscar_rss(limite=3):
    bloco = "<b>=== NOTÍCIAS RSS ===</b>\n"
    for nome, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)
        bloco += f"\n📌 <b>{nome}</b>\n"
        # Pegamos apenas as top notícias de cada feed
        for entrada in feed.entries[:limite]:
            titulo = formatar_titulo(entrada.get("title", ""))
            link = entrada.get("link", "#")
            bloco += f"• <a href='{link}'>{titulo}</a>\n"
    return bloco

def buscar_hackernews(limite=5):
    bloco = "<b>=== HACKER NEWS ===</b>\n\n"
    try:
        ids = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=5).json()[:limite]
        for story_id in ids:
            item = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json", timeout=5).json()
            titulo = formatar_titulo(item.get("title", ""))
            link = item.get("url", f"https://news.ycombinator.com/item?id={story_id}")
            bloco += f"🔹 <a href='{link}'>{titulo}</a>\n"
    except:
        bloco += "<i>Erro ao carregar Hacker News.</i>"
    return bloco

# 5. Execução Principal
def executar_bot():
    # Envia o cabeçalho separado
    agora = datetime.now().strftime('%d/%m/%Y %H:%M')
    enviar_telegram(f"🚀 <b>TECH REPORT - {agora}</b>\n<code>Status: Online</code>")
    
    # Busca e envia cada bloco de uma vez (evita que um erro mate o outro)
    print("Buscando RSS...")
    enviar_telegram(buscar_rss())
    
    print("Buscando Hacker News...")
    enviar_telegram(buscar_hackernews())
    
    if NEWSAPI_KEY:
        print("Buscando NewsAPI...")
        # Lógica simples para a NewsAPI aqui...
        
    print("Processo finalizado!")

if __name__ == "__main__":
    executar_bot()