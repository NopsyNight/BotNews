import os
import time
import logging
import feedparser
import requests
from datetime import datetime

# CONFIGURAÇÃO DE LOGS (Substitui o "from venv import logger")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# CONFIGURAÇÕES DO TELEGRAM E APIs
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")

# Parâmetros de Retry e Timeout 
TIMEOUT = 10          # Segundos máximo por requisição HTTP
MAX_RETRIES = 3       # Tentativas antes de desistir
RETRY_DELAY = 2       # Segundos entre tentativas

# Palavras-chave de interesse
KEYWORDS_INTERESSE = ["Java", "Spring", "Python", "Backend", "SQL", "API", "Vaga", "I.A", "Anthropic"]

# Validação crítica de variáveis de ambiente
if not TELEGRAM_TOKEN or not CHAT_ID:
    raise ValueError("❌ TELEGRAM_TOKEN e CHAT_ID devem estar configurados!")

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

def formatar_titulo(titulo: str) -> str:
    if not titulo:
        return "Sem título"
    
    # Destacar as Keywords de Interesse
    for keyword in KEYWORDS_INTERESSE:
        if keyword.lower() in titulo.lower():
            # Escapar caracteres especiais do HTML
            titulo_safe = titulo.replace('<', '&lt;').replace('>', '&gt;')
            return f"🔥 <b>{titulo_safe}</b>"
    
    return titulo.replace('<', '&lt;').replace('>', '&gt;')

def enviar_telegram(mensagem: str, retry_count: int = 0) -> bool:
    """Envia a mensagem montada para o seu Telegram com sistema de retry."""
    if not mensagem or not mensagem.strip():
        logger.warning("Mensagem vazia, não será enviada.")
        return False
        
    # Telegram tem um limite de 4096 caracteres
    if len(mensagem) > 4096:
        logger.warning(f"Mensagem muito longa ({len(mensagem)} chars), truncando...")
        mensagem = mensagem[:4093] + "..."
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": mensagem,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    # Método com retry automático (removemos o request.post solto que duplicava o envio)
    try:
        response = requests.post(url, json=payload, timeout=TIMEOUT)
        response.raise_for_status()
        logger.info("✅ Mensagem enviada com sucesso")
        return True
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao enviar mensagem: {e}")
        
        # Retry lógico usando a variável correta (retry_count)
        if retry_count < MAX_RETRIES:
            logger.info(f"🔄 Tentando novamente ({retry_count + 1}/{MAX_RETRIES})...")
            time.sleep(RETRY_DELAY)
            return enviar_telegram(mensagem, retry_count + 1)
        
        logger.error("Houve falha após todas as tentativas")
        return False

# ─────────────────────────────────────────────
# FONTES DE NOTÍCIAS (Agora usando formatar_titulo)
# ─────────────────────────────────────────────
def buscar_rss(limite=3):
    texto = "<b>=== NOTÍCIAS DO DIA ===</b>\n"
    for nome, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)
        texto += f"\n<b>[{nome}]</b>\n"
        for entrada in feed.entries[:limite]:
            # APLICANDO A FORMATAÇÃO AQUI
            titulo = formatar_titulo(entrada.get("title", "Sem título"))
            link   = entrada.get("link",  "#")
            texto += f"• <a href='{link}'>{titulo}</a>\n"
    return texto

def buscar_hackernews(limite=5):
    texto = "<b>=== HACKER NEWS (Top Stories) ===</b>\n\n"
    url_ids = "https://hacker-news.firebaseio.com/v0/topstories.json"
    ids = requests.get(url_ids).json()[:limite]
    for story_id in ids:
        url_item = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
        item = requests.get(url_item).json()
        # APLICANDO A FORMATAÇÃO AQUI
        titulo = formatar_titulo(item.get("title", "Sem título"))
        link   = item.get("url", f"https://news.ycombinator.com/item?id={story_id}")
        pontos = item.get("score", 0)
        texto += f"• [{pontos} pts] <a href='{link}'>{titulo}</a>\n"
    return texto

def buscar_newsapi(palavra_chave="technology", limite=5):
    # CORREÇÃO DA VERIFICAÇÃO DA KEY
    if not NEWSAPI_KEY:
        return "<i>NEWSAPI não configurada.</i>"
    
    texto = f"<b>=== NEWSAPI — '{palavra_chave}' ===</b>\n\n"
    url = (
        "https://newsapi.org/v2/everything"
        f"?q={palavra_chave}&language=pt&sortBy=publishedAt"
        f"&pageSize={limite}&apiKey={NEWSAPI_KEY}"
    )
    dados = requests.get(url).json()
    for artigo in dados.get("articles", []):
        # APLICANDO A FORMATAÇÃO AQUI
        titulo = formatar_titulo(artigo.get('title', 'Sem título'))
        link = artigo.get('url', '#')
        texto += f"• <a href='{link}'>{titulo}</a>\n"
    return texto


# EXECUÇÃO 
def executar_bot():
    cabecalho = f"🚀 <b>Notícias de T.I. — {datetime.now().strftime('%d/%m/%Y %H:%M')}</b>\n"
    
    msg_rss = buscar_rss(limite=3)
    msg_hn = buscar_hackernews(limite=5)
    msg_api = buscar_newsapi("cybersecurity", limite=5)
    
    # Enviando o cabeçalho primeiro e validando
    if not enviar_telegram(cabecalho):
        logger.error("Falha ao enviar cabeçalho! Abortando execução.")
        return
        
    enviar_telegram(msg_rss)
    enviar_telegram(msg_hn)
    
    if "não configurada" not in msg_api:
        enviar_telegram(msg_api)
        
    logger.info("Notícias processadas com sucesso para o Telegram!")

if __name__ == "__main__":
    try:
        executar_bot()
    except KeyboardInterrupt:
        logger.info("!!! Bot interrompido pelo usuário")
    except Exception as e:
        logger.critical(f"💥 Erro crítico: {e}", exc_info=True)