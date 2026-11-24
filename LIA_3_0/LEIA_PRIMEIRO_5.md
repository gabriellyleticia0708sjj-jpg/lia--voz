# LIA 5.0 — Comece aqui

Esta atualização parte do ZIP 4.0, preservando a tela, voz Francisca, ativação pelo navegador, motor Ollama/OpenJarvis, memória, histórico, scripts originais e app desktop Tkinter. Os recursos 5.0 são da interface web/PWA. O desktop Tkinter legado continua separado.

## Codespaces: atualizar sem perder conversas
1. Pare somente o Flask antigo com Ctrl+C. Faça cópia de segurança local do diretório `LIA_3_0/dados` (não publique dados pessoais no GitHub). Não apague a pasta antiga.
2. Envie `LIA_5_0_COMPLETA.zip` à raiz do repositório `/workspaces/ia-pessoal` e execute:

```bash
cd /workspaces/ia-pessoal
unzip -o LIA_5_0_COMPLETA.zip
cd LIA_3_0
bash iniciar_lia.sh qwen2.5:3b
```

O ZIP não contém um banco vazio nem modelos pesados. A pasta e o esquema de dados antigos são mantidos. O script cria/reaproveita `.venv-web`, instala dependências ausentes, inicia Ollama caso necessário, baixa o modelo escolhido e abre Flask na porta 5000. Se usar outra pasta, ajuste o `cd`. Caso Ollama não esteja instalado: https://ollama.com/download/linux . Mantenha a porta 5000 privada no Codespaces, não encaminhe a porta 11434. A aplicação é pessoal, não tem autenticação multiusuário própria e não deve ser publicada na internet aberta. Abra a URL HTTPS privada em uma aba normal. No menu da LIA selecione o mesmo modelo usado no script (preferências antigas podem continuar salvas).

## Recursos adicionais (instalação opcional)
Em outro terminal, enquanto a LIA está rodando:

```bash
cd /workspaces/ia-pessoal/LIA_3_0
ollama pull nomic-embed-text
ollama pull qwen2.5vl:3b
.venv-web/bin/python INSTALAR_VOZ_OFFLINE.py
```

Baixe somente os recursos que deseja. Os modelos não estão no ZIP e podem consumir vários GB de disco e RAM. Para memória semântica abra menu > Ferramentas > Personalidade, marque pesquisa semântica, salve e clique em Indexar lote de conversas até concluir (16 mensagens de cada vez). Repita após novas conversas. O modelo de embeddings é opcional e sua precisão em português varia; a busca lexical é mantida. A busca por similaridade usa apenas conversas anteriores indexadas; a conversa atual usa o contexto recente e a busca lexical. O histórico SQLite guarda todas as mensagens de chat, mas a IA recebe uma janela limitada de trechos. A memória pessoal continua separada. Apagar só uma memória não apaga o histórico que a contém. Apagar todo o histórico também apaga seus vetores. Não guarde senhas, dados financeiros ou outras informações sensíveis.

