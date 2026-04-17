import os
import time
import logging
import feedparser
import requests
import schedule
import re
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
CHAT_ID_RAW    = os.getenv("CHAT_ID")
NEWSAPI_KEY    = os.getenv("NEWSAPI_KEY")

# FIX #7 — Verifica variáveis obrigatórias antes de iniciar
if not TELEGRAM_TOKEN or not CHAT_ID_RAW:
    logger.critical("❌ TELEGRAM_TOKEN e CHAT_ID são obrigatórios! Configure as variáveis de ambiente.")
    exit(1)

try:
    CHAT_ID = int(CHAT_ID_RAW)
except ValueError:
    logger.critical("❌ CHAT_ID precisa ser um número inteiro.")
    exit(1)

RSS_FEEDS = {
    "TechCrunch":    "https://techcrunch.com/feed/",
    "Ars Technica":  "https://feeds.arstechnica.com/arstechnica/index",
    "The Verge":     "https://www.theverge.com/rss/index.xml",
    "dev.to":        "https://dev.to/feed",
    "G1 Tecnologia": "https://g1.globo.com/dynamo/tecnologia/rss2.xml",
    "Canaltech":     "https://canaltech.com.br/rss/",
    "Tecnoblog":     "https://tecnoblog.net/feed/",
}

KEYWORDS_INTERESSE = [
    "Java", "Spring", "Python", "Backend", "SQL",
    "API", "Vaga", "I.A", "Anthropic", "IA", "LLM",
    "Segurança", "Cloud", "DevOps", "Linux",
]


# ─────────────────────────────────────────────
# 3. KEEP-ALIVE (SERVIDOR FLASK PARA A RENDER)
# ─────────────────────────────────────────────
app = Flask('')

@app.route('/')
def home():
    return "🚀 Mensageiro está ativo!"

def run_server():
    # A Render injeta a porta automaticamente via variável PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)


# ─────────────────────────────────────────────
# 4. FUNÇÕES DE SUPORTE
# ─────────────────────────────────────────────
def formatar_titulo(titulo: str) -> str:
    """Escapa HTML e destaca palavras de interesse com negrito e emoji."""
    if not titulo:
        return "Sem título"
    titulo_safe = titulo.replace('<', '&lt;').replace('>', '&gt;')
    for kw in KEYWORDS_INTERESSE:
        if kw.lower() in titulo_safe.lower():
            return f"🔥 <b>{titulo_safe}</b>"
    return titulo_safe


def limpar_html(texto: str) -> str:
    """Remove tags HTML que não sejam permitidas pelo Telegram (<b>, <i>, <a>)."""
    return re.sub(r'<(?!/?(b|i|a)(\s[^>]*)?>)[^>]+>', '', texto)


def enviar_mensagem_em_partes(chat_id: int, texto_completo: str):
    """
    Divide o texto em blocos separados por linha dupla e envia cada um
    individualmente, respeitando o limite de caracteres do Telegram.
    """
    partes = texto_completo.split('\n\n')
    for parte in partes:
        parte = parte.strip()
        if not parte:
            continue
        try:
            parte_limpa = limpar_html(parte)
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": parte_limpa,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }
            resp = requests.post(url, json=payload, timeout=10)
            if not resp.ok:
                logger.warning(f"Telegram rejeitou mensagem: {resp.text}")
        except Exception as e:
            logger.error(f"Erro ao enviar parte para o Telegram: {e}")


# ─────────────────────────────────────────────
# 5. FUNÇÕES DE BUSCA DE NOTÍCIAS
# ─────────────────────────────────────────────
def buscar_rss(limite: int = 3) -> str:
    """
    Lê os feeds RSS configurados e retorna um bloco de texto formatado.
    FIX #5 — usa requests com timeout para evitar travamento da thread.
    """
    bloco = "<b>=== 📰 NOTÍCIAS RSS ===</b>\n"
    for nome, url in RSS_FEEDS.items():
        try:
            # FIX #5 — download com timeout antes de passar ao feedparser
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            feed = feedparser.parse(response.content)

            if not feed.entries:
                logger.warning(f"Feed vazio ou indisponível: {nome}")
                continue

            bloco += f"\n📌 <b>{nome}</b>\n"
            for entrada in feed.entries[:limite]:
                titulo = formatar_titulo(entrada.get("title", "Sem título"))
                link   = entrada.get("link", "#")
                bloco += f"• <a href='{link}'>{titulo}</a>\n"

        except requests.exceptions.Timeout:
            logger.error(f"Timeout ao acessar feed: {nome}")
        except Exception as e:
            # FIX #4 — captura a exceção e loga corretamente
            logger.error(f"Erro ao processar feed '{nome}': {e}")

    return bloco


