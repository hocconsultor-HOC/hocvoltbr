# HOCVOLTBR: aplicativo Android, do arquivo ao Google Play

O app tem **o mesmo layout e as mesmas funções do site**: é o próprio site empacotado como aplicativo Android nativo (Capacitor).
Quem monta o arquivo instalável é o GitHub, de graça, toda vez que você atualiza o site.

## Visão geral: 3 etapas

| Etapa | O que você ganha | Tempo |
|---|---|---|
| A. Subir para o GitHub | Site no ar + montagem automática do app | 20–30 min (uma vez) |
| B. Instalar no seu Pixel 9 | O app no seu celular, **hoje**, sem loja | 15 min |
| C. Publicar no Google Play | Qualquer pessoa baixa pela loja | cerca de 3 semanas (regra do Google, explicada abaixo) |

---

## A. Subir para o GitHub (uma vez)

Se você ainda não fez a parte do site, siga primeiro o `LEIA-ME.md` (criar a conta e o repositório `hocvoltbr`, ativar o Pages).

1. **Envie os arquivos novos.** No repositório `hocvoltbr`, clique em **Add file → Upload files** e arraste:
   - `index.html`, `privacidade.html`, `manifest.webmanifest`, `.gitignore` e a pasta `icons`;
   - a pasta **`app`** inteira (ela **não** traz a pasta `node_modules`, que o GitHub baixa sozinho).
2. **Crie o robô do app.** A pasta `.github` costuma ficar oculta, então faça pelo navegador: **Add file → Create new file**, nome exato `.github/workflows/app-android.yml`, cole o conteúdo de `robo-app-android.yml` e clique em **Commit changes**.
   Faça o mesmo para atualizar `.github/workflows/atualizar-base.yml` com o conteúdo de `robo-atualizacao.yml` (versão nova, que publica só os arquivos do site).
3. **Cadastre os secrets.** Em **Settings → Secrets and variables → Actions → New repository secret**, crie:

| Nome do secret | Valor | Para quê |
|---|---|---|
| `OCM_KEY` | sua chave do Open Charge Map | o app já abre com as duas bases ativas, para qualquer pessoa |
| `ANDROID_KEYSTORE_BASE64` | está no arquivo `LEIA-ME-CHAVE-PRIVADA.txt` | assinar o app para o Google Play |
| `ANDROID_KEYSTORE_PASSWORD` | está no mesmo arquivo | idem |
| `ANDROID_KEY_ALIAS` | `rotavolt` | idem |

> **A chave de assinatura é sua e é confidencial.** Guarde o `rotavolt-upload.jks` e o `LEIA-ME-CHAVE-PRIVADA.txt` fora do GitHub (pendrive, cofre de senhas). Toda atualização do app no Google Play precisa dessa mesma chave.

---

## B. Instalar no seu Pixel 9 (hoje, sem loja)

1. No GitHub, abra a aba **Actions → App Android (APK e AAB) → Run workflow**. A montagem leva de 8 a 15 minutos.
2. Quando ficar verde, entre na execução e baixe **HOCVOLTBR-app-android** (é um .zip). Dá para fazer isso direto no celular, pelo Chrome, entrando no GitHub.
3. No Pixel, abra o .zip em **Arquivos** e toque em `HOCVOLTBR.apk` (ou `HOCVOLTBR-teste.apk`, se os secrets da chave ainda não estiverem cadastrados).
4. O Android vai pedir para **permitir instalar apps desta fonte**: permita.
5. O Play Protect pode avisar que o app não veio da loja: toque em **Mais detalhes → Instalar mesmo assim**.
6. Pronto: o ícone **HOCVOLTBR** aparece na tela inicial.

**Outro caminho, ainda mais rápido:** com o site no ar, abra o link no Chrome do Pixel → menu **⋮ → Instalar app**. Ele vira um ícone na tela inicial e abre em tela cheia, como um app.

---

## C. Publicar no Google Play

### C1. Conta de desenvolvedor (só você pode fazer)
1. Acesse **play.google.com/console** com a sua conta Google.
2. Escolha o tipo de conta:
   - **Pessoal**: taxa única de US$ 25 e verificação de identidade com documento. Contas pessoais novas precisam fazer o **teste fechado** (C4).
   - **Organização**: exige CNPJ e número D-U-N-S, que é gratuito, mas pode levar semanas. É **dispensada** do teste fechado. Se a HOC Consultoria tiver CNPJ, vale considerar.
3. Faça a verificação pedida (documento e, às vezes, confirmação pelo app Play Console no seu celular Android).

### C2. Criar o app
**Criar app** → nome `HOCVOLTBR: Eletropostos` → idioma Português (Brasil) → App → Gratuito → aceite as declarações.

### C3. Preencher a ficha e as políticas
Use o arquivo `FICHA-DA-LOJA-E-FORMULARIOS.md` (kit da loja). Lá estão os textos prontos, as imagens e as respostas de Conteúdo do app, Classificação e Segurança dos dados.

### C4. Teste fechado (regra do Google para contas pessoais novas)
1. **Testar e lançar → Testes → Teste fechado → Criar faixa**.
2. Em **Testadores**, crie uma lista com **pelo menos 12 e-mails** (contas Google de quem tem Android). Uma sugestão é convidar clientes, família e amigos. Coloque 15 a 20, para garantir.
3. **Criar versão** → envie o arquivo **`HOCVOLTBR-GooglePlay.aab`** (vem no mesmo download da etapa B) → aceite a **Assinatura de apps do Google Play** (opção padrão).
4. Revise e envie. Depois da aprovação, copie o **link de participação** e mande para os testadores. Cada um precisa entrar no link, aceitar e instalar o app.
5. Os 12 testadores precisam ficar inscritos por **14 dias seguidos**. Peça para usarem o app de vez em quando.

### C5. Produção
1. Depois dos 14 dias: **Painel → Solicitar acesso à produção** (responda às perguntas sobre o teste).
2. O Google analisa em alguns dias.
3. Aprovado: **Produção → Criar versão** (reaproveite o mesmo .aab) → **Enviar para revisão**. Publicado, o app aparece na busca do Google Play.

### Atualizações depois de publicado
Qualquer mudança no site faz o GitHub montar uma nova versão do app sozinho, já com o número de versão maior. Basta enviar o novo `HOCVOLTBR-GooglePlay.aab` no Play Console.

---

## Perguntas rápidas

- **O app atualiza a base sozinho?** Sim. Ele baixa a base do site (atualizada às 23h59) e, se estiver sem internet para isso, usa a base que veio dentro dele.
- **Precisa da chave do Open Charge Map no celular?** Não, se você cadastrar o secret `OCM_KEY`: a chave já vai embutida no app.
- **E o iPhone (App Store)?** É outro processo: conta Apple Developer (US$ 99 por ano) e montagem num Mac. O mesmo projeto Capacitor serve de base, quando você quiser.
