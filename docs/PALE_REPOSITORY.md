# PALE como repositório-guarda-chuva

O PALE (`Projeto Acústico-Lógico-Estrutural`) é o repositório público dos experimentos de áudio, visualização, aprendizagem musical e investigação acústica da Adventure Labs.

## Fronteira

- O PALE fornece o catálogo, contratos compartilhados, ferramentas locais e documentação comum.
- Cada experimento mantém sua hipótese, artefatos, interface e critérios de avaliação identificados por um `experiment_id`.
- O `exp-001` é o primeiro experimento registrado e preserva sua execução de representação acústica.
- O `exp-002` é a experiência audiovisual 3D local reativa a áudio.
- Experimentos diferentes não devem compartilhar hipóteses científicas silenciosamente; compartilhamento de código precisa ser explícito e testado.

## Catálogo local

Listar os experimentos:

```sh
uv run python -m acoustic_lab experiments
```

Executar o primeiro experimento pelo catálogo:

```sh
uv run python -m acoustic_lab experiments --run exp-001 --output artifacts/my-run
```

Executar o organismo pelo mesmo ponto de entrada:

```sh
uv run python -m acoustic_lab experiments \
  --run exp-002 \
  --audio /caminho/para/audio.mp3 \
  --output artifacts/organism-run
```

Os comandos continuam disponíveis para compatibilidade (`run` e `experiment2`). O catálogo é a nova fronteira de descoberta do guarda-chuva, não uma substituição imediata dos experimentos existentes.
