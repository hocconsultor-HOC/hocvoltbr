# HOCVOLTBR: como colocar no ar (uma vez só, cerca de 15 minutos)

Depois de configurado, o site fica num link fixo que abre em qualquer computador, celular ou tablet.
A base do Brasil se atualiza sozinha **todos os dias às 23h59** (horário de Brasília), sem custo.

## O que vem no pacote

| Arquivo | Para que serve |
|---|---|
| `index.html` | O site |
| `scripts/atualizar_base.py` | O robô que varre os 27 estados toda noite |
| `.github/workflows/atualizar-base.yml` | O agendamento das 23h59 (cópia visível: `robo-atualizacao.yml`) |
| `manifest.webmanifest` e `icons/` | Permitem instalar o site como app na tela inicial |
| `data/` | Onde o robô grava a base (começa vazia) |

## Passo a passo

1. **Crie uma conta grátis** em https://github.com (pode ser com o e-mail da consultoria).
2. Clique em **New repository**. Nome: `hocvoltbr`. Marque **Public** (o plano grátis exige repositório público para hospedar o site). Clique em **Create repository**.
3. Clique em **uploading an existing file** e arraste: `index.html`, `manifest.webmanifest`, `LEIA-ME.md` e as pastas `icons`, `scripts` e `data`. Clique em **Commit changes**.
4. **Crie o robô.** No Mac e no Windows, a pasta `.github` fica oculta e costuma não subir no arrastar. Por isso:
   **Add file → Create new file**, digite exatamente `.github/workflows/atualizar-base.yml` no nome,
   cole todo o conteúdo do arquivo `robo-atualizacao.yml` e clique em **Commit changes**.
5. **Ative o site:** **Settings → Pages → Source: GitHub Actions**.
6. **Permita que o robô salve a base:** **Settings → Actions → General → Workflow permissions → Read and write permissions → Save**.
7. **Primeira varredura:** aba **Actions → Atualizar base diária e publicar site → Run workflow**.
   Leva de 10 a 30 minutos. Quando ficar verde, o site está no ar em:
   **https://SEU-USUARIO.github.io/hocvoltbr/**

A partir daí, todo dia às 23h59 o robô roda sozinho. No topo do site aparece a data e a hora da última atualização.

## Importante: ative o Open Charge Map (grátis)

Teste real feito em 18/11/2026: o OpenStreetMap tinha **1 eletroposto cadastrado na cidade inteira do Rio de Janeiro**. Na mesma região, o Open Charge Map tinha vários (Shopping Nova América, Cachambi, Méier etc.). Sem a chave, muitas cidades aparecem vazias.

Isso soma uma segunda fonte aberta à base. O robô usa os pontos dela apenas quando ainda não existem no OpenStreetMap, para não duplicar.

1. Cadastre-se grátis em https://openchargemap.org. Depois, em **My Profile → My API Keys**, gere uma chave.
2. No GitHub: **Settings → Secrets and variables → Actions → New repository secret**. Nome: `OCM_KEY`. Valor: a chave.

## Abrir em cada aparelho

| Aparelho | Como |
|---|---|
| PC com Windows (Chrome, Edge, Firefox) | Abra o link |
| Mac (Safari, Chrome) | Abra o link |
| iPhone e iPad (Safari) | Abra o link. Para virar app: **Compartilhar → Adicionar à Tela de Início** |
| Android: Galaxy, Pixel, Motorola etc. (Chrome, Samsung Internet) | Abra o link. Para virar app: **⋮ → Instalar app** ou **Adicionar à tela inicial** |

Dica: o botão **"Copiar link desta busca"** gera um link pronto, por exemplo `.../hocvoltbr/?cidade=Campinas&uf=SP`, para mandar a um cliente pelo WhatsApp.

## Bom saber

- O GitHub às vezes atrasa alguns minutos o horário agendado. A hora exata aparece no topo do site.
- Se um estado falhar numa noite, o robô mantém os dados do dia anterior desse estado. Se todos falharem, ele não apaga nada.
- O botão **"Conferir ao vivo agora"** consulta o mapa naquele momento, sem esperar a atualização das 23h59.
- Encontrou um eletroposto que não aparece? Qualquer pessoa pode cadastrá-lo em https://www.openstreetmap.org, e ele entra na base na varredura seguinte.
- Se o arquivo `index.html` for aberto direto do computador, sem o link, o site funciona em modo "ao vivo", sem a base diária.

## Correções verificadas (horário, gratuidade, postos que faltam nas bases)

No `index.html`, a lista `VERIFICADOS` guarda informações conferidas à mão. Elas valem por cima das bases abertas.
Exemplos já incluídos: NorteShopping (recarga e estacionamento grátis para quem recarrega, horário do shopping) e Shopping Nova América (recarga grátis, estacionamento pago).
Para incluir outro local, copie um bloco e ajuste o nome, as coordenadas, o horário e as fontes.
