# Camada visual semântica — v1 exploratória

## Âncora

Testar se sinais acústicos locais tornam diferenças temporais mais legíveis
sem alterar os pontos congelados dos dois mundos e sem apresentar hipótese
visual como descoberta musical.

## Contrato de extração

Cada janela usa somente o áudio externo já sondado. O extrator grava cinco
sinais físicos, todos limitados a `[0, 1]`:

- `rms`: energia média da janela;
- `centroid`: centro de massa espectral relativo à frequência de Nyquist;
- `spread`: dispersão espectral relativa à frequência de Nyquist;
- `flux`: mudança espectral em relação à janela anterior, com transformação
  limitada;
- `attack`: aumento de RMS em relação à janela anterior, limitado por uma
  referência fixa.

Esses nomes descrevem extrações de sinal, não categorias musicais. Não há
notas, acordes, instrumentos, gênero, emoção ou rótulo de origem.

## Hipóteses de visualização

No toggle `Exploratória · hipótese`: `rms` controla opacidade, escala e halo, `centroid`
controla matiz, `spread` aplica um pequeno deslocamento de profundidade,
`flux` controla densidade dos ramos e `attack` aumenta o brilho do halo. O
modo `Agnóstica` mantém a visualização anterior disponível para comparação. No
modo exploratório, pontos com RMS mais baixo ficam quase transparentes, mas não
são removidos. Picos locais de ataque/mudança são marcados como `onset` e
recebem uma explosão de pontos; isso é um proxy acústico de início, não uma
detecção de notas.

A câmera pode aproximar-se até `0.45` unidades e a opção `Auto câmera` ativa a
rotação orbital suave. O movimento automático é desligável e não altera os
dados.

Os embeddings, projeções, checkpoints e áudio não são recalculados nem
alterados. O artefato experimental é isolado em
`artifacts/external-probe-semantic-v4/`.
