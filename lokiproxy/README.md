# HuginProxy (lokiproxy) — MVP

**Apenas para uso local de testes/estudos.** Proxy interceptador (HTTP/1.1 + CONNECT) com GUI Qt (PySide6) e engine de regras.
**Não utilize em redes de terceiros, ambientes de produção ou sem autorização explícita.**

## Funcionalidades

- Proxy HTTP/1.1 (porta local padrão `127.0.0.1:8080`).
- Suporte a `CONNECT` (TLS). MITM experimental com CA local autoassinada e certificados por SNI **apenas para testes** (no MVP, o CONNECT faz túnel transparente).
- GUI (PySide6 + qasync): tabela de flows (id, método, host, caminho, status, tamanho, duração), painel de detalhes (headers + body, texto/hex).
- Intercept ON/OFF, Forward, Drop, Repeat (Repeat WIP).
- Filtros/busca incremental (filtro simples na tabela).
- Editor de regras (YAML) com validação (pydantic). Engine de regras: `match(url_regex, method, status) -> actions(rewrite_url, set/remove header, set_request_body, set_response_body, mock_response)`.
- Logs estruturados via EventBus (status bar/stdout no MVP).
- Testes básicos (CA e rules).
- Empacotamento com PyInstaller (exemplo abaixo).

## Instalação (dev)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Executando

1. Gere a CA local (uma vez):
   ```bash
   python -m lokiproxy.cli ca init
   ```
   Instale **manualmente** o `~/.lokiproxy/ca.pem` no **navegador de testes** (apenas local).

2. Rode o proxy + GUI:
   ```bash
   python -m lokiproxy.cli run --host 127.0.0.1 --port 8080
   ```
   Configure seu navegador de testes para usar o proxy `127.0.0.1:8080`.

> **Aviso ético:** este projeto é educacional. Interceptação TLS e alteração de tráfego podem ser ilegais/antiéticas fora de um ambiente de testes controlado. Use com responsabilidade e apenas com seu próprio tráfego local.

## PyInstaller (build desktop)

```bash
pip install pyinstaller
pyinstaller -n HuginProxy -F -w -i NONE -p . -m lokiproxy.cli:main
```

## Limitações conhecidas do MVP

- CONNECT implementa túnel transparente; MITM completo pode ser evoluído em iteração futura.
- Sem suporte completo a keep-alive/pipelining; lida com uma requisição por conexão no MVP.
- Editor de bodies é textual (hex só leitura). Conteúdos binários devem ser tratados com cuidado.
- Repetir request (Repeat) ainda não implementado no core.
- Falta persistência de flows, export/import.

## Estrutura

```
lokiproxy/
  core/
    ca.py
    proxy.py
    flows.py
    rules.py
    bus.py
  gui/
    main.py
    app.py
    flows_view.py
    flow_detail.py
    rules_editor.py
  cli.py
  config.example.yaml
  rules.example.yaml
  tests/
  README.md
  pyproject.toml
```

## Segurança e escopo

- Bind em `127.0.0.1` por padrão.
- CA autoassinada instalada **apenas** em um navegador local de testes, nunca no sistema todo.
- Lista de *passthrough* pode ser ampliada para domínios que você **não** deseja interceptar.
