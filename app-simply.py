from flask import Flask, render_template, request, jsonify, session
import requests
import os
import json
from dotenv import load_dotenv
from datetime import datetime
from flask_cors import CORS
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()

app = Flask(__name__)
CORS(app)  # Habilitar CORS para segurança
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24).hex())

# Configurações da API
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")  # Modelo econômico para testes

# Verificar configuração
if not OPENROUTER_API_KEY:
    logger.warning("⚠️  OPENROUTER_API_KEY não configurada no .env")
    logger.warning("   Obtenha uma chave gratuita em: https://openrouter.ai")
    logger.warning("   Adicione ao .env: OPENROUTER_API_KEY=sua_chave_aqui")

# Templates de prompt otimizados
PLATFORM_CONFIGS = {
    "LinkedIn": {
        "prompt": "Crie um post profissional para LinkedIn com:\n1. Gancho impactante\n2. Insights práticos\n3. Dados relevantes\n4. Call-to-action claro\n5. 3-5 hashtags estratégicas",
        "max_tokens": 400,
        "temperature": 0.7
    },
    "Instagram": {
        "prompt": "Crie um post para Instagram com:\n1. Emojis estratégicos\n2. Texto conciso (máx 2200 chars)\n3. Pergunta engajadora\n4. Hashtags populares (5-10)\n5. Linguagem descontraída",
        "max_tokens": 300,
        "temperature": 0.8
    },
    "Facebook": {
        "prompt": "Crie um post para Facebook com:\n1. Título intrigante\n2. Texto conversacional\n3. Perguntas para interação\n4. Chamada para compartilhamento\n5. Hashtags moderadas",
        "max_tokens": 500,
        "temperature": 0.7
    },
    "Twitter/X": {
        "prompt": "Crie uma thread (2-3 tweets) para Twitter com:\n1. Tweet 1: Gancho + ponto principal\n2. Tweet 2: Dado ou exemplo\n3. Tweet 3: Conclusão + CTA\n4. Hashtags populares (2-3)\n5. Mencionar @perfis_relevantes se aplicável",
        "max_tokens": 350,
        "temperature": 0.75
    }
}

TONES = {
    "Profissional": "linguagem corporativa, formalidade moderada, baseada em dados",
    "Engraçado": "humor leve, tom descontraído, analogias criativas",
    "Técnico": "termos específicos, explicações detalhadas, precisão",
    "Persuasivo": "argumentação sólida, benefícios claros, call-to-action forte",
    "Inspiracional": "storytelling emocional, mensagem motivacional, tom elevado",
    "Descontraído": "linguagem coloquial, primeira pessoa, tom pessoal"
}

