import os
import feedparser
import requests
from datetime import datetime
import logging
from typing import List, Dict, Optional
import time

# ─────────────────────────────────────────────
# CONFIGURAÇÃO DE LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# CONFIGURAÇÕES DO TELEGRAM E APIs
# ─────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")

# Validação crítica de variáveis de ambiente
if not TELEGRAM_TOKEN or not CHAT_ID:
    raise ValueError("❌ TELEGRAM_TOKEN e CHAT_ID devem estar configurados!")

# Palavras-chaves do meu gosto para desenvolvimento de software
KEYWORDS_INTERESSE = ["java", "spring", "python", "backend", "sql", "api", "vaga", "estágio"]

RSS_FEEDS = {
    "TechCrunch": "https://techcrunch.com/feed/",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "dev.to": "https://dev.to/feed",
    "G1 Tecnologia": "https://g1.globo.com/dynamo/tecnologia/rss2.xml",
    "Canaltech": "https://canaltech.com.br/rss/",
    "Tecnoblog": "https://tecnoblog.net/feed/",
    "Inovação Tecnológica": "https://www.inovacaotecnologica.com.br/boletim/rss.xml",
    "UOL Tecnologia": "https://rss.uol.com.br/feed/tecnologia.xml",
}

# Configurações de timeout e retry
TIMEOUT = 10  # segundos
MAX_RETRIES = 3
RETRY_DELAY = 2  # segundos

def formatar_titulo(titulo: str) -> str:
    """Adiciona um destaque visual se a notícia for sobre sua stack."""
    if not titulo:
        return "Sem título"
    
    for keyword in KEYWORDS_INTERESSE:
        if keyword.lower() in titulo.lower():
            # Escapar caracteres especiais do HTML
            titulo_safe = titulo.replace('<', '&lt;').replace('>', '&gt;')
            return f"🔥 <b>{titulo_safe}</b>"
    
    titulo_safe = titulo.replace('<', '&lt;').replace('>', '&gt;')
    return titulo_safe

def enviar_telegram(mensagem: str, retry_count: int = 0) -> bool:
    """Envia mensagem para o Telegram com retry."""
    if not mensagem or not mensagem.strip():
        logger.warning("Tentativa de enviar mensagem vazia")
        return False
    
    # Telegram tem limite de 4096 caracteres por mensagem
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
    
    try:
        response = requests.post(url, json=payload, timeout=TIMEOUT)
        response.raise_for_status()
        logger.info(f"✅ Mensagem enviada com sucesso")
        return True
    
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Erro ao enviar mensagem: {e}")
        
        # Retry lógico
        if retry_count < MAX_RETRIES:
            logger.info(f"🔄 Tentando novamente ({retry_count + 1}/{MAX_RETRIES})...")
            time.sleep(RETRY_DELAY)
            return enviar_telegram(mensagem, retry_count + 1)
        
        logger.error("❌ Falha após todas as tentativas")
        return False

def buscar_rss(limite: int = 3) -> Optional[str]:
    """Busca notícias dos feeds RSS configurados."""
    try:
        texto = "✨ <b>CURADORIA RSS</b>\n"
        texto += "<code>" + "—" * 20 + "</code>\n"
        
        feeds_processados = 0
        
        for nome, url in RSS_FEEDS.items():
            try:
                logger.info(f"Buscando feed: {nome}")
                feed = feedparser.parse(url)
                
                # Verificar se o feed foi parseado corretamente
                if feed.bozo:
                    logger.warning(f"⚠️ Feed {nome} com problemas: {feed.bozo_exception}")
                
                if not feed.entries:
                    logger.warning(f"⚠️ Feed {nome} sem entradas")
                    continue
                
                texto += f"\n📌 <b>{nome}</b>\n"
                
                for entrada in feed.entries[:limite]:
                    titulo = formatar_titulo(entrada.get("title", "Sem título"))
                    link = entrada.get("link", "#")
                    
                    # Validar URL
                    if link and link != "#":
                        texto += f"🔹 <a href='{link}'>{titulo}</a>\n"
                    else:
                        texto += f"🔹 {titulo}\n"
                
                feeds_processados += 1
                
            except Exception as e:
                logger.error(f"❌ Erro ao processar feed {nome}: {e}")
                continue
        
        if feeds_processados == 0:
            logger.error("❌ Nenhum feed foi processado com sucesso")
            return None
        
        logger.info(f"✅ {feeds_processados}/{len(RSS_FEEDS)} feeds processados")
        return texto
    
    except Exception as e:
        logger.error(f"❌ Erro geral ao buscar RSS: {e}")
        return None

def buscar_hackernews(limite: int = 5) -> Optional[str]:
    """Busca top stories do Hacker News."""
    try:
        texto = "🔥 <b>HACKER NEWS TOP STORIES</b>\n"
        texto += "<code>" + "—" * 20 + "</code>\n\n"
        
        url_ids = "https://hacker-news.firebaseio.com/v0/topstories.json"
        
        logger.info("Buscando top stories do Hacker News...")
        response = requests.get(url_ids, timeout=TIMEOUT)
        response.raise_for_status()
        
        ids = response.json()[:limite]
        stories_processadas = 0
        
        for story_id in ids:
            try:
                url_item = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                response = requests.get(url_item, timeout=TIMEOUT)
                response.raise_for_status()
                
                item = response.json()
                
                if not item:
                    continue
                
                titulo = formatar_titulo(item.get("title", "Sem título"))
                link = item.get("url", f"https://news.ycombinator.com/item?id={story_id}")
                pontos = item.get("score", 0)
                
                texto += f"⬆️ <code>{pontos:4d}</code> | <a href='{link}'>{titulo}</a>\n"
                stories_processadas += 1
                
                # Pequeno delay para evitar rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"❌ Erro ao processar story {story_id}: {e}")
                continue
        
        if stories_processadas == 0:
            logger.error("❌ Nenhuma story foi processada")
            return None
        
        logger.info(f"✅ {stories_processadas}/{limite} stories processadas")
        return texto
    
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Erro ao buscar Hacker News: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Erro geral no Hacker News: {e}")
        return None

def executar_bot():
    """Função principal que executa o bot."""
    logger.info("🤖 Iniciando Tech Bot...")
    
    data_formatada = datetime.now().strftime('%d/%m/%Y às %H:%M')
    
    # Cabeçalho
    cabecalho = (
        f"🤖 <b>TECH_BOT_UPDATE</b>\n"
        f"📅 {data_formatada}\n"
        f"<code>Status: Online e Atualizado</code>\n"
        f"———————————————————"
    )
    
    if not enviar_telegram(cabecalho):
        logger.error("❌ Falha ao enviar cabeçalho")
        return
    
    # Buscar e enviar RSS
    rss_texto = buscar_rss()
    if rss_texto:
        enviar_telegram(rss_texto)
    else:
        logger.warning("⚠️ Pulando envio de RSS (sem dados)")
    
    # Buscar e enviar Hacker News
    hn_texto = buscar_hackernews()
    if hn_texto:
        enviar_telegram(hn_texto)
    else:
        logger.warning("⚠️ Pulando envio de Hacker News (sem dados)")
    
    # Rodapé
    enviar_telegram("🏁 <i>Fim da atualização. Bons estudos, Matheus!</i>")
    
    logger.info("✅ Bot finalizado com sucesso!")

if __name__ == "__main__":
    try:
        executar_bot()
    except KeyboardInterrupt:
        logger.info("⚠️ Bot interrompido pelo usuário")
    except Exception as e:
        logger.critical(f"💥 Erro crítico: {e}", exc_info=True)