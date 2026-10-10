# Handoff técnico — Laboratório de Descoberta Acústica

**Status:** especificação inicial para implementação de um MVP experimental, não um sistema já construído.
**Data:** 09/10/2026
**Plataforma inicial:** MacBook Air M4, com 16 GB ou 32 GB de memória (confirmar). Execução local, uma vez por dia, quando a máquina estiver disponível. Xeon com GPU de cerca de 2 GB fica como opção futura, não como requisito.

## 1. Visão e hipótese

Construir um **motor experimental de descoberta de estruturas acústicas**. O sistema recebe sinais sonoros sem receber rótulos ou regras de teoria musical, aprende regularidades diretamente dos dados e exibe representações visuais que possam evoluir entre ciclos. A hipótese a investigar é se o aprendizado produz relações reprodutíveis, úteis para previsão/generalização, que eventualmente possam ser comparadas à teoria musical estabelecida — **sem afirmar de antemão que haverá descoberta científica inédita**.

**Não é:** um visualizador de espectro convencional; um classificador de gêneros/instrumentos; um compositor por LLM; um sistema de trading; ou um agente de RL no MVP.

## 2. Princípios inegociáveis

1. **Núcleo de aprendizado inicializado do zero**, sem pesos de modelos de áudio ou LLMs pré-treinados.
2. **Sem supervisão musical:** não fornecer notas, acordes, BPM, escalas, gêneros ou nomes de instrumentos ao modelo.
3. **Metadados externos segregados:** manter origem/licença/rótulos do dataset apenas em registro de auditoria e avaliações *posteriores*, nunca como entradas do treinamento.
4. **Sem alteração arbitrária da versão em produção:** treinar uma candidata, avaliar em dados reservados e só então promover uma nova versão. Manter rollback.
5. **Reprodutibilidade:** seeds, configurações, hashes de datasets, métricas, checkpoints e logs versionados.
6. **Autonomia controlada:** executar o processo diário automaticamente, mas sem inferir descobertas só porque uma visualização parece interessante.
7. **Reconhecer limites de viés:** arquitetura, função de perda, distribuição de áudios e forma de visualizar são escolhas humanas. Meta é reduzir dependência de categorias musicais prontas, não eliminar todo viés.

## 3. Escopo de MVP

### Biblioteca inicial — aproximadamente 500 amostras de 5 segundos

- **300 áudios sintéticos** gerados localmente: senoides, misturas de osciladores, modulações, ruído e mudanças temporais; amostrar parâmetros de distribuições documentadas, sem afinação temperada pré-definida.
- **100 gravações ambientais** do ESC-50, respeitando licença e atribuição (CC BY-NC; verificar compatibilidade do uso).
- **100 gravações instrumentais isoladas** de NSynth, respeitando atribuição/licença, sem expor seus rótulos ao modelo.
- Formato de entrada preferencial: WAV PCM, mono e taxa de amostragem normalizada (por exemplo 22.050 Hz internamente para protótipo; arquivar original sem perda).
- Separar conjuntos de treino, validação e teste **por fonte/arquivo original ou família de geração**, evitando que versões do mesmo som contaminem o teste. Preservar conjunto de teste nunca visto durante o ajuste.
- Arquivos com identificadores opacos; manifesto confidencial/segregado com licença, procedência e metadados.

### Processamento e aprendizado

- Captura/normalização do áudio com Python e bibliotecas genéricas de sinal (NumPy, SciPy, SoundFile; Essentia opcional e somente nas funções que não adicionem semântica musical).
- Modelo pequeno em **PyTorch**, treinado do zero, usando CPU ou MPS no M4. Exemplo inicial: codificador convolucional compacto + previsão de segmentos futuros ou reconstrução de trechos ocultos. Ajustar tamanho por benchmarks reais.
- Manter baselines simples de previsão e testar se a rede realmente generaliza para amostras inéditas.
- Guardar embeddings intermediários para visualização; **PCA/UMAP/Three.js são recursos de apresentação**, não provas de teoria descoberta. Registrar parâmetros e permitir comparar versões.
- Aprendizado diário incremental com conjunto de replay e validação para reduzir esquecimento catastrófico. Se piorar, não promover.

## 4. Loop autônomo diário

Rodar **uma vez por dia**, com horário configurável, por exemplo via `launchd` no macOS. Não é necessário operação contínua, e o job deve tolerar Mac desligado ou em repouso (execução recuperável sem duplicidade).

