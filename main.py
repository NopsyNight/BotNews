import os
import time
import logging
import feedparser
import requests
import schedule
from datetime import datetime
from flask import Flask
from threading import Thread

# ─────────────────────────────────────────────
# 1. CONFIGURAÇÃO DE LOGS
# ─────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 2. CONFIGURAÇÕES DO TELEGRAM E APIs
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
}

KEYWORDS_INTERESSE = ["Java", "Spring", "Python", "Backend", "SQL", "API", "Vaga", "I.A", "Anthropic"]

# ─────────────────────────────────────────────
# 3. KEEP-ALIVE (SERVIDOR FLASK PARA A RENDER)
# ─────────────────────────────────────────────
app = Flask('')

@app.route('/')
def home():
    return "🚀 Bot de Notícias está Online na Render!"

def run_server():
    # A Render injeta a porta automaticamente na variável de ambiente PORT, ou usa 10000 como fallback
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ─────────────────────────────────────────────
# 4. FUNÇÕES DE SUPORTE E BUSCA
# ─────────────────────────────────────────────
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
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        if retry_count < 3:
            time.sleep(2)
            return enviar_telegram(mensagem, retry_count + 1)
        logger.error(f"Falha ao enviar: {e}")
        return False

def buscar_rss(limite=3):
    bloco = "<b>=== NOTÍCIAS RSS ===</b>\n"
    for nome, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)
        bloco += f"\n📌 <b>{nome}</b>\n"
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

def buscar_newsapi(palavra_chave="technology", limite=5):
    if not NEWSAPI_KEY:
        return "<i>NEWSAPI não configurada.</i>"
    
    texto = f"<b>=== NEWSAPI — '{palavra_chave}' ===</b>\n\n"
    try:
        url = f"https://newsapi.org/v2/everything?q={palavra_chave}&language=pt&sortBy=publishedAt&pageSize={limite}&apiKey={NEWSAPI_KEY}"
        dados = requests.get(url, timeout=5).json()
        for artigo in dados.get("articles", []):
            titulo = formatar_titulo(artigo.get('title', 'Sem título'))
            link = artigo.get('url', '#')
            texto += f"• <a href='{link}'>{titulo}</a>\n"
    except:
        texto += "<i>Erro ao carregar NewsAPI.</i>"
    return texto

# ─────────────────────────────────────────────
# 5. LÓGICA DE EXECUÇÃO E AGENDAMENTO
# ─────────────────────────────────────────────
def executar_bot():
    logger.info("Coletando notícias...")
    agora = datetime.now().strftime('%d/%m/%Y %H:%M')
    
    enviar_telegram(f"🚀 <b>TECH REPORT - {agora}</b>\n<code>Status: Online via Render</code>")
    enviar_telegram(buscar_rss())
    enviar_telegram(buscar_hackernews())
    
    msg_api = buscar_newsapi("cybersecurity", limite=5)
    if "não configurada" not in msg_api:
        enviar_telegram(msg_api)
        
    logger.info("Notícias enviadas com sucesso para o Telegram!")

def tarefa_diaria():
    logger.info("Iniciando disparo agendado...")
    executar_bot()

# ─────────────────────────────────────────────
# STARTUP DO SISTEMA
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # 1. Inicia o servidor Web em uma thread separada (para a Render não desligar a máquina)
    Thread(target=run_server).start()
    
    # 2. Configura o relógio (Lembrando que o servidor usa UTC. 12:00 UTC = 09:00 Brasil)
    # Ajuste o horário abaixo para o minuto desejado
    horario_agendado = "12:00" 
    schedule.every().day.at(horario_agendado).do(tarefa_diaria)
    
    logger.info(f"Sistema iniciado! Servidor web rodando e bot agendado para {horario_agendado} (UTC).")
    
    # OPCIONAL: Descomente a linha abaixo se quiser que o bot mande as notícias ASSIM QUE a Render ligar, 
    # além de mandar no horário agendado.
    # executar_bot()
    
    # 3. Mantém o processo vivo, checando o relógio a cada minuto
    while True:
        schedule.run_pending()
        time.sleep(60)