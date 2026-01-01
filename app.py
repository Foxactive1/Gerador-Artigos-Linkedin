from flask import Flask, render_template, request, jsonify, session
import requests
import os
import json
from dotenv import load_dotenv
from datetime import datetime
import traceback

# Carregar variáveis de ambiente - APENAS UMA VEZ
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")

# Verificar se a chave está carregada
if not OPENROUTER_API_KEY:
    print("AVISO: OPENROUTER_API_KEY não encontrada no .env")
    print("Por favor, crie um arquivo .env com sua chave OpenRouter")

# Cache simples para prompts
PLATFORM_PROMPTS = {
    "LinkedIn": (
        "Crie um POST profissional para LinkedIn com estrutura otimizada para engajamento. "
        "Inclua: 1) Gancho impactante, 2) Contexto valioso, 3) Insights práticos, "
        "4) Storytelling breve, 5) Call-to-action claro. "
        "Use parágrafos curtos, linguagem direta e hashtags estratégicas no final."
    ),
    "Instagram": (
        "Crie um POST para Instagram com tom envolvente e visual. "
        "Estrutura: 1) Chamada visual inicial, 2) Texto conciso com quebras, "
        "3) Emojis estratégicos, 4) Pergunta engajadora, 5) Hashtags relevantes. "
        "Limite: 2200 caracteres."
    ),
    "Facebook": (
        "Crie um POST para Facebook com abordagem mais detalhada e conversacional. "
        "Inclua: 1) Título intrigante, 2) Desenvolvimento com exemplos, "
        "3) Perguntas para comentários, 4) Link para saber mais (opcional). "
        "Tom amigável e acessível."
    ),
    "Twitter/X": (
        "Crie um THREAD para Twitter (2-3 tweets conectados). "
        "Tweet 1: Gancho + ponto principal. "
        "Tweet 2: Desenvolvimento ou dado estatístico. "
        "Tweet 3: Conclusão + CTA. Use hashtags populares e mencione @relevant."
    )
}

