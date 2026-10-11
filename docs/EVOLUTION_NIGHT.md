# Primeiro ciclo evolutivo e janela de 9–10/10/2026

## Plano técnico

O baseline é `artifacts/phase1-final` e a prévia sensorial aprovada é `artifacts/experience-preview-audio-reactive`. `artifacts/evolution/baseline.json` congela hashes do índice do dataset (incluindo splits), config, checkpoint, prévia, código alvo e avaliadores. Se um hash mudar, o comando recusa novos ciclos. O código ativo da experiência não é alterado.

Cada ciclo gera três candidatas por linha, salva diff/seed/métricas/logs e registra um relatório em `artifacts/evolution/cycle-NNN/report.json`. A linha visual varia coordenadas do Mundo B e mede separação geométrica e mudança de panorama; é apenas uma triagem objetiva, seguida de revisão perceptiva humana. A linha de modelo treina três seeds independentes para prever o futuro com o passado, comparando validação com persistência. O teste reservado é lido somente se a candidata superar persistência em 5% na validação. O gate de grupo exige as três seeds com ganho de 5% no teste sintético; não sustenta conclusão sobre áudio real. A linha de código altera a expressão de escala da função `_fit_3d` por AST, em cópia isolada, declara ocupação espacial como alvo e exige limite de clipping e coordenadas finitas. Patch de código só entra no ativo após revisão e aprovação humana.

O `sandbox-exec` da linha de código nega rede, escrita fora da pasta da candidata e leitura do dataset e código ativo. O processo recebe ambiente mínimo. O modelo roda em subprocesso limitado por timeout, 2 threads e monitor de 1 GiB de RSS. Cada ciclo tem 60 s no agendamento e 10 min no comando manual, com cotas iguais por linha e candidatas incompletas preservadas. O teto de artefatos é 2 GiB; baselines e promovidas não são apagados automaticamente. Um ciclo só integra vencedoras após seus gates; o primeiro ciclo não promoveu nenhuma.

## Operação desta noite

`ops/overnight-2026-10-09.plist` chama `acoustic_lab.night` a cada 30 min, a partir da carga. O processo só age entre 09/10 23:00 e 10/10 09:00, horário de São Paulo. Teto: 20 tentativas, 60 s por tentativa e 600 s acumulados; corre com prioridade baixa, uma instância por vez, bateria acima de 50%, até 2 threads e 1 GiB de RSS no treino. Se o Mac dormir, não o acorda; a janela fecha às 09:00. Após fim, STOP ou teto, o agente descarrega o próprio job do `launchd`.

Iniciar: `launchctl bootstrap gui/$(id -u) ops/overnight-2026-10-09.plist`. Verificar: `launchctl print gui/$(id -u)/com.adventurelabs.acoustic-lab-exp-001-night` e `cat artifacts/evolution/night-state.json`. Parar imediatamente: `.venv/bin/python -m acoustic_lab.evolution stop`; cria `artifacts/evolution/STOP`, interrompe o trabalhador ativo e descarrega o job. `artifacts/evolution/night.stdout.log` e `night.stderr.log` guardam diagnósticos. Não remover STOP durante esta janela.

## Validação inicial

Três ciclos manuais foram executados. O terceiro concluiu em cerca de 6 s; todas as seeds de modelo ficaram abaixo da persistência na validação; uma candidata visual aguarda revisão perceptiva; duas mutações de código passaram os gates geométricos em sandbox e aguardam revisão. O smoke de isolamento foi repetido com o sandbox nativo do macOS. Sem revisão humana das trajetórias/áudio, nenhuma candidata visual ou patch pode entrar no acervo/ativo. `integration.status=not_run` é o estado correto nesta rodada.

O primeiro tick do `launchd` gerou `cycle-101` e revelou um contador incorreto (ID de artefato contado como número de tentativas). O estado foi corrigido de 101 para 1, com os 32,99 s já gastos preservados. A variação de parâmetros também foi normalizada para os ciclos noturnos. O manifesto usado pelo primeiro tick está arquivado como `baseline-night-101.json`; `baseline.json` é o baseline congelado para os ticks seguintes. O teste `test_night.py` cobre a contagem e a sequência de artefatos.