1. **Preparar:** detectar novos arquivos autorizados, checar integridade, deduplicar e versionar o manifesto.
2. **Amostragem:** escolher lotes de treino com diversidade acústica sem usar rótulos como alvo.
3. **Treinar:** partir do último checkpoint aprovado, aplicar um orçamento configurável de tempo/etapas (começar pequeno, medir temperatura e desempenho do Air).
4. **Avaliar:** calcular erros de previsão/reconstrução e estabilidade em validação; comparar contra checkpoint anterior e baselines. Teste final reservado só em avaliações definidas, não a cada escolha de hiperparâmetro.
5. **Promover ou rejeitar:** publicar novo checkpoint somente se critérios mínimos objetivos forem atendidos; caso contrário manter o anterior.
6. **Visualizar:** produzir projeções e trajetórias dos embeddings, distribuição de distâncias e exemplos auditivos associados, com comparações entre versões.
7. **Registrar:** salvar relatório datado, métricas, versões, gráficos, alterações e hipóteses a investigar.

**Primeiro ciclo:** operar com lote fixo e uma atualização curta. Evoluir a duração apenas a partir dos benchmarks; não assumir execução rápida em qualquer configuração de 16 GB.

## 5. Componentes e interfaces

- `data/`: importação, geração de áudio sintético, manifesto, licenças, splits, hashes.
- `signal/`: processamento físico básico dos sinais e janelamento.
- `learning/`: modelo, treinamento, checkpoint, replay e métricas.
- `evaluation/`: baselines, avaliação fora da amostra, estabilidade e experimentos cegos.
- `visualization/`: primeiro gráficos estáticos/HTML interativo; Three.js 3D numa segunda etapa.
- `orchestration/`: um comando `run_daily`, idempotente, agendamento `launchd`, logs e controle de execução.
- `reports/`: resumo legível, métricas e visualização por execução.
- `config/`: parâmetros sem alterações manuais no código; tudo documentado.

**Stack inicial recomendada:** Python, NumPy, SciPy, SoundFile, PyTorch (MPS quando estável), Matplotlib/Plotly e SQLite ou arquivos JSON/Parquet para rastreabilidade. Essentia e Three.js opcionais, depois que o pipeline principal estiver comprovado. Não incorporar LLM ao núcleo; futuramente um LLM pode apenas explicar relatórios já gerados, sem orientar o aprendizado.

## 6. Critérios de aceite do MVP

- Gerar e carregar um primeiro conjunto de áudios **sem rótulos musicais nas entradas do modelo**.
- Reproduzir treinamento inicial do zero com seed fixa e registrar os resultados.
- Executar o pipeline inteiro por comando único e produzir um relatório datado.
- Apresentar gráficos comparáveis entre ciclos, com ligação ao trecho sonoro correspondente.
- Mostrar métricas de validação em material não visto durante o treino, comparando ao baseline.
- Manter versões/rollback e não substituir um checkpoint quando houver regressão significativa.
- Conseguir agendar a execução diária no macOS com proteção contra execuções duplicadas.
- Instalação/documentação reprodutível sem exigir GPU dedicada externa.

## 7. Entregas em fases

**Fase 1 — prova técnica:** estrutura do repositório, gerador de áudios sintéticos, primeiro modelo pequeno, baseline, conjunto de testes, execução manual e gráficos. **Somente depois** incorporar amostras externas.

**Fase 2 — autonomia local:** checkpoints, avaliação automática, relatório por ciclo, replay, importação controlada de datasets e agendamento diário no Mac.

**Fase 3 — exploração científica:** visualizações dinâmicas, busca ativa de exemplos acústicos que maximizam incerteza/curiosidade, e experimentos cegos com entradas nunca vistas. Se o sistema gerar sons, arquivar os parâmetros de geração e **não** usar só seus próprios sons na avaliação.

**Fase 4 — eventual expansão:** interface Three.js, streaming de áudio e/ou execução híbrida no Xeon, somente se houver justificativa medida.

## 8. Perguntas em aberto — não bloqueiam a Fase 1

- MacBook com 16 GB ou 32 GB?
- Horário desejado e política de execução quando o notebook estiver desligado?
- Limite de recursos/tempo por execução diária?
- Uso estritamente pessoal ou futura publicação/comercialização (impacta licenças)?
- O usuário prefere começar pela visualização 2D ou 3D?

## 9. Instrução de implementação ao agente de código

> Leia este handoff e primeiro faça um plano técnico curto, verificando o ambiente local e as dependências presentes. Implemente **somente a Fase 1**, com testes e documentação, sem acrescentar conceitos de teoria musical, modelos pré-treinados, downloads automáticos nem serviços pagos. Use um modelo pequeno e uma tarefa autossupervisionada mensurável, mantendo divisão correta entre treino, validação e teste. Não prometa descobertas científicas; mostre o que o modelo aprendeu por métricas e projeções reproduzíveis. Ao concluir, informe comandos de execução, resultados medidos, limitações e propostas para a Fase 2.