- Pesquisa: menu Ferramentas > Pesquisa; envia a consulta ao serviço DDGS, usa filtro de busca e mostra até cinco resultados com fontes; não garante a segurança ou veracidade dos resultados. Não há pesquisa automática em segundo plano nem acesso a contas pessoais.
- PDF: até 8 MB, primeiras 30 páginas com texto e limite de 18 mil caracteres. PDF escaneado sem texto não tem OCR. A análise é por trechos, não substitui leitura integral.
- Imagem: PNG/JPEG/WebP, até 8 MB; Ollama com qwen2.5vl:3b. Imagens redimensionadas a até 1024px, sem identificação de pessoas. O modelo visual é separado do modelo de conversa; poderá ser pesado para Codespaces pequenos.
- Código/projeto: selecione arquivos ou ZIP; lê uma amostra de até 25 arquivos e 18 mil caracteres, ignora pastas e nomes comuns de credenciais. Nunca executa código ou extrai o ZIP para o sistema. O filtro de segredos é auxiliar, revise o arquivo antes de enviar. O conteúdo e resultados de análise não são armazenados automaticamente no histórico.
- Agenda: eventos e lembretes persistidos em SQLite; exportação manual `.ics` para importar em calendário externo. Não existe sincronização bidirecional, login Google/Outlook ou notificação garantida quando a LIA está fechada. Os lembretes aparecem na página ativa, com verificação periódica; Codespaces pode suspender.
- Conversas: lista das 200 conversas recentes, visualização paginada de 100 mensagens, opção de retomar. Histórico original continua disponível, incluindo conversas mais antigas.
- Voz offline: Ferramentas > Voz offline > Gravar > Parar e transcrever. Revise e envie o texto manualmente. Vosk processa localmente no servidor LIA após baixar o modelo; em Codespaces ainda precisa de conexão até o servidor remoto. O reconhecimento contínuo e a palavra de ativação continuam usando a API do navegador. A voz de resposta Francisca requer internet; a alternativa do navegador depende das vozes do dispositivo.
- PWA: no Chrome/Edge, use o botão Instalar LIA ou menu do navegador > Instalar aplicativo (se disponível). No celular, abra a URL privada autenticada e use Adicionar à tela de início. A PWA precisa do servidor ativo; não é um APK/EXE independente nem continua ouvindo com a tela fechada.
- Dispositivos: abra Ferramentas > Dispositivos. Digite o número com DDI e mensagem; confirme a ação. O aplicativo abrirá o discador, SMS ou WhatsApp compatível com o dispositivo que está usando. Você conclui a ligação ou envio. Não lê contatos, mensagens privadas, localização, nem controla outro dispositivo remotamente. Não há acesso oculto ou execução de comandos produzidos pela IA.

## Windows: executar no próprio computador
Instale Python 3.11 e Ollama para Windows de fontes oficiais, mantenha a pasta em um local fixo. Rode `INSTALAR_LIA_5_WINDOWS.bat` uma vez, depois `INICIAR_LIA_5_WINDOWS.bat`. O inicializador usa o servidor local e abre o navegador. Para iniciar no login do Windows, execute `ATIVAR_INICIO_WINDOWS.bat` e confirme; desative com `DESATIVAR_INICIO_WINDOWS.bat`. Não funciona no computador remoto do Codespaces. Para voz local, rode `.venv-web-win\Scripts\python.exe INSTALAR_VOZ_OFFLINE.py` no terminal local. Para escolher Qwen, instale `ollama pull qwen2.5:3b` e selecione no menu. Os arquivos de Tkinter antigos continuam no projeto, sem as novas ferramentas web.

## Desempenho e privacidade
`llama3.2:1b` é mais leve, `qwen2.5:3b` é uma opção intermediária, `qwen2.5:7b` é maior. Compare no seu hardware. A inicialização pré-carrega o modelo e o mantém ativo por 15 minutos. Modelos visuais e embeddings podem deslocar o modelo de chat da RAM e aumentar a espera. Não há benchmark de latência. Se ficar lento, desative pesquisa semântica e use o modelo leve. A pesquisa e Francisca usam internet; o áudio Vosk e anexos trafegam ao Codespaces quando usado remotamente. Dados SQLite não são criptografados pelo projeto. Faça backups seguros e não exponha as portas.

## Testes
`python TESTAR_MEMORIA.py` testa memória e contexto sem internet. `python TESTAR_LIA_5.py` precisa das dependências web e usa Flask test client com serviços externos simulados. Nesta entrega, a verificação de sintaxe e os testes de memória passaram; testes de rotas não puderam ser executados no ambiente de criação, pois Flask não estava disponível. Verifique as funcionalidades reais no seu ambiente antes de uso cotidiano.

Referências técnicas: https://ollama.com/library/nomic-embed-text ; https://ollama.com/library/qwen2.5vl ; https://alphacephei.com/vosk/models ; https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable ; https://pypi.org/project/ddgs/ .