def buscar_hackernews(limite: int = 5) -> str:
    """Busca as top stories do Hacker News via API pública."""
    bloco = "<b>=== 👾 HACKER NEWS ===</b>\n\n"
    try:
        ids_resp = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=10
        )
        ids_resp.raise_for_status()
        ids = ids_resp.json()[:limite]

        for story_id in ids:
            item_resp = requests.get(
                f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                timeout=10
            )
            item_resp.raise_for_status()
            item   = item_resp.json()
            titulo = formatar_titulo(item.get("title", ""))
            link   = item.get("url", f"https://news.ycombinator.com/item?id={story_id}")
            pontos = item.get("score", 0)
            bloco += f"🔹 [{pontos} pts] <a href='{link}'>{titulo}</a>\n"

    except Exception as e:
        # FIX #4 — captura a exceção e loga corretamente
        logger.error(f"Erro ao carregar Hacker News: {e}")
        bloco += "<i>Erro ao carregar Hacker News.</i>"

    return bloco


def buscar_newsapi(palavra_chave: str = "tecnologia", limite: int = 5) -> str:
    if not NEWSAPI_KEY:
        logger.info("NEWSAPI_KEY não configurada, pulando esta fonte.")
        return ""

    texto = f"<b>=== 🌐 NEWSAPI — '{palavra_chave}' ===</b>\n\n"
    try:
        url = (
            "https://newsapi.org/v2/everything"
            f"?q={palavra_chave}"
            f"&language=pt"
            f"&sortBy=publishedAt"
            f"&pageSize={limite}"
            f"&apiKey={NEWSAPI_KEY}"
        )
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        dados = resp.json()

        artigos = dados.get("articles", [])
        if not artigos:
            return ""

        for artigo in artigos:
            titulo = formatar_titulo(artigo.get('title', 'Sem título'))
            link   = artigo.get('url', '#')
            texto += f"• <a href='{link}'>{titulo}</a>\n"

    except Exception as e:
        # FIX #4 — captura a exceção e loga corretamente
        logger.error(f"Erro ao carregar NewsAPI ({palavra_chave}): {e}")
        texto += "<i>Erro ao carregar NewsAPI.</i>"

    return texto


# ─────────────────────────────────────────────
# 6. LÓGICA DE EXECUÇÃO E AGENDAMENTO
# ─────────────────────────────────────────────
def executar_bot():
    logger.info("Coletando notícias...")

    texto_final  = f"🚀 <b>Notícias de T.I — {datetime.now().strftime('%d/%m/%Y %H:%M')}</b>\n\n"
    texto_final += buscar_hackernews() + "\n\n"

    # FIX #3 — termo em português para ter resultados reais no filtro 'language=pt'
    newsapi_bloco = buscar_newsapi("tecnologia", limite=5)
    if newsapi_bloco:
        texto_final += newsapi_bloco + "\n\n"

    texto_final += buscar_rss(limite=3)

    # FIX #1 — envia o conteúdo completo (linha que estava faltando antes)
    enviar_mensagem_em_partes(CHAT_ID, texto_final)
    logger.info("✅ Notícias enviadas com sucesso para o Telegram!")


def tarefa_diaria():
    logger.info("Iniciando disparo agendado...")
    executar_bot()


# ─────────────────────────────────────────────
# 7. STARTUP DO SISTEMA
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # Inicia o servidor Flask em thread separada (mantém a Render ativa)
    Thread(target=run_server, daemon=True).start()

    # Para receber às 09:00 no brasil, use "12:00" aqui.
    horario_agendado = "12:00"  
    schedule.every().day.at(horario_agendado).do(tarefa_diaria)

    logger.info(f"✅ Sistema iniciado! Bot agendado para {horario_agendado} UTC (08:00 Brasília).")

    # Mantém o processo vivo checando o agendador a cada minuto
    while True:
        schedule.run_pending()
        time.sleep(60)