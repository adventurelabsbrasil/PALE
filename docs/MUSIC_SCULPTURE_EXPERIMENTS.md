# Music Sculpture — experimentos separados

## Propósito

Este documento organiza experimentos visuais que ficam **separados do plano
inicial de evolução da Music Sculpture**. Ele não redefine o produto, não
altera a análise musical e não transforma uma hipótese estética em descoberta
musical.

O plano inicial permanece sendo:

- preservar o Micélio como modo padrão e referência de regressão;
- tornar o modo Árvore / raízes mais legível como organismo vegetal;
- validar a mesma música em abertura, expansão, retorno e pausas;
- manter determinismo, custo controlado e exportações reconstruíveis.

## Estado de referência

Experimento local em `http://127.0.0.1:8007/music_painting.html`, com Für Elise
como obra de referência. O modo Árvore já possui raízes distribuídas, massas
para graves, galhos intermediários, cones/brotos para agudos e conexões de
memória. O Micélio deve continuar sendo comparado após cada rodada.

## Regras para qualquer experimento

1. Uma hipótese por rodada.
2. Alterar somente o modo Árvore, salvo quando a hipótese exigir comparação.
3. Fixar música, seed e câmera antes de comparar imagens.
4. Não mudar análise de áudio, heurística de motivos ou dados exportados.
5. Não criar geometrias por frame.
6. Registrar resultado como `passou`, `inconclusivo` ou `rejeitado`.
7. Parar quando o critério visual estiver atendido; novas ideias voltam para
   este backlog.

## Experimentos propostos

### E1 — Hierarquia de crescimento

**Pergunta:** uma pessoa distingue raiz, tronco, galho e broto sem conhecer o
código?

**Hipótese:** separar a geometria por registro e ataque torna a função musical
visível sem aumentar muito a densidade.

**Variações:**

- A: estado atual;
- B: graves como massas radiculares, médios como tubos e agudos como cones;
- C: B com brotos apenas nos ataques fortes ou nas notas de retorno.

**Gate:** escolher a variante em que três observadores identificam a ordem
base → ramificação → copa em até 10 segundos, sem explicação prévia.

### E2 — Silhueta e clareiras

**Pergunta:** a obra continua legível quando a música fica densa?

**Hipótese:** amostragem de conexões de acorde/retorno e preservação de vazios
nas pausas produzem uma silhueta mais reconhecível que a conexão de todos os
eventos.

**Medições:**

- quantidade de conexões visíveis por segundo;
- área de clareira durante pausas;
- distinção visual entre início, seção densa e retorno.

**Gate:** nenhuma seção deve virar uma massa contínua; as pausas precisam ser
percebidas como espaço, não apenas como ausência de animação.

### E3 — Memória como estágio de crescimento

**Pergunta:** o retorno de um motivo parece uma reincidência transformada?

**Hipótese:** deslocar cada ocorrência para uma altura e lateralidade
progressivas comunica crescimento sem duplicar o motivo literalmente.

**Gate:** no retorno de Für Elise, identificar visualmente que algo reapareceu
em outra posição; as conexões de memória devem ligar apenas fases equivalentes.

### E4 — Paleta funcional

**Pergunta:** cor e saturação ajudam a ler função ou apenas decoram?

**Hipótese:** raízes/troncos escuros, galhos oliva, brotos âmbar e pausas menos
saturadas comunicam estrutura melhor que o brilho proporcional à energia.

**Gate:** energia alta não pode converter toda a copa em vermelho/rosa; graves,
médios, agudos e pausas devem manter diferenças cromáticas estáveis.

### E5 — Câmera e composição

**Pergunta:** a câmera atual mostra a árvore inteira nos momentos importantes?

**Hipótese:** uma composição ligeiramente mais afastada, ou um enquadramento
determinístico por seção, melhora a leitura sem alterar a obra.

**Gate:** base e copa aparecem simultaneamente na abertura, na região densa e
no retorno, sem depender de interação manual.

### E6 — Piano ao vivo como crescimento incremental

**Pergunta:** a linguagem Árvore funciona também sem uma peça pré-analisada?

**Hipótese:** ataques criam brotos e sustains criam extensões de galho, mantendo
o mesmo vocabulário visual do arquivo carregado.

**Gate:** tocar notas isoladas, um acorde e uma nota sustentada deve produzir
três respostas distinguíveis; a troca para Micélio continua reversível.

## Ordem recomendada

Executar E1 → E2 → E3 → E4. Executar E5 somente se a silhueta continuar
difícil de ler. Executar E6 depois que a gramática visual estiver estável.

E1 e E2 são os únicos experimentos necessários para fechar a rodada atual. E3–E6
ficam estacionados até haver evidência de que a estrutura básica já está
legível.

## Registro mínimo por rodada

- hipótese e variante escolhida;
- música, seed, modo e câmera;
- screenshot da abertura, seção densa e retorno;
- resultado do Micélio antes/depois;
- console, testes, PNG e JSON;
- decisão: manter, reverter ou estacionar;
- próxima hipótese, se houver.

## Fora deste documento

Não entram aqui: experiment2, alterações de análise musical, claims científicos,
automação diária, deploy, mudança de stack, novos datasets ou substituição do
Micélio. Cada um exige plano próprio e nova âncora.
