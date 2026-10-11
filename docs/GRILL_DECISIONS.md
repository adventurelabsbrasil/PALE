# Decisões do grill — laboratório acústico

**Data:** 09/10/2026
**Status:** decisões de produto e operação para a próxima implementação; não descreve funcionalidades já entregues.
**Fontes locais:** [`HANDOFF.md`](../HANDOFF.md) (hipótese e fases originais), [`README.md`](../README.md) (Fase 1 executada), [`config/phase1.toml`](../config/phase1.toml).

## Intenção central

- O sistema deve encontrar formas próprias de organizar os sons e de nos fazer ouvi-los e vê-los. Não receberá rótulos ou regras de teoria musical, nem pesos de áudio ou LLM pré-treinados no núcleo. Viés humano zero é impossível; a resposta escolhida foi manter representações concorrentes e não usar categorias musicais prontas como objetivo.
- “Autorregenerar” inclui **as três capacidades**: evoluir modelos/representações, gerar sons de sondagem e experimentar alterações no próprio código. Alterações de código ficam isoladas; **substituir a versão em uso exige testes e aprovação humana**. Comparações com explicações acústicas ou musicais conhecidas acontecem depois da descoberta de uma hipótese, sem orientar o treino.
- Um padrão promissor recebe o nome de **hipótese candidata** até replicação cega e comparação com explicações conhecidas. Ganho de previsão e novidade perceptiva são resultados diferentes.

## Dois critérios independentes

1. **Preditivo:** a próxima tarefa é prever um trecho futuro usando apenas o passado, comparando com baseline de persistência. Exigir pelo menos **5% menos erro** em cada grupo reservado — sintéticos, gravações ambientais e instrumentais — em **três inicializações independentes**, cada uma passando em todos os grupos. Uma candidata não pode piorar outro grupo além da variação de medição. Grupos novos começam exploratórios; só viram gate após baseline e teste reservado próprios.
2. **Perceptivo:** uma experiência pode entrar no acervo mesmo sem vencer o baseline preditivo, desde que seja distinta das existentes, responda de modo estável ao mesmo áudio e passe por limites de conforto e segurança. **Várias experiências ficam ativas lado a lado**, sem uma representação principal. Marcações humanas organizam a interface, mas não alimentam a recompensa do modelo.

**Decisão substituída:** a exigência inicial de ganho preditivo de 5% antes de qualquer automação diária deixou de valer para a exploração audiovisual. Essa exploração pode começar após seu próprio gate de estabilidade, diversidade e segurança. O gate de 5% continua válido apenas para afirmar/promover capacidade preditiva. A ativação do agendamento diário ocorre **após apresentação das evidências e decisão humana**.

## Primeira experiência visível

- **Ambiente 3D imersivo no navegador do MacBook, com fones estéreo e áudio binaural.** O sistema pode evoluir posições, formas, movimento e mapeamento espacial dentro de limites de conforto/estabilidade.
- Mostrar **dois mundos lado a lado** reagindo ao mesmo áudio; alternar qual espacialização é ouvida. A mesma entrada deve produzir uma resposta reproduzível, e uma experiência nova deve acrescentar perspectiva distinta à coleção.
- Sons gerados pelo sistema podem voltar ao treino em **parcela limitada e identificada**. A avaliação permanece em gravações independentes; não validar o sistema apenas com sons que ele próprio produziu.

## Entrada de dados

- Uso assumido nesta etapa: **pesquisa local privada, sem uso comercial**. No piloto, o usuário coloca arquivos em uma pasta de entrada; o sistema valida e importa. Busca automática fica para depois e apenas em fontes previamente aprovadas.
- A pasta pode conter **qualquer tipo de áudio**, inclusive fala e música; o modelo não recebe esses nomes como rótulos. Preservar o arquivo original e derivar vários trechos curtos; todos os trechos do mesmo original permanecem no mesmo conjunto de treino, validação ou teste.
- Arquivos sem procedência/licença documentada entram com direitos **não verificados** e não podem ter seu áudio exportado publicamente. Procedência e direitos ficam em registro de auditoria segregado das entradas do modelo. As fontes externas sugeridas no handoff original exigem verificação de licença antes da importação.

## Ciclo local e avisos

- Horário fixo escolhido: **09:00, America/Sao_Paulo**. Se o Mac estiver desligado, dormindo ou temporariamente inelegível, tentar uma vez na próxima oportunidade; nunca acumular vários ciclos perdidos. Pode rodar enquanto o usuário usa o Mac, com baixa prioridade, até **2 threads**, bateria acima de **50%** e teto inicial de **1 GiB de RAM**.
- **10 minutos de processamento no total por dia** para treino, sondas, experiências 3D e experimentos de autorregeneração, com tempo por atividade registrado. A distribuição é dinâmica. **Prioridade sensorial** foi assumida pela direção expressa no fim do grill; esta prioridade específica não recebeu resposta explícita à pergunta de alocação.
- Treinar diariamente mesmo sem áudio novo. Encerrar cedo quando a validação indicar platô; manter checkpoint aprovado. Ao atingir o teto antes de concluir, salvar a candidata para retomada e promover somente após avaliação completa. Candidatas que passam nos critérios podem ser promovidas automaticamente, com rollback; mudanças de código continuam exigindo aprovação humana.
- **Teto de 2 GiB em disco**: preservar originais e checkpoints aprovados; descartar candidatas antigas após 30 dias. Se originais/aprovados consumirem o teto, interromper novas importações e avisar, sem apagá-los.
- Notificações nativas do macOS **em cada sucesso**, erro e aviso, com registro local persistente. Rejeição de candidata por qualidade aparece no resumo normal; três rejeições consecutivas ou regressão forte geram alerta separado. O platô aparece no resumo diário.

## Estado e próximo corte de implementação

- A Fase 1 existe apenas neste laboratório; repositório Git local na branch `main`, **sem commits**. Os artefatos locais são ignorados pelo Git. O resultado verificável está em `artifacts/phase1-final/`; quatro testes passaram. O modelo inicial ficou cerca de **1,3% pior** que a interpolação no teste. O ciclo levou cerca de **2,5 s**; medição posterior indicou pico de **532 MB de RAM** em um Mac com **16 GiB**.
- Primeiro entregar a experiência 3D navegável com dois mundos e áudio espacial sobre os áudios já disponíveis; depois acrescentar evolução controlada de mundos/modelos, sondas, importação real e operação diária. A interface não deve apresentar novidade visual como prova científica.
- Nenhuma decisão deste registro autoriza consultar outros projetos, repositórios ou arquivos pessoais. Trabalhar somente em `exp-001` e usar diretórios temporários apenas para artefatos transitórios do trabalho.

## Validação sensorial da primeira iteração

**Data:** 09/10/2026
**Veredito:** aprovada como experiência audiovisual exploratória local.

- A mesma entrada WAV produz reação visual perceptível nos dois mundos.
- Os mundos continuam visualmente distintos, preservando seus mapeamentos espaciais próprios.
- A alternância A/B muda o panorama sem interromper a reação visual.
- O gesto explícito de áudio, o limite de ganho de 18% e o movimento suavizado foram mantidos.
- Desmarcar “Movimento” estabiliza os canvases sem interromper o áudio.
- Smoke manual no Chrome local passou sem erros ou warnings de console; `uv run pytest -q` passou com 4 testes e `node --check` passou.

Esta validação confirma a pergunta da primeira iteração — “a reação audiovisual torna a diferença entre os mundos perceptível?” — sem constituir evidência científica de descoberta musical. A próxima etapa deve escolher uma nova hipótese de exploração; não há ajuste de polish obrigatório nesta implementação.
