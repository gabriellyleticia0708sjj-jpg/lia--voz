# LIA 5.0 — Atualização

**Leia [LEIA_PRIMEIRO_5.md](LEIA_PRIMEIRO_5.md) para instalação e novos recursos.** A documentação 4.0 está preservada abaixo como referência.

# LIA 4.0 — Windows / VS Code

Interface minimalista: menu de três pontos no canto superior esquerdo, esfera roxa animada, resposta central e caixa de mensagem inferior. Histórico, voz, palmas e configurações ficam no menu. Mantém os dois motores de IA da versão anterior: Ollama (padrão) e OpenJarvis (API compatível).

## Instalação

1. Extraia o ZIP. Abra a pasta `LIA_3_0` no VS Code.
2. Execute `INSTALAR_WINDOWS.bat` uma vez (ou `python -m venv .venv` e `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`).
3. Instale Ollama de https://ollama.com/download/windows e baixe o modelo: `ollama pull llama3.2:1b`. Se o comando `ollama` não estiver no PATH, use `& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" pull llama3.2:1b` no PowerShell.
4. Execute `INICIAR_LIA.bat` ou `.\.venv\Scripts\python.exe main.py`.
5. Menu `•••` → Configurações: motor `ollama`, modelo `llama3.2:1b`.

## Voz e palmas

- Menu `•••` → **Ouvir agora**: captura uma frase e reconhece pelo serviço Google de SpeechRecognition (requer internet).
- Menu `•••` → **Configurações** → **Ativação por duas palmas**: ativa o detector experimental de dois picos de áudio. O resultado depende do microfone e de ruídos externos.
- **Ativação por voz “LIA”**: utiliza Vosk local para detectar a palavra, sem internet após instalar o modelo. Baixe um modelo Vosk em português da página oficial https://alphacephei.com/vosk/models, extraia a pasta do modelo e **renomeie-a para `vosk-pt` dentro de `modelos`**. A estrutura final deve ser `modelos/vosk-pt/am`, `modelos/vosk-pt/conf`, etc. Em seguida, habilite “Ativação por voz” nas Configurações. O reconhecimento da frase após ativar usa Google e precisa de internet nesta versão.
- Para evitar concorrência pelo microfone, o monitor de palmas/palavra-chave pausa durante a escuta de um comando.
- A esfera anima enquanto aguarda, escuta, pensa e sintetiza a resposta. Não é uma sincronização fonética exata.

## Privacidade e limitações

- As conversas ficam em `dados/conversas.json`; configurações em `dados/config.json`.
- O modelo Ollama gera respostas localmente, mas o reconhecimento de comandos após a ativação usa serviço online. Não há gravação contínua de áudio em disco pelo aplicativo.
- O OpenJarvis só funciona se o servidor local já estiver instalado e disponível na URL configurada.
- A interface e o código foram verificados quanto à sintaxe, mas o microfone e os modelos precisam ser testados no seu Windows.
- Não há automação de controle do PC nesta versão; a LIA não executa comandos arbitrários do sistema.

## Versão web — GitHub Codespaces
A versão desktop permanece intacta. No terminal, dentro da pasta LIA_3_0:

```bash
python -m pip install -r requirements-web.txt
python app.py
```
Abra a porta 5000 na aba Portas (mantenha PRIVADA). Não instale requirements.txt para a versão web. O servidor é pessoal, sem autenticação própria; não exponha publicamente.

O Ollama deve rodar no próprio Codespace. Instale conforme https://ollama.com/download/linux, depois execute `ollama serve` em um terminal e `ollama pull llama3.2:1b` em outro. O modelo depende da RAM disponível. O Ollama do Windows não é acessível automaticamente. Para OpenJarvis, configure o servidor no Codespace e a variável OPENJARVIS_URL antes de iniciar app.py. Escolha o motor e modelo no menu.

Use Chrome ou Edge compatível, abra a página HTTPS encaminhada, permita microfone e habilite voz/palmas no menu. A Web Speech API pode usar internet e parar quando a aba fica em segundo plano. O detector de palmas é experimental; desligue o microfone pelo menu. O histórico web fica em dados/web.sqlite3, separado do histórico desktop. Não há controle do Windows pelo navegador. A animação reage ao estado da resposta, não ao áudio exato.

## Atualização 3.1 — voz e diagnóstico web

No menu, use **Verificar conexão com a IA** para verificar o servidor/modelo. O botão não testa a geração de texto.
Use **Voz da LIA**, velocidade, tom e **Testar voz** para escolher as vozes instaladas ou disponibilizadas pelo navegador. Não é necessário Ollama para testar a fala.
Para ativação, abra a URL HTTPS da porta privada em uma aba normal do Chrome, conceda acesso ao microfone e marque **Ativar dizendo LIA**. A última frase reconhecida e os erros ficam no menu. O serviço de reconhecimento depende do navegador e pode usar internet; não é Vosk na versão web.
Se a porta 5000 estiver ocupada, execute `PORT=5001 python app.py` e abra a porta 5001 privada. Não use main.py no Codespaces.
O Ollama precisa permanecer em execução no Codespace, com o modelo disponível. `ollama serve`, `ollama list` e `ollama pull llama3.2:1b` são comandos separados.

