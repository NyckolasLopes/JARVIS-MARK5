import requests
from bs4 import BeautifulSoup
from groq import Groq
import os
import logging

logger = logging.getLogger(__name__)

def _web_search(query, num_results=3):
    """Busca na web usando DuckDuckGo HTML (sem API key necessária)."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        url = f"https://html.duckduckgo.com/html/?q={query}"
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        for result in soup.find_all('div', class_='result__body')[:num_results]:
            title_tag = result.find('a', class_='result__a')
            snippet_tag = result.find('a', class_='result__snippet')
            if title_tag and snippet_tag:
                results.append({
                    "title": title_tag.get_text(strip=True),
                    "snippet": snippet_tag.get_text(strip=True)
                })
        
        return results
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return []

def SEARCH(query):
    """Busca informações na web e gera uma resposta usando o Groq."""
    try:
        # Buscar na web
        search_results = _web_search(query)
        
        if not search_results:
            return "Não consegui encontrar resultados para essa pesquisa."
        
        # Montar contexto com os resultados
        context = "\n".join([
            f"- {r['title']}: {r['snippet']}" for r in search_results
        ])
        
        # Usar Groq para gerar resposta baseada nos resultados
        GROQ_API = os.getenv("GROQ_API")
        if not GROQ_API:
            return context
        
        client = Groq(api_key=GROQ_API)
        response = client.chat.completions.create(
            messages=[{
                "role": "system",
                "content": "Você é o JARVIS. Responda de forma concisa em português baseado nos resultados de busca fornecidos."
            }, {
                "role": "user", 
                "content": f"Pergunta: {query}\n\nResultados da busca:\n{context}\n\nResponda de forma concisa:"
            }],
            model="llama-3.1-8b-instant",
            max_tokens=256
        )
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"SEARCH error: {e}")
        return f"Erro na busca: {str(e)}"