# whisperDAV
> Testador silencioso de WebDAV com confirmação de execução fora de banda.
> Descobre o que o servidor executa sem fazer barulho nenhum.

---

## Visão geral

As ferramentas clássicas de teste de WebDAV funcionam. Mas elas se anunciam. Uma rajada de requisições `PUT` com nomes de arquivo previsíveis, um User-Agent reconhecível, sem limpeza alguma — e qualquer analista de SOC mediano já sabe o que está acontecendo.

O whisperDAV foi criado para responder uma pergunta diferente: é possível testar se um endpoint WebDAV executa arquivos enviados sem gerar uma assinatura de detecção óbvia? A resposta é sim — desde que você tenha paciência e use um **callback fora de banda** em vez de ler a resposta diretamente.

> **Aviso legal:** esta ferramenta é destinada exclusivamente a engagements de pentest autorizados, competições de CTF e ambientes de laboratório controlados. Usá-la contra sistemas sem permissão explícita é ilegal. O autor não assume nenhuma responsabilidade.

---

## Como funciona

```
upload do payload → espera aleatória → dispara GET → servidor faz ping OOB → deleta arquivo
```

Em vez de ler a saída do comando na resposta HTTP — o que parece exatamente o que é — o whisperDAV injeta um payload que faz o servidor se comunicar com um endpoint **interactsh** sob seu controle. Se o callback DNS chegar, a execução está confirmada. Nada suspeito aparece nos logs HTTP do servidor.

---

## Funcionalidades

| Funcionalidade | Descrição |
|---|---|
| Impersonação de browser | Rotaciona User-Agents reais a cada requisição. Nenhuma assinatura de ferramenta. |
| Timing humanizado | Delay aleatório entre cada ação. Quebra padrões de detecção automatizada. |
| Confirmação OOB | Callbacks DNS via interactsh. Execução confirmada sem tocar no corpo da resposta HTTP. |
| Limpeza automática | Arquivos enviados são deletados após cada teste. Nenhum artefato deixado no servidor. |
| Nomes de arquivo benignos | Nomes gerados parecem arquivos legítimos de aplicação, não scripts de teste. |
| Teste seletivo | Uma extensão por vez. Sem rajadas de upload que inundam os logs. |

---

## Requisitos

```bash
pip install requests

# interactsh-client (para callbacks OOB)
sudo apt install interactsh-client
# ou:
go install github.com/projectdiscovery/interactsh/cmd/interactsh-client@latest
```

---

## Uso

### Básico

```bash
python3 whisperdav.py http://alvo/webdav --oob abc123.oast.me --ext aspx
```

### Múltiplas extensões com delay customizado

```bash
python3 whisperdav.py http://alvo/webdav \
  --oob abc123.oast.me \
  --ext aspx php ashx \
  --delay-min 5 \
  --delay-max 15
```

### Argumentos

| Argumento | Obrigatório | Descrição |
|---|---|---|
| `url` | sim | URL base do endpoint WebDAV |
| `--oob` | sim | Seu subdomínio interactsh (ex: `abc123.oast.me`) |
| `--ext` | não | Extensões a testar. Padrão: `aspx`. Opções: `aspx php ashx txt html` |
| `--delay-min` | não | Espera mínima entre ações em segundos. Padrão: `8` |
| `--delay-max` | não | Espera máxima entre ações em segundos. Padrão: `25` |

---

## Fluxo de uso

1. **Inicie o interactsh-client** em um terminal separado. Copie o subdomínio gerado (ex: `abc123.oast.me`).

2. **Execute o whisperDAV** apontando para a URL do WebDAV e o seu subdomínio OOB. Escolha quais extensões testar.

3. **Monitore o interactsh** aguardando callbacks DNS. Cada callback carrega um identificador que indica qual extensão o gerou.

4. **Correlacione os resultados.** Callback recebido significa que o servidor executou o arquivo. Sem callback significa que a extensão foi enviada mas não executada, ou foi bloqueada.

---

## Payloads suportados

Cada extensão recebe um payload próprio que só realiza uma consulta DNS para o seu endpoint OOB — nada destrutivo, nada gravado em disco, nada que retorne saída na resposta HTTP.

| Extensão | Técnica |
|---|---|
| `.aspx` | Código C# inline via ping no `cmd.exe` |
| `.ashx` | HTTP handler em C#, específico para IIS |
| `.php` | `fsockopen` com fallback para `dns_get_record` |
| `.txt` / `.html` | Teste somente de upload, sem execução esperada |

---

## Máquinas para praticar

Se você está estudando para uma certificação de pentest ou apenas aprendendo, estas máquinas do Hack The Box são bons alvos para aplicar essa técnica:

**Granny** é a porta de entrada — IIS clássico com WebDAV, dificuldade fácil. **Grandpa** tem configuração similar com um caminho de exploração ligeiramente diferente. **Bounty** é o próximo passo: WebDAV com filtragem de upload, dificuldade média e cenário mais próximo do mundo real.

---

Projeto desenvolvido como exercício prático durante os estudos para a certificação DCPT. O objetivo foi entender não só como o abuso de WebDAV funciona, mas por que as ferramentas padrão fazem tanto barulho — e o que é preciso construir para ser mais silencioso. Contribuições e feedback são bem-vindos.