@app.route('/')
def home():
    """Página principal"""
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Endpoint de verificação de saúde"""
    return jsonify({
        "status": "healthy",
        "api_configured": bool(OPENROUTER_API_KEY),
        "model": OPENROUTER_MODEL
    })

@app.route('/generate', methods=['POST'])
def generate_content():
    """Endpoint principal para geração de conteúdo"""
    try:
        # Validar entrada
        data = request.get_json()
        if not data:
            return jsonify({"error": "Nenhum dado recebido"}), 400
        
        # Extrair parâmetros
        platform = data.get('platform', 'LinkedIn')
        tone = data.get('tone', 'Profissional')
        topic = data.get('topic', '').strip()
        length = data.get('length', 'medio')
        keywords = data.get('keywords', '')
        
        # Validações
        if not topic:
            return jsonify({"error": "O tema é obrigatório"}), 400
        
        if len(topic) > 150:
            return jsonify({"error": "Tema muito longo (máximo 150 caracteres)"}), 400
        
        if not OPENROUTER_API_KEY:
            return jsonify({"error": "API não configurada. Configure OPENROUTER_API_KEY no arquivo .env"}), 500
        
        # Log da requisição
        logger.info(f"Gerando conteúdo para: {platform} | Tom: {tone} | Tema: {topic[:30]}...")
        
        # Configurar parâmetros baseados na plataforma
        platform_config = PLATFORM_CONFIGS.get(platform, PLATFORM_CONFIGS['LinkedIn'])
        
        # Construir prompt otimizado
        prompt = f"""
        {platform_config['prompt']}
        
        TOM: {tone} - {TONES.get(tone, TONES['Profissional'])}
        
        TEMA: {topic}
        
        {"INCLUIR ESTAS PALAVRAS-CHAVE: " + keywords if keywords else ""}
        
        EXTENSÃO: {length} (ajuste o comprimento conforme)
        
        REGRAS IMPORTANTES:
        1. NÃO use markdown complexo, apenas **negrito** para ênfase
        2. NÃO adicione títulos como "Post:" ou "Artigo:"
        3. SEJA específico e evite generalidades
        4. ADAPTE completamente ao tom {tone}
        5. Use parágrafos curtos para melhor legibilidade
        
        ESTRUTURA DO CONTEÚDO:
        - Introdução impactante
        - Desenvolvimento com valor
        - Conclusão com CTA claro
        - Hashtags relevantes no final
        """
        
        # Preparar requisição para OpenRouter
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "InNovaArticlesAI"
        }
        
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "Você é um redator especialista em marketing digital com 10 anos de experiência. Crie conteúdo original, persuasivo e otimizado para cada plataforma."
                },
                {"role": "user", "content": prompt}
            ],
            "max_tokens": platform_config['max_tokens'],
            "temperature": platform_config['temperature'],
            "top_p": 0.9,
            "frequency_penalty": 0.2,
            "presence_penalty": 0.1,
            "stream": False
        }
        
        # Fazer requisição com timeout
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=45
        )
        
        # Processar resposta
        if response.status_code != 200:
            error_data = response.json()
            logger.error(f"OpenRouter error: {error_data}")
            return jsonify({
                "error": f"Erro na API: {error_data.get('error', {}).get('message', 'Erro desconhecido')}"
            }), 500
        
        result = response.json()
        
        if "choices" not in result or not result["choices"]:
            return jsonify({"error": "Resposta vazia da API"}), 500
        
        # Extrair conteúdo
        content = result["choices"][0]["message"]["content"].strip()
        
        # Coletar estatísticas
        usage = result.get("usage", {})
        
        # Preparar resposta
        response_data = {
            "success": True,
            "article": content,
            "metadata": {
                "platform": platform,
                "tone": tone,
                "topic": topic[:50],
                "length": length,
                "tokens_used": usage.get("total_tokens", 0),
                "timestamp": datetime.now().isoformat(),
                "model": OPENROUTER_MODEL,
                "characters": len(content)
            }
        }
        
        # Log de sucesso
        logger.info(f"Conteúdo gerado com sucesso! Tokens usados: {usage.get('total_tokens', 0)}")
        
        return jsonify(response_data)
        
    except requests.exceptions.Timeout:
        logger.error("Timeout na requisição para OpenRouter")
        return jsonify({"error": "A API demorou muito para responder. Tente novamente."}), 504
    
    except requests.exceptions.ConnectionError:
        logger.error("Erro de conexão com OpenRouter")
        return jsonify({"error": "Erro de conexão. Verifique sua internet."}), 503
    
    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}", exc_info=True)
        return jsonify({"error": f"Erro interno do servidor: {str(e)}"}), 500

@app.route('/templates', methods=['GET'])
def get_templates():
    """Retorna templates predefinidos"""
    templates = [
        {
            "id": "linkedin_leadership",
            "name": "Liderança no LinkedIn",
            "platform": "LinkedIn",
            "tone": "Profissional",
            "length": "medio",
            "description": "Post para posicionar líderes e especialistas",
            "example_topic": "Como desenvolver uma cultura de inovação na sua equipe"
        },
        {
            "id": "instagram_promo",
            "name": "Promoção no Instagram",
            "platform": "Instagram",
            "tone": "Descontraído",
            "length": "curto",
            "description": "Anúncio de produto/serviço com alto engajamento",
            "example_topic": "Lançamento do novo curso de Marketing Digital"
        },
        {
            "id": "facebook_community",
            "name": "Engajamento no Facebook",
            "platform": "Facebook",
            "tone": "Conversacional",
            "length": "longo",
            "description": "Post para gerar discussão e interação",
            "example_topic": "Quais são os maiores desafios do home office hoje?"
        },
        {
            "id": "twitter_thread",
            "name": "Thread Educativa",
            "platform": "Twitter/X",
            "tone": "Técnico",
            "length": "medio",
            "description": "Thread para ensinar um conceito complexo",
            "example_topic": "5 conceitos de IA que todo profissional deveria conhecer"
        }
    ]
    return jsonify({"templates": templates})

@app.route('/stats', methods=['GET'])
def get_stats():
    """Retorna estatísticas do sistema"""
    return jsonify({
        "status": "operational",
        "version": "1.0.0",
        "supported_platforms": list(PLATFORM_CONFIGS.keys()),
        "supported_tones": list(TONES.keys()),
        "model": OPENROUTER_MODEL,
        "api_configured": bool(OPENROUTER_API_KEY)
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint não encontrado"}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Método não permitido"}), 405

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Erro interno do servidor"}), 500

if __name__ == '__main__':
    # Mensagem inicial
    print("\n" + "="*60)
    print("🚀 InNovaArticlesAI - Gerador de Conteúdo com IA")
    print("="*60)
    
    if OPENROUTER_API_KEY:
        print("✅ API Key configurada")
        print(f"🤖 Modelo: {OPENROUTER_MODEL}")
    else:
        print("⚠️  ATENÇÃO: OPENROUTER_API_KEY não configurada!")
        print("   Crie um arquivo .env com sua chave:")
        print('   OPENROUTER_API_KEY="sua-chave-aqui"')
        print("\n   Obtenha uma chave gratuita em: https://openrouter.ai")
    
    print("\n📡 Servidor rodando em: http://localhost:5000")
    print("🛑 Pressione CTRL+C para parar")
    print("="*60 + "\n")
    
    # Configurações do servidor
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000,
        threaded=True
    )