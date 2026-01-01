import requests
import json

# Teste simples da API
test_data = {
    "platform": "LinkedIn",
    "tone": "Profissional",
    "topic": "Inteligência Artificial no Marketing Digital",
    "length": "curto",
    "keywords": "#marketing #ia #tecnologia"
}

try:
    response = requests.post(
        "http://localhost:5000/generate",
        json=test_data,
        timeout=30
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        print("\nArtigo gerado com sucesso!")
        print(f"Plataforma: {data.get('metadata', {}).get('platform')}")
        print(f"Tamanho do artigo: {len(data.get('article', ''))} caracteres")
        print("\n--- Artigo ---")
        print(data.get('article', '')[:200] + "...")
    else:
        print(f"Erro: {response.status_code}")
        
except Exception as e:
    print(f"Erro ao testar API: {str(e)}")