TONE_GUIDELINES = {
    "Profissional": "Linguagem corporativa, dados concretos, formalidade moderada.",
    "Engraçado": "Humor leve, analogias criativas, tom descontraído.",
    "Técnico": "Terminologia específica, dados precisos, explicações detalhadas.",
    "Persuasivo": "Benefícios claros, urgência controlada, argumentação sólida.",
    "Inspiracional": "Storytelling emocional, mensagem motivacional, tom elevado.",
    "Descontraído": "Linguagem coloquial, primeira pessoa, tom pessoal."
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        # Log da requisição recebida
        print(f"Recebida requisição para /generate")
        
        data = request.json
        print(f"Dados recebidos: {data}")
        
        # Validação
        if not data:
            return jsonify({"error": "Nenhum dado recebido"}), 400
        
        if 'topic' not in data:
            return jsonify({"error": "Tema é obrigatório"}), 400
        
        topic = data.get('topic', '').strip()
        if not topic:
            return jsonify({"error": "Tema não pode ser vazio"}), 400
        
        if len(topic) > 150:
            return jsonify({"error": "Tema muito longo (máximo 150 caracteres)"}), 400
        
        # Verificar se a API key está configurada
        if not OPENROUTER_API_KEY:
            return jsonify({"error": "Chave API não configurada. Por favor, configure OPENROUTER_API_KEY no arquivo .env"}), 500
        
        platform = data.get('platform', 'LinkedIn')
        tone = data.get('tone', 'Profissional')
        length = data.get('length', 'medio')
        keywords = data.get('keywords', '')
        style = data.get('style', 'padrão')
        
        # Mapear extensão para tokens
        length_tokens = {
            'curto': 300,
            'medio': 500,
            'longo': 800
        }
        
        # Construir prompt avançado
        prompt = f"""
        {PLATFORM_PROMPTS.get(platform, PLATFORM_PROMPTS['LinkedIn'])}
        
        TONALIDADE: {tone}. {TONE_GUIDELINES.get(tone, '')}
        
        TEMA PRINCIPAL: {topic}
        
        {'PALAVRAS-CHAVE/HASHTAGS A INCLUIR: ' + keywords if keywords else ''}
        
        ESTILO DE ESCRITA: {style}
        EXTENSÃO: {length} ({length_tokens[length]} palavras aproximadamente)
        
        FORMATO DE SAÍDA:
        1. Título (em negrito com **)
        2. Corpo do texto com parágrafos claros
        3. Hashtags relevantes no final
        4. Call-to-action final
        
        IMPORTANTE:
        - NÃO use markdown além de negrito (**texto**)
        - NÃO inclua títulos como "Artigo:" ou "Post:"
        - NÃO seja genérico, seja específico com exemplos
        - Adapte completamente ao tom {tone}
        """
        
        print(f"Prompt construído para {platform}, tom {tone}, extensão {length}")
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "InNovaArticlesAI"
        }
        
        body = {
            "model": MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "Você é um redator especialista em marketing digital e copywriting. Crie conteúdo original, persuasivo e adaptado à plataforma."
                },
                {"role": "user", "content": prompt}
            ],
            "max_tokens": length_tokens[length] * 1.5,
            "temperature": 0.7 if tone == "Engraçado" else 0.5,
            "top_p": 0.9,
            "frequency_penalty": 0.3,
            "presence_penalty": 0.1
        }
        
        print(f"Enviando requisição para OpenRouter API...")
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=body,
            headers=headers,
            timeout=45
        )
        
        print(f"Status code da resposta: {response.status_code}")
        
        if response.status_code != 200:
            error_data = response.json()
            print(f"Erro da API: {error_data}")
            return jsonify({
                "error": f"Erro na API OpenRouter: {error_data.get('error', {}).get('message', 'Erro desconhecido')}"
            }), 500
        
        result = response.json()
        
        if "choices" not in result or len(result["choices"]) == 0:
            return jsonify({"error": "Resposta vazia da API"}), 500
        
        article = result["choices"][0]["message"]["content"].strip()
        
        # Registro de uso (simples)
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "platform": platform,
            "tone": tone,
            "topic": topic[:50],
            "length": length,
            "tokens_used": result.get("usage", {}).get("total_tokens", 0)
        }
        
        # Salvar no histórico da sessão
        if 'history' not in session:
            session['history'] = []
        
        session['history'] = session['history'][-9:] + [log_entry]  # Mantém últimos 10
        
        return jsonify({
            "article": article,
            "metadata": {
                "platform": platform,
                "tone": tone,
                "length": length,
                "estimated_tokens": result.get("usage", {}).get("total_tokens", 0),
                "timestamp": datetime.now().isoformat()
            }
        })
        
    except requests.exceptions.Timeout:
        print("Timeout na requisição para OpenRouter")
        return jsonify({"error": "Timeout - API demorou muito para responder"}), 504
    except requests.exceptions.ConnectionError:
        print("Erro de conexão com OpenRouter")
        return jsonify({"error": "Erro de conexão - verifique sua internet"}), 503
    except Exception as e:
        print(f"Erro inesperado: {str(e)}")
        print(traceback.format_exc())  # Isso mostrará o traceback completo
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

@app.route('/history', methods=['GET'])
def get_history():
    """Retorna histórico da sessão atual"""
    try:
        return jsonify({"history": session.get('history', [])})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/templates', methods=['GET'])
def get_templates():
    """Retorna templates predefinidos"""
    templates = [
        {
            "id": "linkedin_pro",
            "name": "Post LinkedIn Pro",
            "platform": "LinkedIn",
            "tone": "Profissional",
            "length": "medio",
            "description": "Post estratégico para líderes e empresas"
        },
        {
            "id": "instagram_engage",
            "name": "Instagram Engajador",
            "platform": "Instagram",
            "tone": "Descontraído",
            "length": "curto",
            "description": "Post visual com alta taxa de engajamento"
        },
        {
            "id": "thread_twitter",
            "name": "Thread Viral Twitter",
            "platform": "Twitter/X",
            "tone": "Persuasivo",
            "length": "longo",
            "description": "Thread educativa que viraliza"
        }
    ]
    return jsonify({"templates": templates})

if __name__ == '__main__':
    # Verificar se a API key está configurada
    if not OPENROUTER_API_KEY:
        print("=" * 60)
        print("AVISO IMPORTANTE: OPENROUTER_API_KEY não encontrada!")
        print("Por favor, crie um arquivo .env com:")
        print("OPENROUTER_API_KEY=sua_chave_aqui")
        print("FLASK_SECRET_KEY=sua_chave_secreta_aqui")
        print("=" * 60)
    
    app.run(debug=True, port=5000)