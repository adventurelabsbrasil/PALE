# Laboratório de Descoberta Acústica — Fase 1

Experimento local de aprendizado autossupervisionado com sons sintéticos. O modelo recebe apenas espectrogramas de áudio, nunca parâmetros do gerador, famílias ou rótulos musicais. Uma projeção visual não constitui evidência de descoberta científica.

## Instalação e execução

Requer macOS Apple Silicon ou outro computador com Python 3.12, `uv` e espaço para cerca de 100 MB de WAVs e artefatos. No diretório deste laboratório:

```sh
uv sync --python /opt/homebrew/bin/python3.12
uv run pytest -q
uv run python -m acoustic_lab run --config config/phase1.toml --output artifacts/my-run
```

`--output` precisa apontar para um diretório novo. Abrir `artifacts/my-run/report.html` no navegador para ver métricas, curvas e pontos clicáveis com seus WAVs. O comando não baixa datasets nem usa serviços externos. A primeira instalação das dependências Python pode precisar de acesso à rede.

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
