# PALE — Projeto Acústico-Lógico-Estrutural

Este repositório é o guarda-chuva público dos experimentos de áudio da Adventure Labs. O primeiro experimento (`exp-001`) é o laboratório de descoberta acústica descrito abaixo; o catálogo comum está documentado em [`docs/PALE_REPOSITORY.md`](docs/PALE_REPOSITORY.md).

Para listar e executar experimentos pelo ponto de entrada do PALE:

```sh
uv run python -m acoustic_lab experiments
uv run python -m acoustic_lab experiments --run exp-001 --output artifacts/my-run
```

## Laboratório de Descoberta Acústica — Fase 1

Experimento local de aprendizado autossupervisionado com sons sintéticos. O modelo recebe apenas espectrogramas de áudio, nunca parâmetros do gerador, famílias ou rótulos musicais. Uma projeção visual não constitui evidência de descoberta científica.

## Instalação e execução

Requer macOS Apple Silicon ou outro computador com Python 3.12, `uv` e espaço para cerca de 100 MB de WAVs e artefatos. No diretório deste laboratório:

```sh
uv sync --python /opt/homebrew/bin/python3.12
uv run pytest -q
uv run python -m acoustic_lab run --config config/phase1.toml --output artifacts/my-run
```

`--output` precisa apontar para um diretório novo. Abrir `artifacts/my-run/report.html` no navegador para ver métricas, curvas e pontos clicáveis com seus WAVs. O comando não baixa datasets nem usa serviços externos. A primeira instalação das dependências Python pode precisar de acesso à rede.

## Ingestão WAV

`acoustic_lab.ingest.ingest_audio(file_path)` aceita WAV, descarta metadados do
contêiner, faz downmix para um tensor mono 1D, normaliza o pico para `[-1, 1]`
e envia o tensor para MPS quando o backend está disponível, com fallback para
CPU.

Para validar um arquivo local:

```sh
uv run python -m acoustic_lab.ingest /caminho/para/audio.wav
# shape=(...) sample_rate=... device=...
```

O carregamento usa `torchaudio`/TorchCodec e requer FFmpeg disponível no
sistema para decodificação de áudio. Essa ingestão é um probe de entrada; não
importa o arquivo para o dataset, não altera checkpoint e não promove uma
representação.

## Probe controlado de representação

Um WAV externo pode ser medido sem entrar no dataset. O probe calcula o mesmo
espectrograma da Fase 1, usa janelas completas de 128 quadros com hop de 16,
transforma cada embedding na PCA congelada do treino e grava métricas em um
diretório novo:

```sh
uv run python -m acoustic_lab.probe \
  --audio /caminho/para/audio.wav \
  --checkpoint artifacts/phase1-final/checkpoint.pt \
  --projection artifacts/phase1-final/pca_fit.json \
  --config artifacts/phase1-final/config.toml \
  --output artifacts/probe-001
```

O diretório também contém `probe.html`: sirva-o com `python3 -m http.server`
e abra no navegador para explorar a trajetória por janela, ouvir o WAV e
inspecionar as métricas. A página é um protótipo local, não uma interface de
produção.

Áudio menor que uma janela produz zero pontos (não é preenchido). O relatório
registra hash do WAV, checkpoint e projeção, estados de silêncio/clipping,
distância entre janelas adjacentes e latência. A PCA nunca é recalculada pelo
probe; `probe.json` é evidência de sondagem, não dado de treinamento.

## Probe externo agnóstico em dois mundos

Para passar um MP3 ou WAV externo pelos dois mundos congelados e abrir a
trajetória no Three.js:

```sh
uv run python -m acoustic_lab.external_probe \
  --audio /caminho/para/audio.mp3 \
  --source artifacts/phase1-final \
  --world-b artifacts/experience-preview-audio-reactive/future_predictor.pt \
  --output artifacts/external-probe-001
python3 -m http.server 8005 --directory artifacts/external-probe-001
```

