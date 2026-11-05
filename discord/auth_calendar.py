"""
Script de Autenticação Interativa do Google Calendar.

Executado uma única vez no terminal para autorizar o bot a acessar a agenda do Google:
    python3 discord/auth_calendar.py

Ao concluir, gera o arquivo `token.json` que é renovado automaticamente em segundo plano.
"""

from pathlib import Path
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from config import GOOGLE_CREDENTIALS_FILE, GOOGLE_TOKEN_FILE

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def main():
    caminho_cred = Path(GOOGLE_CREDENTIALS_FILE)
    caminho_token = Path(GOOGLE_TOKEN_FILE)

    print("=" * 70)
    print("🔑 Assistente de Autenticação com Google Calendar")
    print("=" * 70)

    if not caminho_cred.exists():
        print(f"\n❌ Arquivo de credenciais não encontrado em: {caminho_cred}")
        print("\nPara obter o arquivo 'credentials.json':")
        print("1. Acesse: https://console.cloud.google.com/")
        print("2. Crie ou selecione um projeto.")
        print("3. Ative a 'Google Calendar API' na biblioteca de APIs.")
        print("4. Em 'Tela de permissão OAuth' (OAuth consent screen), configure como 'Externo'")
        print("   e adicione o seu e-mail como 'Usuário de Teste' (Test User).")
        print("5. Em 'Credenciais' -> 'Criar Credenciais' -> 'ID do cliente OAuth':")
        print("   - Tipo de aplicativo: 'App para computador' (Desktop App)")
        print("6. Baixe o JSON gerado, renomeie para 'credentials.json' e salve em:")
        print(f"   {caminho_cred.resolve()}")
        print("\nDepois de salvar o arquivo, execute este script novamente!")
        sys.exit(1)

    print(f"\n✔ Arquivo de credenciais encontrado: {caminho_cred}")
    print("\nIniciando fluxo de autorização OAuth 2.0...")
    print("Uma janela do navegador será aberta para você fazer login.")
    print("-" * 70)
    print("⚠️  ATENÇÃO PARA DUAS TELAS DO GOOGLE:")
    print("1. Se aparecer 'Erro 403: access_denied' ou 'App não verificado':")
    print("   👉 Adicione seu e-mail em 'Usuários de teste' neste link direto:")
    print("      https://console.cloud.google.com/apis/credentials/consent?project=discord-bot-512020")
    print("   👉 Role até 'Usuários de teste' -> '+ ADD USERS' -> digite seu e-mail e salve.")
    print("\n2. Se aparecer 'O Google não verificou este app':")
    print("   👉 Clique no link 'Avançado' (no canto inferior esquerdo)")
    print("   👉 Clique em 'Acessar discord-bot-512020 (não seguro)'")
    print("   👉 Marque a caixinha de permissão da agenda e clique em 'Continuar'.")
    print("-" * 70 + "\n")

    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(caminho_cred), SCOPES)
        creds = flow.run_local_server(port=0, prompt="consent")

        with open(caminho_token, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

        print("\n" + "=" * 70)
        print("🎉 AUTORIZAÇÃO CONCLUÍDA COM SUCESSO!")
        print(f"Token salvo com segurança em: {caminho_token.resolve()}")
        print("O bot agora está pronto para consultar, criar e remover compromissos na sua agenda!")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Erro durante o fluxo de autorização: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
