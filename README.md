# 🚀 Bot de Notícias Automatizado!

Um Mensageiro diário que utiliza Api's de sites para trazer notícias automatizadas sobre os conteúdos mais relevantes na Área do T.I

## 📋 Sobre o Projeto

Este projeto foi desenvolvido para automatizar a atualização profissional sobre o ecossistema de T.I. O bot consome dados de múltiplas fontes (RSS Feeds, Hacker News e NewsAPI), processa as informações mais relevantes e utiliza a infraestrutura do **GitHub Actions** para execução agendada, eliminando a necessidade de um servidor ligado 24/7.

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3.10+
- **Bibliotecas:** - `requests`: Comunicação com APIs REST (Telegram, Hacker News, NewsAPI).
  - `feedparser`: Parsing de feeds RSS/XML.
- **Automação (CI/CD):** GitHub Actions.
- **Segurança:** GitHub Secrets (Environment Variables).

## ✨ Funcionalidades

- **Agregador de Fontes:** Consolida notícias do TechCrunch, Ars Technica, The Verge, Dev.to e portais brasileiros (Tecnoblog, Canaltech).
- **Filtro Inteligente:** Busca via palavras-chave personalizadas (ex: Java, Spring Boot, Python).
- **Entrega Formatada:** Mensagens enviadas via Telegram Bot API com suporte a HTML e links diretos.
- **Execução Serverless:** Rodagem automática diária configurada via Cron Job.

## ⚙️ Configuração do Ambiente

### Pré-requisitos
- Python instalado.
- Token de um Bot do Telegram (gerado pelo [@BotFather](https://t.me/botfather)).
- Seu Chat ID (pode ser obtido via [@userinfobot](https://t.me/userinfobot)).

### Instalação Local
1. Clone o repositório:
   ```bash
   git clone [https://github.com/SeuUsuario/BotNews.git](https://github.com/SeuUsuario/BotNews.git)