Abra `http://127.0.0.1:8005/external_probe.html`. O comando aceita MP3/WAV,
decodifica para mono a 22.050 Hz, não treina e não importa o áudio no dataset.
O Mundo A usa o encoder da Fase 1; o Mundo B usa o preditor de trecho futuro
aprovado. A página sincroniza o marcador das duas trajetórias com a reprodução
do áudio. Esta é uma experiência isolada; a prévia Three.js aprovada não é
alterada.

## Experimento 2 — Organism

## Music Paint Wall — experimento visual isolado

Para abrir o estudo de pintura musical, sirva a pasta web e abra
`http://127.0.0.1:8007/music_painting.html`:

```sh
./scripts/serve_music_painting.sh
```

A página carrega automaticamente três obras locais de piano encontradas em
`~/Downloads`: Chopin, Beethoven e Bach. Os botões trocam a música sem exigir
upload; a opção de carregar outro WAV/MP3 continua disponível.

O estudo 02 aceita upload local de WAV/MP3 de piano. Uma análise offline extrai
ataques, energia, duração, brilho e picos aproximados de notas; esses eventos
alimentam partículas GPU com impacto, expansão, respingos e escorrimento. O
pitch ancora a região, mas a combinação dos parâmetros cria uma composição
emergente e única por música. A seed deriva do hash do arquivo, permitindo
reconstrução determinística; a obra e os eventos podem ser exportados em PNG e
JSON. O estado permanece em memória e o artefato é separado das experiências
acústicas existentes.

O piano vivo oferece cinco instrumentos Web Audio transparentes — oscilador,
baixo, pluck/piano, percussão e ruído/textura — com controles de dinâmica,
filtro, ataque e panorâmica. Cada toque gera um evento `pale-timeline-v1` com
origem `synthetic`, tempo, duração, campos acústicos e identificador estável;
a análise de áudio usa o mesmo contrato, mas preserva `confidence: inferred`.

O experimento 2 é uma experiência audiovisual independente da Fase 1. Ele
representa um áudio como um organismo 3D: um núcleo reage ao estado acústico
presente e uma malha espiral preserva memória temporal. A análise usa sinais
acústicos gerais, sem encoder, PCA, rótulos musicais ou importação para o
dataset. O visualizador usa Three.js/WebGL2 local, shaders GLSL próprios e
adapta a complexidade para manter fluidez em áudios distintos.

Para gerar e abrir a experiência com uma única chamada:

```sh
uv run python -m acoustic_lab experiment2 \
  --audio /Users/ribasrodrigo91/Downloads/exp-002.mp3 \
  --output artifacts/experiment-002
```

O comando copia o áudio para o artefato, registra seu SHA-256, prepara os
assets locais, inicia um servidor em `127.0.0.1` e abre o navegador. A página
oferece iniciar/pausar, reiniciar, busca temporal, reset da câmera e
encerramento do servidor. A saída é local e deve ser tratada como artefato
privado; ela não entra no Git nem no dataset.

Para validar apenas a geração, sem abrir navegador ou servidor:

```sh
uv run python -m acoustic_lab experiment2 \
  --audio /Users/ribasrodrigo91/Downloads/exp-002.mp3 \
  --output artifacts/experiment-002 \
  --no-serve --no-open
```

## Prévia audiovisual 3D local

Depois de uma execução da Fase 1, gere a experiência exploratória em um diretório novo:

```sh
uv run python -m acoustic_lab experience \
  --source artifacts/phase1-final \
  --output artifacts/experience-preview
python3 -m http.server 8000 --directory artifacts/experience-preview
```

Abra <http://localhost:8000/experience.html>. A página usa Three.js e OrbitControls empacotados localmente, sem CDN. Os dois mundos usam os mesmos WAVs: o Mundo A reutiliza o encoder da Fase 1; o Mundo B treina um pequeno preditor de trecho futuro do zero, usando apenas o passado como entrada. A PCA 3D de cada mundo é ajustada somente no split de treino.

Selecione um ponto, clique em “Iniciar áudio” e alterne a espacialização A/B. O gesto explícito é necessário por política do navegador; o ganho é limitado a 18%. Arrastar navega, a roda faz zoom e “Resetar câmera” retorna à posição inicial.