## Atualização 4.0 — inicialização, memória permanente e voz neural (web)

**Atualizar sem apagar dados:** pare o Flask antigo com Ctrl+C. Extraia este ZIP sobre a pasta `LIA_3_0` existente (a pasta de destino da extração é o diretório pai). O ZIP não contém a pasta `dados` nem um banco vazio. Não apague a pasta anterior: o arquivo `dados/web.sqlite3` existente será reaproveitado. Faça uma cópia de segurança do banco com o Flask parado antes de atualizar. Mantenha dados pessoais fora do GitHub.

No Codespaces, abra um terminal na pasta do projeto e execute:

```bash
cd /workspaces/ia-pessoal/LIA_3_0
bash iniciar_lia.sh
```

O inicializador cria um ambiente Python isolado, instala as dependências se necessário, verifica/inicia o Ollama, baixa o modelo escolhido se faltar, tenta pré-carregá-lo e abre o Flask. O Ollama precisa estar instalado no Codespace; caso falte, consulte https://ollama.com/download/linux. A primeira execução pode demorar por causa das instalações. Abra a porta 5000 **privada**, numa aba HTTPS normal do Chrome. Não exponha a interface sem autenticação à internet. Para uma porta diferente: `PORT=5001 bash iniciar_lia.sh`.

**Modelos:**
- `bash iniciar_lia.sh llama3.2:1b` — opção inicial, leve e rápida.
- `bash iniciar_lia.sh qwen2.5:3b` — equilíbrio de capacidade e consumo.
- `bash iniciar_lia.sh qwen2.5:7b` — maior capacidade potencial; pode ser lento ou não caber na RAM do Codespace.

Se já tiver uma preferência de modelo salva no navegador, escolha também o mesmo modelo no menu da LIA. O inicializador baixa apenas o modelo indicado. Para testar outro modelo com o servidor já ativo: `ollama pull qwen2.5:3b` num terminal separado e altere o campo Modelo no menu. Modelos maiores não garantem respostas melhores em todas as tarefas. `keep_alive=15m` reaproveita o modelo na RAM, e o contexto enviado é limitado para reduzir a latência. O desempenho depende de CPU, RAM, GPU e tamanho da resposta. O Codespaces não é um serviço sempre ativo.

**Memória web:** o SQLite preserva mensagens entre reinícios. O ID da conversa também fica salvo no navegador. A IA recebe as últimas mensagens, a memória pessoal e trechos de conversas antigas encontrados por palavras-chave, inclusive de outras conversas. Todo o histórico fica no banco, mas nem todas as mensagens são enviadas a cada pergunta. A busca é lexical, não semântica; pode perder informações ou interpretar incorretamente. Para informações importantes, use memória explícita:

- `Meu nome é Ana` (use o nome ou apelido desejado).
- `Qual é meu nome?`
- `Lembre-se de que estudo Python`.
- `O que você sabe sobre mim?`
- `Esqueça meu nome`.

O nome e notas explícitas são tratados diretamente no SQLite, sem consultar o Ollama. Há até 50 entradas pessoais; o histórico não tem limite artificial de mensagens. No menu, **Histórico** mostra a página mais recente e **Ver mensagens anteriores** recupera as demais. **Memória pessoal** mostra as informações e permite editar/apagar. Apagar a memória pessoal não apaga menções no histórico e vice-versa. Para apagar ambos, use os dois controles. Não guarde senhas, chaves, endereço ou outras informações sensíveis. A filtragem é básica e não torna o banco criptografado. O arquivo `dados/web.sqlite3` reside no Codespace; apagar o Codespace pode eliminar os dados, então faça backups privados. Não envie o banco ao GitHub.

**Voz:** Francisca Neural é a opção inicial (Edge TTS, requer internet, envia texto da resposta ao serviço de voz); o menu permite escolher o navegador como alternativa, ajustar velocidade/tom e testar a fala sem Ollama. Se a voz neural falhar, tenta a voz do navegador. Permita reprodução de áudio e microfone quando solicitado. O detector de palmas continua experimental. A síntese de voz do desktop não foi alterada.

**Testes:** `python3 TESTAR_MEMORIA.py` verifica persistência, alteração/apagamento do nome, notas, recuperação entre conversas e envio do contexto ao adaptador de IA com resposta simulada. O Python, JavaScript e scripts Bash foram verificados sintaticamente. Flask, Ollama real, microfone e síntese online precisam ser testados no Codespaces. Não há automação de controle do computador nesta versão.
