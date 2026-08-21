import os
import requests
from pathlib import Path

# Configurações
API_URL = "http://127.0.0.1:8000/api/v1/documents/upload"
PASTA_DOCUMENTOS = "./pautas_camara" # Crie essa pasta e coloque os PDFs dentro
TIPO_DOCUMENTO = "Pauta_Legislativa"

def iniciar_upload_em_lote():
    # Garante que a pasta existe
    if not os.path.exists(PASTA_DOCUMENTOS):
        os.makedirs(PASTA_DOCUMENTOS)
        print(f"Pasta '{PASTA_DOCUMENTOS}' criada. Coloque seus PDFs nela e rode novamente.")
        return

    # Lista todos os PDFs da pasta
    caminho_pasta = Path(PASTA_DOCUMENTOS)
    arquivos_pdf = list(caminho_pasta.glob("*.pdf"))

    if not arquivos_pdf:
        print(f"Nenhum arquivo .pdf encontrado na pasta '{PASTA_DOCUMENTOS}'.")
        return

    print(f"Foram encontrados {len(arquivos_pdf)} documentos. Iniciando indexação no RAG...\n")

    sucessos = 0
    erros = 0

    for caminho_arquivo in arquivos_pdf:
        nome_arquivo = caminho_arquivo.name
        print(f"Processando: {nome_arquivo}...")
        
        # Abre o arquivo em modo binário de leitura ("rb")
        with open(caminho_arquivo, "rb") as arquivo:
            # Estrutura exigida pelo 'UploadFile' e 'Form' do FastAPI
            files = {"file": (nome_arquivo, arquivo, "application/pdf")}
            data = {"doc_type": TIPO_DOCUMENTO}
            
            try:
                # Faz o POST para a API
                resposta = requests.post(API_URL, files=files, data=data)
                
                if resposta.status_code == 201:
                    dados_resposta = resposta.json()
                    chunks = dados_resposta.get('chunks_created', 0)
                    print(f"✅ [SUCESSO] Indexado! Gerou {chunks} fragmentos (chunks).")
                    sucessos += 1
                else:
                    print(f"❌ [ERRO] {resposta.status_code} - {resposta.text}")
                    erros += 1
            
            except requests.exceptions.ConnectionError:
                print("❌ [FALHA] Não foi possível conectar. O servidor do FastAPI (Uvicorn) está rodando?")
                break
            except Exception as e:
                print(f"❌ [FALHA] Erro inesperado ao enviar {nome_arquivo}: {e}")
                erros += 1

    print(f"\nResumo da Operação: {sucessos} com sucesso | {erros} com erro.")

if __name__ == "__main__":
    iniciar_upload_em_lote()