Esta prévia é uma experiência sensorial local, não uma avaliação de generalização nem evidência de descoberta musical. Ela não importa áudio externo, não agenda ciclos diários e não publica artefatos.

## Método

- Gerador: 100 configurações de origem, três variações de fase/ruído cada, cinco famílias físicas (oscilador, mistura, modulação, ruído filtrado e transição). Frequências e demais parâmetros vêm de distribuições contínuas; não há grade de notas. A divisão aleatória por **configuração de origem** produz 210/45/45 arquivos de treino/validação/teste.
- Arquivos: WAV PCM 16-bit, mono, 22.050 Hz, cinco segundos. `dataset_index.json` contém apenas ID opaco, caminho, divisão e SHA-256. `provenance_audit.json` guarda família, parâmetros e grupo, mas nunca é lido pelo treinamento.
- Tarefa: reconstruir 16 quadros ocultos de recortes de 128 quadros de um espectrograma STFT de magnitude logarítmica. A região oculta recebe a interpolação entre as bordas visíveis; uma rede convolucional temporal pequena, inicializada do zero, aprende uma correção residual. A máscara é informada como canal binário. O melhor checkpoint é escolhido pelo erro de validação. O teste é avaliado uma vez após essa escolha.
- Baseline: interpolação linear entre os dois quadros visíveis nas bordas do trecho oculto. Ambos são medidos com erro quadrático médio somente na região ocultada, em quatro recortes fixos por arquivo de validação ou teste. A PCA dos embeddings é ajustada somente nos exemplos de treino; cores indicam apenas a divisão dos dados.

`config/phase1.toml` controla tamanho do conjunto, transformada, máscara e treino. O ciclo grava configuração, versões de software, hashes, métricas, checkpoint, projeção e HTML. Cada execução é independente; não há promoção ou agendamento nesta fase.

## Execução verificada neste Mac

Com a configuração versionada (seed 44), o ciclo levou **2,512 s** de processamento após a instalação. O melhor checkpoint foi o da época 2. Em 45 arquivos e 180 janelas de validação, o erro quadrático médio foi **0,00003037** para a rede e **0,00002994** para a interpolação. No teste reservado, também com 45 arquivos e 180 janelas, foi **0,00002994** para a rede e **0,00002955** para a interpolação. A rede ficou cerca de **1,3% pior** que o baseline no teste; este experimento ainda não demonstra vantagem preditiva do aprendizado. O relatório local está em `artifacts/phase1-final/report.html` nesta máquina e pode ser regenerado com o comando acima usando um novo diretório de saída.

## Limitações

Áudios são inteiramente sintéticos; a variedade é restrita às cinco famílias do gerador. Uma divisão por configuração evita variações quase idênticas entre conjuntos, mas não demonstra transferência a gravações reais. O baseline pode superar a rede em sinais previsíveis; nesse caso o relatório apresenta essa regressão sem inferir aprendizado útil. Repetição exata é esperada no mesmo ambiente de software e CPU; outras versões de PyTorch podem produzir pequenas diferenças numéricas.

## Próxima implementação

As decisões posteriores à Fase 1 estão arquivadas em [`docs/GRILL_DECISIONS.md`](docs/GRILL_DECISIONS.md). O primeiro corte é uma experiência 3D local com dois mundos e áudio espacial; evolução automática e operação diária vêm depois. O ganho preditivo e a novidade perceptiva têm critérios separados.

## Ciclo evolutivo experimental

O ciclo manual e a janela limitada de 9–10/10/2026 estão descritos em [`docs/EVOLUTION_NIGHT.md`](docs/EVOLUTION_NIGHT.md). Para executar um ciclo isolado: `.venv/bin/python -m acoustic_lab.evolution cycle --sequence 1 --seconds 600`. Relatórios, baseline e STOP ficam em `artifacts/evolution/`. Nenhuma mutação de código é aplicada automaticamente à experiência ativa.
